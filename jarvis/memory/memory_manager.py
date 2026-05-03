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
from jarvis.memory.semantic_encoder import SemanticEncoder
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
        self._encoder = SemanticEncoder()
        self._trigger_embeddings: dict[str, list[float]] = {}
        logger.info(f"[MemoryManager] DB: {db_path}")
        self._warm_embedding_cache()

    def _warm_embedding_cache(self) -> None:
        """Embed all known triggers at startup into RAM for zero-latency routing."""
        logger.info("[MemoryManager] Warming semantic embedding cache...")
        count = 0
        apps = self._db.list_apps()
        for aid in apps:
            for edge in self._db.get_edges_for_app(aid):
                for trigger in edge.triggers:
                    trigger_clean = trigger.lower().strip()
                    if trigger_clean not in self._trigger_embeddings:
                        vec = self._encoder.embed(trigger_clean)
                        if vec:
                            self._trigger_embeddings[trigger_clean] = vec
                            count += 1
        logger.info(f"[MemoryManager] Cached {count} embeddings in RAM.")

    def set_pathfinder(self, pathfinder) -> None:
        """Inject the A* pathfinder (Phase 4). Called by Orchestrator on startup."""
        self._pathfinder = pathfinder

    # ── Recall ───────────────────────────────────────

    def recall(
        self,
        command: str,
        app_id: Optional[str] = None,
        command_threshold: float = 0.55,
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

        # Fallback to Hybrid Search (Exact Match -> Semantic Vector Search)
        return self._hybrid_recall(command, app_id, command_threshold)

    def _hybrid_recall(
        self,
        command: str,
        app_id: Optional[str],
        threshold: float,
    ) -> Optional[MemoryPath]:
        cmd_lower = command.lower().strip()
        apps = [app_id] if app_id else self._db.list_apps()

        # Step 1: O(1) Exact Match (Fast-Lane)
        for aid in apps:
            for edge in self._db.get_edges_for_app(aid):
                for trigger in edge.triggers:
                    if cmd_lower == trigger.lower().strip():
                        logger.info(f"[MemoryManager] Exact match (1.0) → {edge.id}")
                        return MemoryPath(edges=[edge], source_app=edge.from_id.split(".")[0])

        # Step 2: Semantic Vector Search
        cmd_vec = self._encoder.embed(cmd_lower)
        if not cmd_vec:
            logger.warning("[MemoryManager] Failed to embed command for semantic search.")
            return None

        best_edge: Optional[GraphEdge] = None
        best_score = 0.0

        for aid in apps:
            edges = self._db.get_edges_for_app(aid)
            for edge in edges:
                for trigger in edge.triggers:
                    trigger_clean = trigger.lower().strip()
                    trigger_vec = self._trigger_embeddings.get(trigger_clean)
                    
                    if trigger_vec:
                        sim = self._encoder.cosine_similarity(cmd_vec, trigger_vec)
                        # Optionally log all scores to help calibrate threshold
                        # logger.debug(f"[Semantic] '{cmd_lower}' vs '{trigger_clean}' = {sim:.3f}")
                        if sim > best_score:
                            best_score = sim
                            best_edge = edge

        if best_edge and best_score >= threshold:
            logger.info(f"[MemoryManager] Semantic match: {best_score:.3f} → {best_edge.id}")
            return MemoryPath(edges=[best_edge], source_app=best_edge.from_id.split(".")[0])

        logger.debug(f"[MemoryManager] No recall match (best score {best_score:.3f} < {threshold}) for: {command!r}")
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

        cmd_vec = self._encoder.embed(cmd_lower)
        apps = [app_id] if app_id else self._db.list_apps()
        
        for aid in apps:
            for edge in self._db.get_edges_for_app(aid):
                if not edge.triggers:
                    continue
                
                # If embedding fails, fallback to basic SequenceMatcher
                if cmd_vec:
                    trigger_scores = []
                    for t in edge.triggers:
                        t_vec = self._trigger_embeddings.get(t.lower().strip())
                        if t_vec:
                            trigger_scores.append(self._encoder.cosine_similarity(cmd_vec, t_vec))
                        else:
                            trigger_scores.append(0.0)
                else:
                    trigger_scores = [
                        SequenceMatcher(None, cmd_lower, t.lower()).ratio()
                        for t in edge.triggers
                    ]

                best_trigger = max(trigger_scores) if trigger_scores else 0.0
                if best_trigger < 0.30:  # raised slightly for cosine sim
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
