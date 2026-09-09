"""
tests/unit/test_context_fusion.py
=====================================
Unit tests for jarvis.perception.context_fusion.ContextFusionLayer.

Note: despite the module's docstring talking about "blending" context, the
current `fuse()` implementation does NOT merge ContextSnapshot data into the
packet at all -- it only scans packet.text for ambiguous pronoun references
and, if found, forces packet.intent = "llm_route". The `snapshot` parameter
is accepted but never read. Several tests below explicitly document this
(see the "snapshot argument" section) rather than assuming a merge behavior
that isn't implemented.
"""
import pytest

from jarvis.perception.context_fusion import ContextFusionLayer
from jarvis.perception.perception_packet import PerceptionPacket, Utterance, ContextSnapshot

pytestmark = pytest.mark.unit


@pytest.fixture
def fusion():
    return ContextFusionLayer()


def _packet(text):
    return PerceptionPacket(utterance=Utterance(text=text))


# ── No ambiguous reference ───────────────────────────────

def test_unambiguous_text_leaves_intent_unset(fusion):
    packet = _packet("open notepad")
    result = fusion.fuse(packet)
    assert result.intent == ""


def test_word_containing_pronoun_substring_is_not_falsely_flagged(fusion):
    """'credit' contains the letters 'it' but is not the standalone word 'it'
    and has no surrounding whitespace matching " it " -- must not trigger
    ambiguous-reference routing. Confirms word-boundary correctness."""
    packet = _packet("check my credit report")
    result = fusion.fuse(packet)
    assert result.intent == ""


# ── Single-word pronoun detection (word-list branch) ─────

def test_standalone_pronoun_it_triggers_llm_route(fusion):
    packet = _packet("close it")
    result = fusion.fuse(packet)
    assert result.intent == "llm_route"


def test_standalone_pronoun_back_triggers_llm_route(fusion):
    packet = _packet("switch back")
    result = fusion.fuse(packet)
    assert result.intent == "llm_route"


def test_word_ending_in_back_does_not_trigger(fusion):
    """'backpack' should not match the pronoun 'back' -- neither the exact
    word-list check nor the padded-substring check should fire."""
    packet = _packet("look at the backpack")
    result = fusion.fuse(packet)
    assert result.intent == ""


# ── Multi-word phrase detection (padded-substring branch) ─

def test_multiword_phrase_the_window_triggers_llm_route(fusion):
    packet = _packet("open the window")
    result = fusion.fuse(packet)
    assert result.intent == "llm_route"


def test_multiword_phrase_the_app_triggers_llm_route(fusion):
    packet = _packet("minimize the app please")
    result = fusion.fuse(packet)
    assert result.intent == "llm_route"


# ── fuse() mutates and returns the same packet ────────────

def test_fuse_returns_same_packet_instance(fusion):
    packet = _packet("close it")
    result = fusion.fuse(packet)
    assert result is packet


def test_fuse_preserves_entities_and_other_fields(fusion):
    packet = _packet("close it")
    packet.entities = {"target": "notepad"}
    result = fusion.fuse(packet)
    assert result.entities == {"target": "notepad"}


# ── snapshot parameter: no merge occurs (documents real behavior) ─

def test_snapshot_argument_does_not_populate_context_snapshot(fusion):
    """fuse() accepts an optional `snapshot`, but the implementation never
    assigns it onto the packet -- packet.context_snapshot stays untouched."""
    packet = _packet("open notepad")
    snapshot = ContextSnapshot(active_app="chrome", active_window_title="Chrome")
    result = fusion.fuse(packet, snapshot=snapshot)
    assert result.context_snapshot is None


def test_snapshot_argument_does_not_overwrite_existing_context_snapshot(fusion):
    """Even when the packet already carries a context_snapshot and a
    *different*, conflicting snapshot is passed to fuse(), the packet's
    existing context_snapshot is left untouched (no merge/overwrite)."""
    packet = _packet("open notepad")
    original = ContextSnapshot(active_app="notepad", active_window_title="Untitled - Notepad")
    packet.context_snapshot = original
    conflicting = ContextSnapshot(active_app="chrome", active_window_title="Google Chrome")

    result = fusion.fuse(packet, snapshot=conflicting)

    assert result.context_snapshot is original
    assert result.context_snapshot.active_app == "notepad"


def test_fuse_with_no_snapshot_argument_still_detects_ambiguity(fusion):
    packet = _packet("do that again")
    result = fusion.fuse(packet, snapshot=None)
    assert result.intent == "llm_route"
