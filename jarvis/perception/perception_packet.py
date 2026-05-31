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
class GoalModel:
    """
    Structured representation of a parsed user goal.

    Produced by GoalUnderstandingLayer (LLM Call 1) and consumed by
    GroundingLayer → KnowledgeGapEngine → CapabilityPlanner.
    """
    primary_goal: str = ""                              # Target end-state description
    intents: list = field(default_factory=list)          # Abstract intent labels (e.g. web_search, content_generation)
    constraints: list = field(default_factory=list)      # User constraints (e.g. "avoid command-line")
    target_app: Optional[str] = None                     # Explicit or inferred target application
    required_knowledge: list = field(default_factory=list)  # Knowledge prerequisites identified
    confidence: float = 1.0                              # Goal extraction confidence
    resolved_references: dict = field(default_factory=dict)  # Pronoun/coreference resolutions from grounding
    knowledge_gaps: list = field(default_factory=list)    # Missing parameters detected by KnowledgeGapEngine
    is_complete: bool = True                              # False if knowledge gaps require clarification


@dataclass
class PerceptionPacket:
    """
    Fully parsed utterance with intent, entities, and context.
    Created by NLU and consumed by Orchestrator.
    """
    utterance: Utterance
    intent: str = ""               # e.g. "open_app", "navigate_location", "set_volume"
    entities: dict = field(default_factory=dict)  # e.g. {"target": "wifi", "level": 80}
    app_context: str = ""          # Active window/app name at the time
    compound: bool = False         # Does this contain multiple instructions?
    sub_commands: list = field(default_factory=list) # List of sub-command dicts
    memory_context: str = ""       # RAG snippets from MemoryManager
    raw_plan_override: list = field(default_factory=list)  # pre-built plan (from memory recall)
    context_snapshot: Optional[ContextSnapshot] = None # NEW
    override_prompt: Optional[str] = None  # If set, Planner uses this text for the LLM call instead of packet.text
    safe_mode: bool = False  # True if cognitive request inside quotes should not execute
    intent_category: str = "EXECUTION" # e.g. EXECUTION, EDUCATIONAL, HYPOTHETICAL, CAPABILITY, TEXT_ANALYSIS
    intent_confidence: float = 1.0
    entity_confidence: float = 1.0
    goal_model: Optional[GoalModel] = None  # Structured goal from GoalUnderstandingLayer

    @property
    def text(self) -> str:
        return self.utterance.text

    @property
    def needs_confirmation(self) -> bool:
        """True if voice confidence is too low to act without confirming."""
        return self.utterance.source == "voice" and self.utterance.confidence < 0.70
