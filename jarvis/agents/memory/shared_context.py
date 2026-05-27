"""
Shared Agent Context
====================
Cross-agent shared state backed by the global ``MemoryManager``.

Agents use this to *observe* facts into global memory and *recall*
relevant context from the graph.  A lightweight ``_world`` dict holds
transient world-state that doesn't warrant a full graph write.

Usage::

    from jarvis.memory.memory_manager import MemoryManager
    ctx = SharedAgentContext(MemoryManager())
    ctx.observe("User prefers dark mode", confidence=0.9)
    hits = ctx.recall("display preferences", limit=3)
    ctx.set_world_state("active_app", "notepad")
"""

import logging
from typing import Any

from jarvis.memory.memory_manager import MemoryManager

logger = logging.getLogger(__name__)


class SharedAgentContext:
    """Cross-agent shared memory backed by the global MemoryManager."""

    def __init__(self, memory: MemoryManager) -> None:
        self._memory = memory
        self._world: dict[str, Any] = {}

    # ── Write ─────────────────────────────────────────

    def observe(self, fact: str, confidence: float = 0.8) -> None:
        """Log an observed fact to global memory.

        The fact is stored as a descriptive string and is available for
        later semantic recall by any agent.

        Parameters
        ----------
        fact:
            Human-readable observation (e.g. "User prefers dark mode").
        confidence:
            Certainty of the observation, 0.0–1.0.
        """
        logger.info(
            f"[SharedContext] observe (conf={confidence:.2f}): {fact!r}"
        )
        # Store as an episodic context string the memory system can index.
        # We piggy-back on get_relevant_context / search_edges which do
        # fuzzy + semantic matching on edge triggers, so the fact itself
        # becomes a "trigger" for future recall.
        from jarvis.memory.graph_db import GraphNode, GraphEdge

        # Ensure observation and world nodes exist to satisfy foreign key relationships
        self._memory.save_node(GraphNode(
            id="observation",
            app_id="global",
            type="APP",
            label="Observation Source"
        ))
        self._memory.save_node(GraphNode(
            id="world",
            app_id="global",
            type="APP",
            label="World State"
        ))

        edge = GraphEdge(
            id=f"obs_{hash(fact) & 0xFFFFFFFF:08x}",
            from_id="observation",
            to_id="world",
            triggers=[fact],
            steps=[],
            confidence=confidence,
        )
        self._memory.save_edge(edge)

    # ── Read ──────────────────────────────────────────

    def recall(self, query: str, limit: int = 5) -> list[str]:
        """Semantic search from global memory.

        Returns up to *limit* edge trigger descriptions ranked by
        relevance.
        """
        results = self._memory.search_edges(query, limit=limit)
        descriptions: list[str] = []
        for edge, _score in results:
            desc = getattr(edge, "description", None) or ", ".join(edge.triggers[:3])
            descriptions.append(desc)
        logger.debug(
            f"[SharedContext] recall({query!r}) → {len(descriptions)} hits"
        )
        return descriptions

    # ── World state ───────────────────────────────────

    def get_world_state(self) -> dict:
        """Return memory stats merged with any active transient state."""
        stats = self._memory.get_stats()
        return {**stats, "transient": dict(self._world)}

    def set_world_state(self, key: str, value: Any) -> None:
        """Store a transient world-state key/value pair."""
        self._world[key] = value
        logger.debug(f"[SharedContext] world[{key}] = {value!r}")
