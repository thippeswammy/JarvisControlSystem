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
            db_dir = os.path.dirname(db_path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)
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
        state_sig: str = "",
        command_threshold: float = 0.55,
    ) -> Optional[MemoryPath]:
        """
        Find a known path for this command.

        Pass 1: State-keyed match (A* or exact trigger match with matching state_sig)
        Pass 2: State-agnostic fallback (semantic search across all edges)

        Returns MemoryPath or None.
        """
        # Pass 1: A* with state knowledge if pathfinder is available
        if self._pathfinder and app_id:
            # We assume A* handles its own state logic if it's evolved, 
            # for now pathfinding is app-level
            path = self._pathfinder.find_path_by_command(command, app_id)
            if path:
                return path

        # Pass 1 & 2 combined in hybrid search
        return self._hybrid_recall(command, app_id, state_sig, command_threshold)

    def _hybrid_recall(
        self,
        command: str,
        app_id: Optional[str],
        state_sig: str,
        threshold: float,
    ) -> Optional[MemoryPath]:
        cmd_lower = command.lower().strip()
        apps = set([app_id]) if app_id else set(self._db.list_apps())
        apps.add("global")
        scored_edges: list[tuple[float, GraphEdge, str]] = []

        # Step 1: O(1) Exact Match with State Bias
        for aid in apps:
            edges = self._db.get_edges_for_app(aid)
            for edge in edges:
                for trigger in edge.triggers:
                    if cmd_lower == trigger.lower().strip():
                        # If state signature matches, it's a perfect hit
                        if state_sig and edge.starting_state_sig == state_sig:
                            logger.info(f"[MemoryManager] State-Keyed Exact match (1.0) → {edge.id}")
                            return MemoryPath(edges=[edge], source_app=aid)
                        # Otherwise log it as potential but keep searching for state match
                        scored_edges.append((1.0, edge, aid))

        # Step 2: Semantic Vector Search
        cmd_vec = self._encoder.embed(cmd_lower)
        if not cmd_vec:
            logger.warning("[MemoryManager] Failed to embed command for semantic search.")
            # If we had any exact matches (without state match), return best one now
            if scored_edges:
                scored_edges.sort(key=lambda x: x[0], reverse=True)
                return MemoryPath(edges=[scored_edges[0][1]], source_app=scored_edges[0][2])
            return None

        # scored_edges already might have 1.0 matches from above
        # (avoid re-scoring exact matches)
        existing_edge_ids = {e[1].id for e in scored_edges}

        for aid in apps:
            edges = self._db.get_edges_for_app(aid)
            for edge in edges:
                for trigger in edge.triggers:
                    trigger_clean = trigger.lower().strip()
                    trigger_vec = self._trigger_embeddings.get(trigger_clean)
                    
                    if trigger_vec:
                        sim = self._encoder.cosine_similarity(cmd_vec, trigger_vec)
                        if edge.id not in existing_edge_ids:
                            scored_edges.append((sim, edge, aid))

        if not scored_edges:
            return None

        # Sort by score descending
        scored_edges.sort(key=lambda x: x[0], reverse=True)
        
        best_score = scored_edges[0][0]
        if best_score < threshold:
            logger.debug(f"[MemoryManager] No recall match (best score {best_score:.3f} < {threshold}) for: {command!r}")
            return None

        # Tie-Breaker Logic (Upgraded for State-Awareness)
        # Filter top edges within 0.02 of the best score
        top_candidates = [cand for cand in scored_edges if (best_score - cand[0]) <= 0.02]
        
        # Priority Order:
        # 1. State Signature Match
        # 2. Local App Bias
        # 3. Highest Score
        
        best_candidate = top_candidates[0]
        
        # 1. Look for state signature match first
        if state_sig:
            for cand in top_candidates:
                if cand[1].starting_state_sig == state_sig:
                    best_candidate = cand
                    logger.debug(f"[MemoryManager] State match tie-breaker → {cand[1].id}")
                    break
        
        # 2. Bias towards active_app if no state match or multiple state matches
        if best_candidate[1].starting_state_sig != state_sig and app_id and app_id != "global":
            for cand in top_candidates:
                if cand[2] == app_id:
                    best_candidate = cand
                    break

        best_edge = best_candidate[1]
        best_aid = best_candidate[2]

        logger.info(f"[MemoryManager] Semantic match: {best_candidate[0]:.3f} → {best_edge.id} (App: {best_aid})")
        return MemoryPath(edges=[best_edge], source_app=best_aid)

    # ── Save ─────────────────────────────────────────

    def save_edge(self, edge: GraphEdge) -> None:
        """Save or update an edge in the graph database."""
        self._db.save_edge(edge)
        logger.info(f"[MemoryManager] Saved edge: {edge.id}")

    def add_learned_macro(self, edge: GraphEdge) -> None:
        """Save macro to DB and hot-load the trigger embedding into RAM."""
        self.save_edge(edge)
        
        # Hot-load triggers into RAM
        for trigger in edge.triggers:
            trigger_clean = trigger.lower().strip()
            if trigger_clean not in self._trigger_embeddings:
                vec = self._encoder.embed(trigger_clean)
                if vec:
                    self._trigger_embeddings[trigger_clean] = vec
                    logger.info(f"[MemoryManager] Hot-loaded semantic trigger: '{trigger_clean}'")

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
        state_sig: str = "",
        top_n: int = 4,
    ) -> str:
        """
        RAG: return top-N relevant edge descriptions for LLM injection.
        Scores by trigger similarity + confidence + state match bonus.
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
                
                # Base score: trigger similarity + confidence
                score = best_trigger * 0.7 + edge.confidence * 0.3
                
                # State match bonus (0.2)
                if state_sig and edge.starting_state_sig == state_sig:
                    score += 0.2
                
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
