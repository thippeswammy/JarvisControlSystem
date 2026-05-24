"""
Agent Local Memory
==================
Per-agent ephemeral memory: scratchpad, task state, execution log, and
episodic history.  Each agent instance gets its own ``AgentLocalMemory``
so concurrent agents never collide.

Usage::

    mem = AgentLocalMemory(agent_name="search_agent")
    mem.note("query", "weather today")
    mem.log_step("Sent request to search API")
    mem.log_episode("search_web", success=True, result="3 results")
    context = mem.to_context()   # inject into LLM prompt
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AgentLocalMemory:
    """Isolated working memory for a single agent instance."""

    agent_name: str
    episodic: list[dict] = field(default_factory=list)
    scratchpad: dict = field(default_factory=dict)
    task_state: dict = field(default_factory=dict)
    exec_log: list[str] = field(default_factory=list)

    # ── Scratchpad helpers ────────────────────────────

    def note(self, key: str, value: Any) -> None:
        """Store a key/value pair in the scratchpad."""
        self.scratchpad[key] = value
        logger.debug(f"[{self.agent_name}] note: {key}={value!r}")

    def recall(self, key: str) -> Any:
        """Retrieve a value from the scratchpad, or ``None`` if missing."""
        return self.scratchpad.get(key)

    # ── Execution log ─────────────────────────────────

    def log_step(self, msg: str) -> None:
        """Append a timestamped step to the execution log."""
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        entry = f"[{ts}] {msg}"
        self.exec_log.append(entry)
        logger.debug(f"[{self.agent_name}] step: {entry}")

    # ── Episodic history ──────────────────────────────

    def log_episode(self, command: str, success: bool, result: str = "") -> None:
        """Record a completed action as an episodic memory entry."""
        episode = {
            "command": command,
            "success": success,
            "result": result,
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        self.episodic.append(episode)
        logger.debug(f"[{self.agent_name}] episode: {episode}")

    # ── Lifecycle ─────────────────────────────────────

    def clear(self) -> None:
        """Reset scratchpad, task_state, and exec_log.  Episodic is kept."""
        self.scratchpad.clear()
        self.task_state.clear()
        self.exec_log.clear()
        logger.info(f"[{self.agent_name}] Local memory cleared (episodic preserved)")

    # ── LLM context serialization ─────────────────────

    def to_context(self, max_episodes: int = 5) -> str:
        """Return a formatted string of recent episodic + scratchpad for LLM context.

        Parameters
        ----------
        max_episodes:
            Maximum number of recent episodes to include.
        """
        parts: list[str] = [f"[Agent: {self.agent_name}]"]

        # Recent episodes
        recent = self.episodic[-max_episodes:] if self.episodic else []
        if recent:
            parts.append("Recent episodes:")
            for ep in recent:
                status = "✓" if ep["success"] else "✗"
                parts.append(
                    f"  {status} {ep['command']}"
                    + (f" → {ep['result']}" if ep.get("result") else "")
                )

        # Scratchpad
        if self.scratchpad:
            parts.append("Scratchpad:")
            for k, v in self.scratchpad.items():
                parts.append(f"  {k}: {v!r}")

        return "\n".join(parts)
