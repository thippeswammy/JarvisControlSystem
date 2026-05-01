"""
Semantic Memory Layer
======================
Stores facts about the world: keyboard shortcuts, hardware info, app knowledge.

Pre-seeded with common shortcuts for Chrome, VS Code, Windows.
New facts are written by ReactiveLearner when shortcuts are discovered.

Usage:
    sem = SemanticMemory()
    facts = sem.query("chrome")          # → list[Fact]
    ctx = sem.as_llm_context("vscode")  # → compact string for LLM
"""
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Fact:
    id: str
    label: str
    value: str
    category: str  # keyboard_shortcut | hardware | software | path
    source: str = "seeded"  # seeded | learned | user-defined


# Pre-seeded facts about common software
_SEED_FACTS: list[Fact] = [
    Fact("fact.chrome.devtools",   "Open Dev Tools in Chrome", "F12 or Ctrl+Shift+I", "keyboard_shortcut"),
    Fact("fact.chrome.address_bar","Focus Chrome Address Bar", "Ctrl+L or F6", "keyboard_shortcut"),
    Fact("fact.vscode.command_palette", "VS Code Command Palette", "Ctrl+Shift+P", "keyboard_shortcut"),
    Fact("fact.vscode.terminal",   "VS Code Integrated Terminal", "Ctrl+`", "keyboard_shortcut"),
    Fact("fact.windows.search",    "Windows Search", "Win+S", "keyboard_shortcut"),
    Fact("fact.windows.run",       "Run Dialog", "Win+R", "keyboard_shortcut"),
    Fact("fact.windows.settings",  "Windows Settings", "Win+I", "keyboard_shortcut"),
    Fact("fact.windows.desktop",   "Show Desktop", "Win+D", "keyboard_shortcut"),
    Fact("fact.windows.lock",      "Lock Screen", "Win+L", "keyboard_shortcut"),
    Fact("fact.notepad.save",      "Save in Notepad", "Ctrl+S", "keyboard_shortcut"),
]


class SemanticMemory:
    """Stores facts about apps and system. Full impl in Phase 8."""

    def __init__(self):
        self._facts: dict[str, Fact] = {f.id: f for f in _SEED_FACTS}

    def query(self, keywords: str) -> list[Fact]:
        kw = keywords.lower()
        return [
            f for f in self._facts.values()
            if kw in f.label.lower() or kw in f.value.lower() or kw in f.id.lower()
        ]

    def save_fact(self, fact: Fact) -> None:
        self._facts[fact.id] = fact
        logger.info(f"[SemanticMemory] Saved fact: {fact.id}")

    def as_context(self, keywords: str = "", top_n: int = 5) -> str:
        facts = self.query(keywords) if keywords else list(self._facts.values())[:top_n]
        return "\n".join(f"- {f.label}: {f.value}" for f in facts[:top_n])

    def as_llm_context(self, command: str = "", top_n: int = 5) -> str:
        """
        Alias for as_context — called by RAGContextBuilder.
        Returns a compact facts string for LLM injection.
        """
        facts = self.query(command) if command else list(self._facts.values())[:top_n]
        if not facts:
            return "(no semantic facts)"
        return "\n".join(f"- {f.label}: {f.value}" for f in facts[:top_n])

