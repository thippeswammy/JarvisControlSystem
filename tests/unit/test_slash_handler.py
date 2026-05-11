"""
tests/unit/test_slash_handler.py
=================================
Unit tests for jarvis.gateway.slash_handler.SlashHandler.
"""
import pytest
from unittest.mock import MagicMock
from jarvis.gateway.slash_handler import SlashHandler

pytestmark = pytest.mark.unit


@pytest.fixture
def handler(fake_session, fake_gateway):
    """A SlashHandler wired with fake session and gateway."""
    h = SlashHandler(session=fake_session, gateway=fake_gateway)
    return h


# ── is_slash ─────────────────────────────────────────────────

def test_is_slash_true(handler):
    assert handler.is_slash("/status") is True

def test_is_slash_with_leading_space(handler):
    assert handler.is_slash("  /help") is True

def test_is_slash_false_for_plain_text(handler):
    assert handler.is_slash("open notepad") is False

def test_is_slash_false_for_empty(handler):
    assert handler.is_slash("") is False


# ── handle — non-slash passthrough ───────────────────────────

def test_handle_returns_none_for_plain_text(handler):
    result = handler.handle("open notepad")
    assert result is None


# ── /help ────────────────────────────────────────────────────

def test_help_lists_all_commands(handler):
    result = handler.handle("/help")
    assert result is not None
    assert "/status" in result
    assert "/reset" in result
    assert "/memory" in result
    assert "/logs" in result
    assert "/whoami" in result


# ── /status ──────────────────────────────────────────────────

def test_status_calls_gateway(handler, fake_gateway):
    result = handler.handle("/status")
    fake_gateway.status.assert_called_once()
    assert "JARVIS Status" in result
    assert "cli" in result


# ── /whoami ──────────────────────────────────────────────────

def test_whoami_returns_session_info(handler, fake_session):
    result = handler.handle("/whoami")
    assert fake_session.id in result
    assert fake_session.channel in result
    assert fake_session.user_id in result


# ── /reset ───────────────────────────────────────────────────

def test_reset_clears_episodic_memory(handler, fake_session):
    result = handler.handle("/reset")
    fake_session.episodic.clear.assert_called_once()
    assert "reset" in result.lower()


# ── /memory ──────────────────────────────────────────────────

def test_memory_no_args_shows_usage(handler):
    result = handler.handle("/memory")
    assert "Usage" in result

def test_memory_status_calls_get_stats(handler, fake_gateway):
    result = handler.handle("/memory status")
    fake_gateway.session_mgr.memory.get_stats.assert_called_once()
    assert "Nodes" in result or "nodes" in result.lower()

def test_memory_search_no_results(handler, fake_gateway):
    fake_gateway.session_mgr.memory.search_edges.return_value = []
    result = handler.handle("/memory search notepad")
    assert "No memory found" in result or "notepad" in result.lower()

def test_memory_unknown_subcommand(handler):
    result = handler.handle("/memory foobar")
    assert "Unknown" in result


# ── unknown command ───────────────────────────────────────────

def test_unknown_command_returns_message(handler):
    result = handler.handle("/nonexistent")
    assert "Unknown command" in result
    assert "/help" in result
