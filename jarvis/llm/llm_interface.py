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


import os
from pathlib import Path

@dataclass
class SkillCallSpec:
    """A single planned action from the LLM."""
    skill: str
    params: dict = field(default_factory=dict)


Plan = list[SkillCallSpec]

@dataclass
class LLMDecision:
    """The unified decision from the LLM Brain."""
    type: str  # "chat", "plan", "mixed", "clarify"
    message: Optional[str] = None
    steps: Optional[Plan] = None
    question: Optional[str] = None


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

    @abstractmethod
    def decide(self, prompt: str, context: str = "") -> Optional[LLMDecision]:
        """
        Given a user command and full context block, make a unified decision.
        Returns None if the backend cannot produce a valid decision.
        """

    def build_system_prompt(self) -> str:
        """
        Returns the Jarvis identity + structured output instructions.
        Loads from external Markdown file if available.
        """
        try:
            # Resolve path relative to this file
            prompt_path = Path(__file__).parent / "prompts" / "system_instructions.md"
            if prompt_path.exists():
                return prompt_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"[LLMInterface] Failed to load external prompt: {e}")

        # Emergency Fallback (minimal identity)
        return (
            "You are Jarvis, a Windows desktop automation assistant.\n"
            "Output ONLY a valid JSON array of steps: [{\"skill\": \"name\", \"params\": {...}}]\n"
            "Available skills: open_app, close_app, navigate_location, click_element, "
            "type_text, press_key, set_volume, set_brightness, search_web, ask_user.\n"
        )
