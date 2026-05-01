"""
Graph Exporter
==============
Generates human-readable .md snapshots of the SQLite graph database.
Called on demand for debugging — NOT on every write (performance).

Output format is identical to the v2 design spec:
    memory/procedural/apps/<app_id>/graph.md
    memory/procedural/apps/<app_id>/ui_map.md

Usage:
    exporter = GraphExporter(db, export_root="./memory/procedural/apps")
    exporter.export_app("settings")
    exporter.export_all()
"""

import logging
import os
from datetime import datetime

from jarvis.memory.graph_db import GraphDB, GraphNode, GraphEdge

logger = logging.getLogger(__name__)


class GraphExporter:
    """Exports SQLite graph content to human-readable .md files."""

    def __init__(self, db: GraphDB, export_root: str = "./memory/procedural/apps"):
        self._db = db
        self._root = export_root

    def export_app(self, app_id: str) -> str:
        """
        Export a single app's graph to graph.md.
        Returns the path of the written file.
        """
        nodes = self._db.get_nodes_for_app(app_id)
        edges = self._db.get_edges_for_app(app_id)

        app_dir = os.path.join(self._root, app_id)
        os.makedirs(app_dir, exist_ok=True)
        path = os.path.join(app_dir, "graph.md")

        lines = [
            f"# procedural/apps/{app_id} — Navigation Graph (DG)",
            f"<!-- Jarvis v2.1 | Exported: {datetime.now().isoformat()[:19]} "
            f"| {len(nodes)} nodes, {len(edges)} edges -->",
            "",
        ]

        for node in sorted(nodes, key=lambda n: n.id):
            lines.extend(self._node_to_md(node))
            lines.append("")

        for edge in sorted(edges, key=lambda e: e.id):
            lines.extend(self._edge_to_md(edge))
            lines.append("")

        content = "\n".join(lines)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"[GraphExporter] Exported '{app_id}' → {path}")
        return path

    def export_all(self) -> list[str]:
        """Export all apps in the database."""
        apps = self._db.list_apps()
        return [self.export_app(app_id) for app_id in apps]

    # ── Private ──────────────────────────────────────

    @staticmethod
    def _node_to_md(node: GraphNode) -> list[str]:
        return [
            "## Node",
            f"- id: {node.id}",
            f"- type: {node.type}",
            f"- label: {node.label}",
            f"- entry_strategy: {node.entry_strategy}",
            f"- entry_value: {node.entry_value or 'none'}",
            f"- state_hash: {node.state_hash or 'none'}",
        ]

    @staticmethod
    def _edge_to_md(edge: GraphEdge) -> list[str]:
        triggers_str = ", ".join(f'"{t}"' for t in edge.triggers) if edge.triggers else "none"
        steps_str = ", ".join(f'"{s}"' for s in edge.steps) if edge.steps else "none"
        return [
            "## Edge",
            f"- id: {edge.id}",
            f"- from: {edge.from_id}",
            f"- to: {edge.to_id}",
            f"- edge_type: {edge.edge_type}",
            f"- triggers: [{triggers_str}]",
            f"- steps: [{steps_str}]",
            f"- fast_path: {edge.fast_path or 'none'}",
            f"- fast_path_value: {edge.fast_path_value or 'none'}",
            f"- confidence: {edge.confidence:.2f}",
            f"- success_count: {edge.success_count}",
            f"- fail_count: {edge.fail_count}",
            f"- last_used: {edge.last_used or 'never'}",
        ]
