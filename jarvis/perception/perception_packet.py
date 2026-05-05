"""
PerceptionPacket & ContextSnapshot
====================================
Dataclasses carrying all information from a single user utterance
through the Jarvis v2 pipeline.

Flow:
    InputAdapter → Utterance
    NLU          → PerceptionPacket  (adds intent, entities, app_context)
    Orchestrator → Plan              (adds skill calls)
    VerificationLoop → SkillResult   (adds outcome)
"""

from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from jarvis.perception.ui_inspector import UISnapshot


@dataclass
class Utterance:
    """Raw user input before NLU processing."""
    text: str
    source: str = "text"           # text | voice | api | telegram
    confidence: float = 1.0        # speech recognition confidence (1.0 for text)
    session_id: str = ""
    metadata: dict = field(default_factory=dict) # e.g. {"chat_id": 123}


@dataclass
class ContextSnapshot:
    """Current system context at the moment of the utterance."""
    active_app: str = ""           # e.g. "settings", "notepad", "chrome"
    active_window_title: str = ""  # Raw window title
    active_node_id: str = ""       # Last known graph node (e.g. "settings.display")
    screen_hash: str = ""          # MD5 of current UIState (from StateHarvester)
    ui_snapshot: Optional["UISnapshot"] = None   # NEW — live UI tree
    state_sig: str = ""                          # NEW — short stable state ID
    state_origin: str = ""                       # NEW — USER | JARVIS
    prior_action: str = ""                       # NEW — last traceable action
    interface: str = "text"                      # NEW — text | telegram | voice


@dataclass
class PerceptionPacket:
    """
    Fully parsed utterance with intent, entities, and context.
    Created by NLU and consumed by Orchestrator.
    """
    utterance: Utterance
    intent: str = ""               # e.g. "open_app", "navigate_location", "set_volume"
    entities: dict = field(default_factory=dict)  # e.g. {"target": "wifi", "level": 80}
    app_context: str = ""          # derived active app from context
    sub_location: str = ""         # e.g. "wifi" in "open settings wifi"
    compound: bool = False         # True if multiple intents detected ("open notepad and type hello")
    sub_commands: list = field(default_factory=list)  # list of (intent, entities) for compound
    memory_context: str = ""       # RAG snippets from MemoryManager
    raw_plan_override: list = field(default_factory=list)  # pre-built plan (from memory recall)
    context_snapshot: Optional[ContextSnapshot] = None # NEW
    override_prompt: Optional[str] = None  # If set, Planner uses this text for the LLM call instead of packet.text

    @property
    def text(self) -> str:
        return self.utterance.text

    @property
    def needs_confirmation(self) -> bool:
        """True if voice confidence is too low to act without confirming."""
        return self.utterance.source == "voice" and self.utterance.confidence < 0.70
