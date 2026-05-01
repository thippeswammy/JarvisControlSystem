"""
RAG Context Builder
===================
Assembles the LLM context from all 5 memory layers within a token budget.

Design spec (Part 7):
  'LLM context budget management: allocate token budget per layer
   (procedural gets most)'

Budget allocation (default total: 400 tokens):
  - Procedural (graph edges): 200 tokens  ← most important
  - Episodic (recent history): 80 tokens
  - Semantic (facts):          60 tokens
  - Preference (habits):       40 tokens
  - Task (active goals):       40 tokens

Usage:
    builder = RAGContextBuilder(memory, episodic, semantic, preference, task)
    context_str = builder.build(command="open display settings", app_id="settings")
    # → passed as part of LLM system prompt
"""
import logging
from typing import Optional

from jarvis.memory.memory_manager import MemoryManager
from jarvis.memory.layers.episodic import EpisodicMemory
from jarvis.memory.layers.semantic import SemanticMemory
from jarvis.memory.layers.preference import PreferenceMemory
from jarvis.memory.layers.task import TaskMemory

logger = logging.getLogger(__name__)

# Rough token budget per section (1 token ≈ 4 chars)
_BUDGET = {
    "procedural": 200,
    "episodic":    80,
    "semantic":    60,
    "preference":  40,
    "task":        40,
}


def _truncate(text: str, max_tokens: int) -> str:
    """Truncate text to approximately max_tokens tokens."""
    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + "…"


class RAGContextBuilder:
    """
    Builds a multi-layer LLM context string within a token budget.

    Each layer contributes a section. Procedural memory gets the largest budget
    since it directly encodes how to navigate to the target.
    """

    def __init__(
        self,
        memory: MemoryManager,
        episodic: Optional[EpisodicMemory] = None,
        semantic: Optional[SemanticMemory] = None,
        preference: Optional[PreferenceMemory] = None,
        task: Optional[TaskMemory] = None,
    ):
        self._memory = memory
        self._episodic = episodic
        self._semantic = semantic
        self._preference = preference
        self._task = task

    def build(
        self,
        command: str,
        app_id: Optional[str] = None,
        total_budget: int = 400,
    ) -> str:
        """
        Assemble context from all available layers, respecting token budgets.
        Returns a formatted multi-section string for LLM injection.
        """
        # Scale budgets if total differs from default
        scale = total_budget / 420  # 420 = sum of defaults
        budgets = {k: max(20, int(v * scale)) for k, v in _BUDGET.items()}

        sections: list[str] = []

        # 1. Procedural memory (graph edges) — highest priority
        proc_ctx = self._memory.get_relevant_context(command, app_id=app_id, top_n=4)
        if proc_ctx and proc_ctx != "(no relevant memory)":
            sections.append(
                "=== Procedural Memory (Navigation Paths) ===\n"
                + _truncate(proc_ctx, budgets["procedural"])
            )

        # 2. Episodic memory (recent history)
        if self._episodic:
            ep_ctx = self._episodic.as_llm_context(max_sessions=3, top_n=5)
            if ep_ctx and "(no episodic" not in ep_ctx:
                sections.append(
                    "=== Episodic Memory (Recent History) ===\n"
                    + _truncate(ep_ctx, budgets["episodic"])
                )

        # 3. Semantic memory (facts about apps/system)
        if self._semantic:
            sem_ctx = self._semantic.as_llm_context(command)
            if sem_ctx and "(no semantic" not in sem_ctx:
                sections.append(
                    "=== Semantic Memory (Facts) ===\n"
                    + _truncate(sem_ctx, budgets["semantic"])
                )

        # 4. Preference memory (user habits)
        if self._preference:
            pref_ctx = self._preference.as_llm_context()
            if pref_ctx and "(no preference" not in pref_ctx:
                sections.append(
                    "=== User Preferences ===\n"
                    + _truncate(pref_ctx, budgets["preference"])
                )

        # 5. Task memory (active goals)
        if self._task:
            task_ctx = self._task.as_llm_context()
            if task_ctx and "(no active tasks)" not in task_ctx:
                sections.append(
                    "=== Active Tasks ===\n"
                    + _truncate(task_ctx, budgets["task"])
                )

        if not sections:
            return "(no relevant memory context)"

        return "\n\n".join(sections)
