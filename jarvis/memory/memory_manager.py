"""
Memory Manager (v2.1)
=====================
Public API for all memory operations.
Replaces the v1 MemoryManager (flat .md file approach).

All reads/writes go through GraphDB (SQLite).
Pathfinding is delegated to graph_pathfinder (Phase 4).
For Phase 2, recall falls back to fuzzy string matching on edge triggers.
"""

import logging
import os
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional

from jarvis.memory.graph_db import GraphDB, GraphNode, GraphEdge
from jarvis.memory.state_harvester import StateHarvester

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_DB_DEFAULT = str(_PROJECT_ROOT / "memory" / "jarvis.db")


@dataclass
class MemoryPath:
    """An ordered list of edges representing a navigation path."""
    edges: list[GraphEdge] = field(default_factory=list)
    source_app: str = ""

    @property
    def steps(self) -> list[str]:
        """Flatten all edge steps into a single ordered list."""
        result = []
        for edge in self.edges:
            result.extend(edge.steps)
        return result

    @property
    def confidence(self) -> float:
        if not self.edges:
            return 0.0
        return min(e.confidence for e in self.edges)


class MemoryManager:
    """
    Public API for Jarvis v2.1 memory.

    Usage:
        mem = MemoryManager()
        path = mem.recall("open wifi settings", snapshot)
        if path:
            for step in path.steps:
                engine.process(step)
        mem.save_edge(edge)
    """

    def __init__(self, db_path: str = _DB_DEFAULT):
        if db_path != ":memory:":
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._db = GraphDB(db_path)
        self._harvester = StateHarvester()
        self._pathfinder = None  # Injected in Phase 4
        logger.info(f"[MemoryManager] DB: {db_path}")

    def set_pathfinder(self, pathfinder) -> None:
        """Inject the A* pathfinder (Phase 4). Called by Orchestrator on startup."""
        self._pathfinder = pathfinder

    # ── Recall ───────────────────────────────────────

    def recall(
        self,
        command: str,
        app_id: Optional[str] = None,
        command_threshold: float = 0.60,
    ) -> Optional[MemoryPath]:
        """
        Find a known path for this command.

        Phase 2: Fuzzy trigger matching on edge triggers.
        Phase 4: Full A* pathfinding replaces this.

        Returns MemoryPath or None.
        """
        # Try A* first if pathfinder is available
        if self._pathfinder and app_id:
            path = self._pathfinder.find_path_by_command(command, app_id)
            if path:
                return path

        # Fuzzy fallback: scan all edges for trigger matches
        return self._fuzzy_recall(command, app_id, command_threshold)

    def _fuzzy_recall(
        self,
        command: str,
        app_id: Optional[str],
        threshold: float,
    ) -> Optional[MemoryPath]:
        cmd_lower = command.lower().strip()
        best_edge: Optional[GraphEdge] = None
        best_score = 0.0

        apps = [app_id] if app_id else self._db.list_apps()
        for aid in apps:
            edges = self._db.get_edges_for_app(aid)
            for edge in edges:
                for trigger in edge.triggers:
                    sim = SequenceMatcher(None, cmd_lower, trigger.lower()).ratio()
                    if sim > best_score:
                        best_score = sim
                        best_edge = edge

        if best_edge and best_score >= threshold:
            logger.info(f"[MemoryManager] Fuzzy recall match: {best_score:.2f} → {best_edge.id}")
            return MemoryPath(edges=[best_edge], source_app=best_edge.from_id.split(".")[0])

        logger.debug(f"[MemoryManager] No recall match for: {command!r}")
        return None

    # ── Save ─────────────────────────────────────────

    def save_edge(self, edge: GraphEdge) -> None:
        """Save or update an edge in the graph database."""
        self._db.save_edge(edge)
        logger.info(f"[MemoryManager] Saved edge: {edge.id}")

    def save_node(self, node: GraphNode) -> None:
        """Save or update a node."""
        self._db.save_node(node)

    def record_success(self, edge_id: str) -> None:
        """Called by ReactiveLearner after verified success."""
        self._db.update_edge_confidence(
            edge_id, success=True,
            boost=0.02,
        )

    def record_failure(self, edge_id: str) -> None:
        """Called by VerificationLoop after mismatch or exception."""
        self._db.update_edge_confidence(
            edge_id, success=False,
            decay=0.05,
        )

    # ── Context for LLM ──────────────────────────────

    def get_relevant_context(
        self,
        command: str,
        app_id: Optional[str] = None,
        top_n: int = 4,
    ) -> str:
        """
        RAG: return top-N relevant edge descriptions for LLM injection.
        Scores by trigger similarity + confidence.
        """
        cmd_lower = command.lower().strip()
        scored: list[tuple[float, GraphEdge]] = []

        apps = [app_id] if app_id else self._db.list_apps()
        for aid in apps:
            for edge in self._db.get_edges_for_app(aid):
                trigger_scores = [
                    SequenceMatcher(None, cmd_lower, t.lower()).ratio()
                    for t in edge.triggers
                ] if edge.triggers else [0.0]
                best_trigger = max(trigger_scores)
                if best_trigger < 0.15:
                    continue
                score = best_trigger * 0.7 + edge.confidence * 0.3
                scored.append((score, edge))

        scored.sort(key=lambda x: x[0], reverse=True)

        parts = []
        for _, edge in scored[:top_n]:
            steps_str = " → ".join(edge.steps) if edge.steps else "(no steps)"
            triggers_str = ", ".join(edge.triggers[:3]) if edge.triggers else "?"
            parts.append(
                f"[Memory] '{triggers_str}' → {steps_str} "
                f"(confidence={edge.confidence:.2f})"
            )

        return "\n".join(parts) if parts else "(no relevant memory)"

    # ── Graph access ─────────────────────────────────

    def get_db(self) -> GraphDB:
        """Direct DB access (used by pathfinder, layers, migration)."""
        return self._db

    def close(self) -> None:
        self._db.close()
