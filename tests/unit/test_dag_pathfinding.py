"""
Unit Tests — A* DAG Pathfinding
=================================
Tests the GraphPathfinder in isolation using in-memory SQLite.

Test cases:
    1. URI fast-path: node with ms-settings URI → skips A*, returns directly
    2. Forward navigation: A* finds shortest path across 3 nodes
    3. BACK edge penalty: A* prefers forward path when back exists
    4. No path → returns None (not an exception)
    5. Low-confidence edge pruned → A* routes around it
    6. Command-based path lookup (find_path_by_command)
"""

import unittest

from jarvis_v2.memory.graph_db import GraphDB, GraphNode, GraphEdge
from jarvis_v2.pathfinding.graph_pathfinder import GraphPathfinder


def _build_settings_graph() -> GraphDB:
    """Build a small settings navigation graph in memory."""
    db = GraphDB(":memory:")

    nodes = [
        GraphNode("app.settings",          "settings", "APP",     "Settings Home",     "uri",   "ms-settings:home"),
        GraphNode("settings.system",        "settings", "PAGE",    "System",            "click", ""),
        GraphNode("settings.display",       "settings", "PAGE",    "Display Settings",  "uri",   "ms-settings:display"),
        GraphNode("settings.display.adv",   "settings", "SECTION", "Advanced Display",  "uri",   "ms-settings:display-advancedgraphics"),
        GraphNode("settings.sound",         "settings", "PAGE",    "Sound Settings",    "uri",   "ms-settings:sound"),
    ]
    for n in nodes:
        db.save_node(n)

    edges = [
        # Home → System (click)
        GraphEdge("e1", "app.settings", "settings.system",
                  edge_type="FORWARD", action_type="click",
                  triggers=["open system", "system settings"],
                  steps=["click:System"], confidence=0.90, success_count=5),
        # System → Display (click)
        GraphEdge("e2", "settings.system", "settings.display",
                  edge_type="FORWARD", action_type="click",
                  triggers=["display", "display settings"],
                  steps=["click:Display"], confidence=0.85, success_count=3),
        # Display → Advanced (click)
        GraphEdge("e3", "settings.display", "settings.display.adv",
                  edge_type="FORWARD", action_type="click",
                  triggers=["advanced display"],
                  steps=["click:Advanced display settings"], confidence=0.80, success_count=2),
        # Display ← System BACK edge (penalty ×1.5)
        GraphEdge("e4", "settings.display", "settings.system",
                  edge_type="BACK", action_type="click",
                  triggers=[], steps=["click:Back"], confidence=0.95, success_count=10),
        # Low-confidence edge (should be pruned)
        GraphEdge("e5", "app.settings", "settings.sound",
                  edge_type="FORWARD", action_type="click",
                  triggers=["sound settings"],
                  steps=["click:Sound"], confidence=0.10, success_count=0),
    ]
    for e in edges:
        db.save_edge(e)

    return db


class TestPathfinderFastPath(unittest.TestCase):

    def setUp(self):
        self.db = _build_settings_graph()
        self.pf = GraphPathfinder(self.db)

    def test_uri_fast_path_returned(self):
        """Nodes with URI entry skip A* entirely."""
        result = self.pf.find("settings", "settings.display")
        self.assertTrue(result.fast_path_used)
        self.assertEqual(result.fast_path_uri, "ms-settings:display")
        self.assertIsNotNone(result.path)
        self.assertEqual(len(result.path.edges), 1)
        self.assertEqual(result.path.edges[0].fast_path, "uri")

    def test_uri_fast_path_steps(self):
        """Fast-path edge steps contain the uri: prefix."""
        result = self.pf.find("settings", "settings.display")
        self.assertIn("uri:ms-settings:display", result.path.steps)

    def test_app_root_uri_fast_path(self):
        result = self.pf.find("settings", "settings.sound")
        # sound has URI but confidence of its graph edge is low;
        # fast-path is based on node entry_strategy, not edge confidence
        self.assertTrue(result.fast_path_used)
        self.assertIn("ms-settings:sound", result.fast_path_uri)


class TestPathfinderAstar(unittest.TestCase):

    def setUp(self):
        self.db = _build_settings_graph()
        # Remove URI from display so A* is forced
        conn = self.db._conn
        conn.execute("UPDATE nodes SET entry_strategy='click', entry_value='' WHERE id='settings.display'")
        conn.execute("UPDATE nodes SET entry_strategy='click', entry_value='' WHERE id='settings.sound'")
        conn.commit()
        self.pf = GraphPathfinder(self.db, min_confidence=0.30)

    def test_forward_path_found(self):
        """A* finds: home → system → display."""
        result = self.pf.find("settings", "settings.display", start_node_id="app.settings")
        self.assertFalse(result.fast_path_used)
        self.assertIsNotNone(result.path)
        self.assertGreater(len(result.path.edges), 0)
        # Should traverse through system
        node_ids = [e.from_id for e in result.path.edges] + [result.path.edges[-1].to_id]
        self.assertIn("settings.system", node_ids)
        self.assertIn("settings.display", node_ids)

    def test_no_path_returns_none(self):
        """No edge to an isolated node → None, no exception."""
        # Add isolated node with no edges
        self.db.save_node(GraphNode("isolated.node", "settings", "ELEMENT", "Orphan"))
        result = self.pf.find("settings", "isolated.node", start_node_id="app.settings")
        self.assertIsNone(result.path)

    def test_low_confidence_edge_pruned(self):
        """Edge with confidence < min_confidence is excluded from A*."""
        # sound has only e5 (confidence=0.10), which is below default min (0.30)
        result = self.pf.find("settings", "settings.sound", start_node_id="app.settings")
        # Should fail since only path is through pruned e5
        self.assertIsNone(result.path)

    def test_back_edge_not_preferred(self):
        """A* should prefer forward path over back edge (penalty ×1.5)."""
        # Path home→system→display should be chosen over display←system (BACK)
        # We check that the result doesn't start with a back edge
        result = self.pf.find("settings", "settings.display", start_node_id="app.settings")
        if result.path and result.path.edges:
            first = result.path.edges[0]
            self.assertNotEqual(first.edge_type, "BACK")


class TestPathfinderCommandLookup(unittest.TestCase):

    def setUp(self):
        self.db = _build_settings_graph()
        # Remove URIs to force A*
        conn = self.db._conn
        conn.execute("UPDATE nodes SET entry_strategy='click', entry_value='' WHERE app_id='settings'")
        conn.commit()
        self.pf = GraphPathfinder(self.db)

    def test_command_match_returns_path(self):
        """'open display settings' should match the display edge trigger."""
        path = self.pf.find_path_by_command("open display settings", "settings")
        self.assertIsNotNone(path)
        node_ids = [e.to_id for e in path.edges]
        self.assertIn("settings.display", node_ids)

    def test_low_similarity_returns_none(self):
        """Completely unrelated command → None."""
        path = self.pf.find_path_by_command("make me a sandwich xyz", "settings")
        self.assertIsNone(path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
