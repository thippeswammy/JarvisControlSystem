"""
LLM Interface
=============
Abstract base class for all LLM backends.
Every backend implements this single contract.

The Plan return type is a list of SkillCall dicts:
    [
        {"skill": "open_app", "params": {"target": "notepad"}},
        {"skill": "type_text", "params": {"text": "hello world"}},
    ]
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SkillCallSpec:
    """A single planned action from the LLM."""
    skill: str
    params: dict = field(default_factory=dict)


Plan = list[SkillCallSpec]


class LLMInterface(ABC):
    """
    Abstract base for all LLM backends (Ollama, OpenAI, Tunneled, Mock).

    Every backend must implement:
      - plan(prompt, context) → Plan
      - health_check() → bool
      - name property
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable backend name (e.g. 'local/ollama', 'openai', 'mock')."""

    @abstractmethod
    def health_check(self) -> bool:
        """
        Returns True if this backend is currently reachable and ready.
        Must be fast (<2s). Called from health monitor thread.
        """

    @abstractmethod
    def plan(self, prompt: str, memory_context: str = "") -> Optional[Plan]:
        """
        Given a user command + memory context, return an ordered Plan.
        Returns None if the backend cannot produce a valid plan.

        Args:
            prompt: The raw user command (e.g. "open display settings")
            memory_context: RAG-retrieved memory snippets for context

        Returns:
            Plan (list of SkillCallSpec), or None on failure / uncertainty.
        """

    def build_system_prompt(self) -> str:
        """
        Returns the Jarvis identity + structured output instructions.
        Shared across all backends.
        """
        return (
            "You are Jarvis, a Windows desktop automation assistant.\n"
            "Given a user command and memory context, output a JSON plan as an array of steps.\n"
            "Each step: {\"skill\": \"skill_name\", \"params\": {...}}\n"
            "Available skills: open_app, close_app, navigate_location, click_element, "
            "type_text, press_key, set_volume, set_brightness, minimize_window, "
            "maximize_window, search_web, session_activate, session_deactivate.\n"
            "Rules:\n"
            "  - Output ONLY valid JSON array. No explanation, no markdown.\n"
            "  - Use 1-3 steps maximum. Simple commands = 1 step.\n"
            "  - If uncertain, output: [{\"skill\": \"ask_user\", \"params\": {\"reason\": \"...\"}}]\n"
            "  - Temperature is 0.1. Be deterministic.\n"
        )
