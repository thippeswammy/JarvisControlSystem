"""
Graph Pathfinder (A*)
=====================
Finds the best navigation path in a NetworkX DiGraph using A* search
with hierarchical pruning.

Algorithm:
    1. Fast-path check: if target node has a URI/keyboard entry → skip A*
    2. Contextual pruning: load only the relevant app's subgraph
    3. A* with heuristic: h(n, target) = hierarchical depth distance
    4. Cycle guard: per-path visited set
    5. Confidence pruning: skip edges below min_confidence threshold

Edge weight formula (built in GraphDB._compute_weight):
    weight = 1 / (confidence × log(success_count + 2))
    BACK edges: weight × 1.5

Returns:
    MemoryPath (list of GraphEdge) or None if no path found
"""

import logging
import math
from dataclasses import dataclass
from typing import Optional

import networkx as nx

from jarvis_v2.memory.graph_db import GraphDB, GraphEdge
from jarvis_v2.memory.memory_manager import MemoryPath

logger = logging.getLogger(__name__)

# Hierarchy depth by node type (lower = higher in tree)
_TYPE_DEPTH = {"APP": 0, "PAGE": 1, "SECTION": 2, "ELEMENT": 3, "DIALOG": 3, "SHORTCUT": 1}
_MIN_CONFIDENCE = 0.30


@dataclass
class PathResult:
    path: Optional[MemoryPath]
    fast_path_used: bool = False
    fast_path_uri: str = ""
    nodes_visited: int = 0


class GraphPathfinder:
    """
    A* pathfinder over the SQLite/NetworkX procedural DAG.

    Usage:
        pf = GraphPathfinder(db)
        result = pf.find(app_id="settings", target_node_id="settings.display")
        if result.fast_path_used:
            os.startfile(result.fast_path_uri)
        elif result.path:
            for edge in result.path.edges:
                skill_bus.dispatch(SkillCall("navigate_location", {"steps": edge.steps}))
    """

    def __init__(self, db: GraphDB, min_confidence: float = _MIN_CONFIDENCE):
        self._db = db
        self._min_conf = min_confidence

    def find(
        self,
        app_id: str,
        target_node_id: str,
        start_node_id: Optional[str] = None,
    ) -> PathResult:
        """
        Find a path from start_node_id to target_node_id within app_id's graph.

        If start_node_id is None, uses the app root (app.<app_id>).
        Returns PathResult with fast_path_used=True if a URI shortcut exists.
        """
        # 1. Fast-path check (O(1))
        target = self._db.get_node(target_node_id)
        if target and target.entry_strategy == "uri" and target.entry_value:
            logger.info(f"[Pathfinder] Fast-path (URI): {target.entry_value}")
            edge = GraphEdge(
                id=f"fastpath.{target_node_id}",
                from_id=start_node_id or f"app.{app_id}",
                to_id=target_node_id,
                edge_type="SHORTCUT",
                action_type="uri_deep_link",
                fast_path="uri",
                fast_path_value=target.entry_value,
                steps=[f"uri:{target.entry_value}"],
                confidence=0.97,
            )
            return PathResult(
                path=MemoryPath(edges=[edge], source_app=app_id),
                fast_path_used=True,
                fast_path_uri=target.entry_value,
            )

        # 2. Load contextual subgraph (only this app)
        g = self._db.get_graph(app_id)
        if g.number_of_nodes() == 0:
            logger.debug(f"[Pathfinder] Empty graph for app: {app_id}")
            return PathResult(path=None)

        start = start_node_id or f"app.{app_id}"

        if start not in g:
            logger.debug(f"[Pathfinder] Start node not in graph: {start}")
            return PathResult(path=None)
        if target_node_id not in g:
            logger.debug(f"[Pathfinder] Target node not in graph: {target_node_id}")
            return PathResult(path=None)

        # 3. Prune low-confidence edges
        pruned_g = self._prune_graph(g)

        # 4. A* search
        try:
            node_path = nx.astar_path(
                pruned_g,
                source=start,
                target=target_node_id,
                heuristic=lambda u, v: self._heuristic(u, v, pruned_g),
                weight="weight",
            )
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            logger.info(f"[Pathfinder] No path from {start!r} to {target_node_id!r}")
            return PathResult(path=None, nodes_visited=pruned_g.number_of_nodes())

        # 5. Convert node path → edge list
        edges = []
        for i in range(len(node_path) - 1):
            u, v = node_path[i], node_path[i + 1]
            edge_data = pruned_g[u][v].get("data")
            if edge_data:
                edges.append(edge_data)
            else:
                # Synthesize a minimal edge if data is missing
                edges.append(GraphEdge(
                    id=f"synth.{u}_{v}",
                    from_id=u, to_id=v,
                    edge_type="FORWARD",
                    action_type="click",
                    steps=[f"click:{v.split('.')[-1]}"],
                    confidence=0.5,
                ))

        path = MemoryPath(edges=edges, source_app=app_id)
        logger.info(
            f"[Pathfinder] A* path: {start} → {target_node_id} | "
            f"{len(edges)} edges, min_confidence={path.confidence:.2f}"
        )
        return PathResult(path=path, nodes_visited=pruned_g.number_of_nodes())

    def find_path_by_command(
        self,
        command: str,
        app_id: str,
    ) -> Optional[MemoryPath]:
        """
        Find a path by matching command text against edge triggers.
        Called by MemoryManager.recall() when pathfinder is injected.

        Uses trigram similarity to score trigger matches.
        Returns MemoryPath or None.
        """
        from difflib import SequenceMatcher
        g = self._db.get_graph(app_id)
        cmd_lower = command.lower().strip()

        best_score = 0.0
        best_target = None

        for u, v, data in g.edges(data=True):
            edge = data.get("data")
            if not edge:
                continue
            for trigger in edge.triggers:
                score = self._score_command(cmd_lower, trigger.lower())
                if score > best_score:
                    best_score = score
                    best_target = v

        if best_score < 0.50 or not best_target:
            return None

        logger.debug(f"[Pathfinder] Command match: {best_score:.2f} → {best_target}")
        result = self.find(app_id=app_id, target_node_id=best_target)
        return result.path

    def _score_command(self, command: str, trigger: str) -> float:
        """
        Score a command against a trigger using word-based coverage.
        More robust than raw SequenceMatcher for short triggers.
        """
        from difflib import SequenceMatcher
        cmd_words = set(command.split())
        trig_words = set(trigger.split())

        if not cmd_words or not trig_words:
            return 0.0

        intersection = cmd_words.intersection(trig_words)
        if not intersection:
            # Fallback to ratio if no word overlap (handles typos)
            return SequenceMatcher(None, command, trigger).ratio() * 0.4

        # Coverage: how many words of the trigger are in the command?
        coverage = len(intersection) / len(trig_words)
        
        # Bonus for ratio to break ties and handle sequence
        ratio = SequenceMatcher(None, command, trigger).ratio()
        
        return coverage * 0.7 + ratio * 0.3

    # ── Private ──────────────────────────────────────

    def _prune_graph(self, g: nx.DiGraph) -> nx.DiGraph:
        """Remove edges below min_confidence threshold."""
        pruned = nx.DiGraph()
        for node, data in g.nodes(data=True):
            pruned.add_node(node, **data)
        for u, v, data in g.edges(data=True):
            edge = data.get("data")
            if edge and edge.confidence >= self._min_conf:
                pruned.add_edge(u, v, **data)
        return pruned

    @staticmethod
    def _heuristic(u: str, v: str, g: nx.DiGraph) -> float:
        """
        A* heuristic: hierarchical depth distance.
        h(n, target) = |depth(n) - depth(target)|
        Nodes higher in the hierarchy (APP > PAGE > SECTION > ELEMENT)
        get lower heuristic values.
        """
        def depth(node_id: str) -> int:
            node_data = g.nodes.get(node_id, {}).get("data")
            if node_data:
                return _TYPE_DEPTH.get(node_data.type, 2)
            # Infer from ID structure: settings.display.advanced → depth 2
            return len(node_id.split(".")) - 1

        return abs(depth(u) - depth(v))
