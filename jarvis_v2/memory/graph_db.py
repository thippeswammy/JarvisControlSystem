"""
Graph Database
==============
SQLite-backed persistent graph store with NetworkX in-memory representation.

Schema:
    nodes(id, app_id, type, label, state_hash, ui_metadata_json, entry_strategy, entry_value)
    edges(id, from_id, to_id, edge_type, action_type, action_params_json,
          confidence, success_count, fail_count, triggers_json, fast_path, fast_path_value,
          steps_json, last_used)

Design (v2.1):
    - All writes are atomic (SQLite transactions)
    - NetworkX DiGraph is loaded per-app on demand (contextual pruning)
    - Edges carry confidence scores for A* pathfinding
    - State hashes enable verification loop (does action actually change state?)
"""

import json
import logging
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

import networkx as nx

logger = logging.getLogger(__name__)


# ── Node and Edge dataclasses ─────────────────────────────────

@dataclass
class GraphNode:
    id: str                          # e.g. "settings.display"
    app_id: str                      # e.g. "settings"
    type: str                        # APP | PAGE | SECTION | ELEMENT | DIALOG | SHORTCUT
    label: str                       # Human-readable name
    entry_strategy: str = "click"    # uri | path | search | click | scroll_into_view | keyboard
    entry_value: str = ""            # ms-settings:display, exe path, etc.
    state_hash: str = ""             # MD5 of UIState dict — for verification loop
    ui_metadata: dict = field(default_factory=dict)  # raw UI tree snapshot


@dataclass
class GraphEdge:
    id: str                          # e.g. "edge.home_to_display"
    from_id: str
    to_id: str
    edge_type: str = "FORWARD"       # FORWARD | BACK | CROSS | SHORTCUT
    action_type: str = "click"       # click | keyboard | type | scroll | wait_for | uri_deep_link
    action_params: dict = field(default_factory=dict)
    confidence: float = 0.9
    success_count: int = 0
    fail_count: int = 0
    triggers: list = field(default_factory=list)  # utterance patterns that activate this edge
    fast_path: str = ""              # "uri" | "keyboard" | ""
    fast_path_value: str = ""        # ms-settings:display, Ctrl+D, etc.
    steps: list = field(default_factory=list)  # ordered action strings
    last_used: str = ""


# ── Database ──────────────────────────────────────────────────

class GraphDB:
    """
    SQLite + NetworkX graph store.

    Usage:
        db = GraphDB("./memory/jarvis_v2.db")
        db.save_node(GraphNode(id="settings.display", app_id="settings", ...))
        db.save_edge(GraphEdge(id="edge.home_to_display", from_id="settings.home", ...))
        g = db.get_graph("settings")  # returns nx.DiGraph for A* pathfinding
    """

    _SCHEMA = """
    CREATE TABLE IF NOT EXISTS nodes (
        id              TEXT PRIMARY KEY,
        app_id          TEXT NOT NULL,
        type            TEXT NOT NULL,
        label           TEXT NOT NULL,
        entry_strategy  TEXT DEFAULT 'click',
        entry_value     TEXT DEFAULT '',
        state_hash      TEXT DEFAULT '',
        ui_metadata     TEXT DEFAULT '{}'
    );

    CREATE TABLE IF NOT EXISTS edges (
        id              TEXT PRIMARY KEY,
        from_id         TEXT NOT NULL,
        to_id           TEXT NOT NULL,
        edge_type       TEXT DEFAULT 'FORWARD',
        action_type     TEXT DEFAULT 'click',
        action_params   TEXT DEFAULT '{}',
        confidence      REAL DEFAULT 0.9,
        success_count   INTEGER DEFAULT 0,
        fail_count      INTEGER DEFAULT 0,
        triggers        TEXT DEFAULT '[]',
        fast_path       TEXT DEFAULT '',
        fast_path_value TEXT DEFAULT '',
        steps           TEXT DEFAULT '[]',
        last_used       TEXT DEFAULT '',
        FOREIGN KEY(from_id) REFERENCES nodes(id),
        FOREIGN KEY(to_id)   REFERENCES nodes(id)
    );

    CREATE INDEX IF NOT EXISTS idx_nodes_app ON nodes(app_id);
    CREATE INDEX IF NOT EXISTS idx_edges_from ON edges(from_id);
    CREATE INDEX IF NOT EXISTS idx_edges_to ON edges(to_id);
    """

    def __init__(self, db_path: str):
        if db_path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")  # Better concurrency
        self._init_schema()
        logger.info(f"[GraphDB] Opened: {db_path}")

    def close(self):
        self._conn.close()

    # ── Node operations ──────────────────────────────

    def save_node(self, node: GraphNode) -> None:
        """Upsert a node. Safe to call multiple times (idempotent)."""
        with self._conn:
            self._conn.execute("""
                INSERT INTO nodes (id, app_id, type, label, entry_strategy, entry_value, state_hash, ui_metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    label=excluded.label,
                    entry_strategy=excluded.entry_strategy,
                    entry_value=excluded.entry_value,
                    state_hash=excluded.state_hash,
                    ui_metadata=excluded.ui_metadata
            """, (
                node.id, node.app_id, node.type, node.label,
                node.entry_strategy, node.entry_value, node.state_hash,
                json.dumps(node.ui_metadata),
            ))

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        row = self._conn.execute(
            "SELECT * FROM nodes WHERE id=?", (node_id,)
        ).fetchone()
        return self._row_to_node(row) if row else None

    def get_nodes_for_app(self, app_id: str) -> list[GraphNode]:
        rows = self._conn.execute(
            "SELECT * FROM nodes WHERE app_id=?", (app_id,)
        ).fetchall()
        return [self._row_to_node(r) for r in rows]

    def update_node_state(self, node_id: str, state_hash: str, ui_metadata: dict) -> None:
        """Update the UIState snapshot of a node (called by VerificationLoop)."""
        with self._conn:
            self._conn.execute(
                "UPDATE nodes SET state_hash=?, ui_metadata=? WHERE id=?",
                (state_hash, json.dumps(ui_metadata), node_id),
            )

    # ── Edge operations ──────────────────────────────

    def save_edge(self, edge: GraphEdge) -> None:
        """Upsert an edge."""
        with self._conn:
            self._conn.execute("""
                INSERT INTO edges
                    (id, from_id, to_id, edge_type, action_type, action_params,
                     confidence, success_count, fail_count, triggers,
                     fast_path, fast_path_value, steps, last_used)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    confidence=excluded.confidence,
                    success_count=excluded.success_count,
                    fail_count=excluded.fail_count,
                    triggers=excluded.triggers,
                    steps=excluded.steps,
                    last_used=excluded.last_used
            """, (
                edge.id, edge.from_id, edge.to_id, edge.edge_type,
                edge.action_type, json.dumps(edge.action_params),
                edge.confidence, edge.success_count, edge.fail_count,
                json.dumps(edge.triggers), edge.fast_path, edge.fast_path_value,
                json.dumps(edge.steps), edge.last_used,
            ))

    def get_edge(self, edge_id: str) -> Optional[GraphEdge]:
        row = self._conn.execute(
            "SELECT * FROM edges WHERE id=?", (edge_id,)
        ).fetchone()
        return self._row_to_edge(row) if row else None

    def get_edges_for_app(self, app_id: str) -> list[GraphEdge]:
        """Return all edges where from_id belongs to app_id."""
        rows = self._conn.execute("""
            SELECT e.* FROM edges e
            JOIN nodes n ON e.from_id = n.id
            WHERE n.app_id = ?
        """, (app_id,)).fetchall()
        return [self._row_to_edge(r) for r in rows]

    def update_edge_confidence(self, edge_id: str, success: bool, decay: float = 0.05, boost: float = 0.02) -> None:
        """
        Adjust confidence after action execution.
        success=True  → confidence += boost
        success=False → confidence -= decay; increment fail_count
        Clamps to [0.0, 1.0].
        """
        row = self._conn.execute(
            "SELECT confidence, success_count, fail_count FROM edges WHERE id=?",
            (edge_id,)
        ).fetchone()
        if not row:
            return

        conf = float(row["confidence"])
        s_count = row["success_count"]
        f_count = row["fail_count"]

        if success:
            conf = min(1.0, conf + boost)
            s_count += 1
        else:
            conf = max(0.0, conf - decay)
            f_count += 1

        with self._conn:
            self._conn.execute(
                "UPDATE edges SET confidence=?, success_count=?, fail_count=?, last_used=? WHERE id=?",
                (conf, s_count, f_count, date.today().isoformat(), edge_id),
            )

    # ── Graph export (NetworkX) ──────────────────────

    def get_graph(self, app_id: str) -> nx.DiGraph:
        """
        Load all nodes + edges for an app into a NetworkX DiGraph.
        Node attributes carry the full GraphNode data.
        Edge attributes carry the full GraphEdge data + computed weight.
        """
        g = nx.DiGraph()

        nodes = self.get_nodes_for_app(app_id)
        for node in nodes:
            g.add_node(node.id, data=node)

        edges = self.get_edges_for_app(app_id)
        for edge in edges:
            # Ensure both endpoints exist (cross-app edges bring in foreign nodes)
            if edge.from_id not in g:
                fn = self.get_node(edge.from_id)
                if fn:
                    g.add_node(fn.id, data=fn)
            if edge.to_id not in g:
                tn = self.get_node(edge.to_id)
                if tn:
                    g.add_node(tn.id, data=tn)

            weight = self._compute_weight(edge)
            g.add_edge(edge.from_id, edge.to_id, data=edge, weight=weight)

        logger.debug(f"[GraphDB] Loaded graph for '{app_id}': {g.number_of_nodes()} nodes, {g.number_of_edges()} edges")
        return g

    def list_apps(self) -> list[str]:
        """Return all distinct app_ids in the database."""
        rows = self._conn.execute("SELECT DISTINCT app_id FROM nodes").fetchall()
        return [r["app_id"] for r in rows]

    # ── Private ──────────────────────────────────────

    def _init_schema(self):
        self._conn.executescript(self._SCHEMA)
        self._conn.commit()

    @staticmethod
    def _compute_weight(edge: GraphEdge) -> float:
        """
        A* edge weight: lower = preferred path.
        weight = 1 / (confidence × log(success_count + 2))
        BACK edges get ×1.5 penalty to prefer forward routes.
        """
        import math
        base = 1.0 / (max(edge.confidence, 0.01) * math.log(edge.success_count + 2))
        if edge.edge_type == "BACK":
            base *= 1.5
        return round(base, 6)

    @staticmethod
    def _row_to_node(row) -> GraphNode:
        return GraphNode(
            id=row["id"],
            app_id=row["app_id"],
            type=row["type"],
            label=row["label"],
            entry_strategy=row["entry_strategy"],
            entry_value=row["entry_value"],
            state_hash=row["state_hash"],
            ui_metadata=json.loads(row["ui_metadata"] or "{}"),
        )

    @staticmethod
    def _row_to_edge(row) -> GraphEdge:
        return GraphEdge(
            id=row["id"],
            from_id=row["from_id"],
            to_id=row["to_id"],
            edge_type=row["edge_type"],
            action_type=row["action_type"],
            action_params=json.loads(row["action_params"] or "{}"),
            confidence=float(row["confidence"]),
            success_count=int(row["success_count"]),
            fail_count=int(row["fail_count"]),
            triggers=json.loads(row["triggers"] or "[]"),
            fast_path=row["fast_path"],
            fast_path_value=row["fast_path_value"],
            steps=json.loads(row["steps"] or "[]"),
            last_used=row["last_used"],
        )
