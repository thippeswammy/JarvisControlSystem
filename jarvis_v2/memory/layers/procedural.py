"""
Procedural Memory Layer
=======================
Manages navigation graphs per application.
Handles seeding, querying, and updating app-level DAGs.

Key responsibilities:
    - Seed the Settings graph (130 ms-settings: URIs) from settings_seed.yaml
    - Load app graphs into NetworkX for pathfinding
    - Auto-create new app entries on first visit
"""

import logging
import os
import re
from datetime import date
from pathlib import Path
from typing import Optional

from jarvis_v2.memory.graph_db import GraphDB, GraphNode, GraphEdge

logger = logging.getLogger(__name__)

_CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"
_SETTINGS_SEED_FILE = _CONFIG_DIR / "settings_seed.yaml"


class ProceduralMemory:
    """
    Manages per-app navigation graphs in the SQLite database.

    Usage:
        proc = ProceduralMemory(db)
        proc.seed_settings_graph()
        graph = proc.get_app_graph("settings")  # NetworkX DiGraph
        proc.record_navigation(app_id, from_node, to_node, steps, success)
    """

    def __init__(self, db: GraphDB):
        self._db = db

    def get_app_graph(self, app_id: str):
        """Return a NetworkX DiGraph for the given app (contextual pruning built-in)."""
        return self._db.get_graph(app_id)

    def ensure_app_root(self, app_id: str, entry_strategy: str = "search", entry_value: str = "") -> GraphNode:
        """
        Ensure an APP root node exists. Auto-creates on first visit.
        Returns the node.
        """
        node_id = f"app.{app_id}"
        existing = self._db.get_node(node_id)
        if existing:
            return existing

        node = GraphNode(
            id=node_id,
            app_id=app_id,
            type="APP",
            label=app_id.title(),
            entry_strategy=entry_strategy,
            entry_value=entry_value,
        )
        self._db.save_node(node)
        logger.info(f"[ProceduralMemory] Auto-created root node for '{app_id}'")
        return node

    def record_navigation(
        self,
        app_id: str,
        from_id: str,
        to_id: str,
        steps: list[str],
        triggers: list[str],
        success: bool,
        fast_path: str = "",
        fast_path_value: str = "",
    ) -> GraphEdge:
        """
        Record a navigation action. Creates or updates the edge.
        Called by ReactiveLearner after successful (verified) navigation.
        """
        edge_id = f"edge.{from_id}_to_{to_id.replace('.', '_')}"
        existing = self._db.get_edge(edge_id)

        if existing:
            self._db.update_edge_confidence(edge_id, success=success)
            return existing

        edge = GraphEdge(
            id=edge_id,
            from_id=from_id,
            to_id=to_id,
            edge_type="FORWARD",
            action_type="sequence",
            steps=steps,
            triggers=triggers,
            fast_path=fast_path,
            fast_path_value=fast_path_value,
            confidence=0.80,
            success_count=1 if success else 0,
            fail_count=0 if success else 1,
            last_used=date.today().isoformat(),
        )
        self._db.save_edge(edge)
        logger.info(f"[ProceduralMemory] New edge saved: {edge_id}")
        return edge

    def seed_settings_graph(self) -> int:
        """
        Seed 130 ms-settings: URI nodes from settings_seed.yaml.
        Idempotent — skips entries that already exist.
        Returns the count of newly added nodes.
        """
        if not _SETTINGS_SEED_FILE.exists():
            logger.warning(f"[ProceduralMemory] settings_seed.yaml not found: {_SETTINGS_SEED_FILE}")
            return 0

        try:
            import yaml
            with open(_SETTINGS_SEED_FILE, encoding="utf-8") as f:
                seed_data = yaml.safe_load(f)
        except Exception as e:
            logger.error(f"[ProceduralMemory] Failed to load seed file: {e}")
            return 0

        count = 0
        app_id = "settings"

        # Ensure settings root node
        self.ensure_app_root(app_id, entry_strategy="uri", entry_value="ms-settings:home")

        for entry in seed_data.get("settings", []):
            uri = entry.get("uri", "")
            label = entry.get("label", "")
            node_id = entry.get("id", "")

            if not (uri and label and node_id):
                continue

            # Check if already seeded
            if self._db.get_node(node_id):
                continue

            # Create node
            self._db.save_node(GraphNode(
                id=node_id,
                app_id=app_id,
                type="PAGE",
                label=label,
                entry_strategy="uri",
                entry_value=uri,
            ))

            # Create direct fast-path edge from settings root
            edge_id = f"edge.settings_home_to_{re.sub(r'[^a-z0-9_]', '_', node_id)}"
            triggers = entry.get("triggers", [label.lower()])
            self._db.save_edge(GraphEdge(
                id=edge_id,
                from_id="app.settings",
                to_id=node_id,
                edge_type="FORWARD",
                action_type="uri_deep_link",
                triggers=triggers,
                fast_path="uri",
                fast_path_value=uri,
                steps=[f"uri:{uri}"],
                confidence=0.97,
                success_count=0,
                last_used="",
            ))
            count += 1

        logger.info(f"[ProceduralMemory] Seeded {count} settings nodes.")
        return count

    def get_fast_path(self, node_id: str) -> Optional[str]:
        """
        Check if a node has a URI fast-path. Returns the URI or None.
        Used by pathfinder to short-circuit A* when a direct URI exists.
        """
        node = self._db.get_node(node_id)
        if node and node.entry_strategy == "uri" and node.entry_value:
            return node.entry_value
        return None
