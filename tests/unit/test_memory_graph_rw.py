"""
Unit Tests — Memory Graph Read/Write
=====================================
Tests the SQLite GraphDB and MemoryManager in isolation.
Uses an in-memory SQLite database (:memory:) so no files are created.

Test cases:
    1. Save and retrieve a node
    2. Save and retrieve an edge
    3. Edge confidence update (success / failure)
    4. get_graph() returns correct NetworkX DiGraph
    5. Edge weight formula (BACK edges penalized)
    6. Fuzzy recall matches on trigger similarity
    7. Settings seed runs without error
    8. Migration runs without error on v1 data
"""

import math
import os
import tempfile
import unittest

from jarvis.memory.graph_db import GraphDB, GraphNode, GraphEdge
from jarvis.memory.memory_manager import MemoryManager
from jarvis.memory.state_comparator import StateComparator
from jarvis.memory.layers.semantic import SemanticMemory
from jarvis.memory.layers.task import TaskMemory


def _make_db() -> GraphDB:
    """Create an in-memory test database."""
    return GraphDB(":memory:")


def _sample_nodes():
    home = GraphNode(
        id="settings.home", app_id="settings", type="APP",
        label="Settings Home", entry_strategy="uri", entry_value="ms-settings:home",
    )
    display = GraphNode(
        id="settings.display", app_id="settings", type="PAGE",
        label="Display Settings", entry_strategy="uri", entry_value="ms-settings:display",
    )
    return home, display


def _sample_edge(from_id="settings.home", to_id="settings.display") -> GraphEdge:
    return GraphEdge(
        id=f"edge.{from_id}_to_{to_id}",
        from_id=from_id,
        to_id=to_id,
        edge_type="FORWARD",
        triggers=["open display settings", "display", "screen settings"],
        steps=["click System", "click Display"],
        confidence=0.90,
        success_count=3,
        fast_path="uri",
        fast_path_value="ms-settings:display",
    )


class TestGraphDB(unittest.TestCase):

    def setUp(self):
        self.db = _make_db()

    def tearDown(self):
        self.db.close()

    def test_save_and_retrieve_node(self):
        home, display = _sample_nodes()
        self.db.save_node(home)
        self.db.save_node(display)

        retrieved = self.db.get_node("settings.display")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.label, "Display Settings")
        self.assertEqual(retrieved.entry_value, "ms-settings:display")

    def test_node_upsert_idempotent(self):
        home, _ = _sample_nodes()
        self.db.save_node(home)
        home.label = "Settings Home Updated"
        self.db.save_node(home)  # Should update, not duplicate
        node = self.db.get_node("settings.home")
        self.assertEqual(node.label, "Settings Home Updated")

    def test_save_and_retrieve_edge(self):
        home, display = _sample_nodes()
        self.db.save_node(home)
        self.db.save_node(display)
        edge = _sample_edge()
        self.db.save_edge(edge)

        retrieved = self.db.get_edge(edge.id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.confidence, 0.90)
        self.assertIn("display", retrieved.triggers)
        self.assertEqual(retrieved.steps, ["click System", "click Display"])

    def test_edge_confidence_boost_on_success(self):
        home, display = _sample_nodes()
        self.db.save_node(home)
        self.db.save_node(display)
        edge = _sample_edge()
        self.db.save_edge(edge)

        self.db.update_edge_confidence(edge.id, success=True, boost=0.02)
        updated = self.db.get_edge(edge.id)
        self.assertAlmostEqual(updated.confidence, 0.92, places=5)
        self.assertEqual(updated.success_count, 4)

    def test_edge_confidence_decay_on_failure(self):
        home, display = _sample_nodes()
        self.db.save_node(home)
        self.db.save_node(display)
        edge = _sample_edge()
        self.db.save_edge(edge)

        self.db.update_edge_confidence(edge.id, success=False, decay=0.05)
        updated = self.db.get_edge(edge.id)
        self.assertAlmostEqual(updated.confidence, 0.85, places=5)
        self.assertEqual(updated.fail_count, 1)

    def test_confidence_clamped_to_bounds(self):
        home, display = _sample_nodes()
        self.db.save_node(home)
        self.db.save_node(display)

        # Max confidence
        edge = _sample_edge()
        edge.confidence = 0.99
        self.db.save_edge(edge)
        for _ in range(10):
            self.db.update_edge_confidence(edge.id, success=True, boost=0.05)
        updated = self.db.get_edge(edge.id)
        self.assertLessEqual(updated.confidence, 1.0)

    def test_get_graph_returns_networkx_digraph(self):
        import networkx as nx
        home, display = _sample_nodes()
        self.db.save_node(home)
        self.db.save_node(display)
        self.db.save_edge(_sample_edge())

        g = self.db.get_graph("settings")
        self.assertIsInstance(g, nx.DiGraph)
        self.assertIn("settings.home", g.nodes)
        self.assertIn("settings.display", g.nodes)
        self.assertTrue(g.has_edge("settings.home", "settings.display"))

    def test_back_edge_weight_penalty(self):
        """BACK edges should have 1.5x weight penalty vs FORWARD edges."""
        forward = GraphEdge(
            id="edge.fwd", from_id="a", to_id="b",
            edge_type="FORWARD", confidence=0.9, success_count=3,
        )
        back = GraphEdge(
            id="edge.bck", from_id="b", to_id="a",
            edge_type="BACK", confidence=0.9, success_count=3,
        )
        w_fwd = GraphDB._compute_weight(forward)
        w_back = GraphDB._compute_weight(back)
        self.assertAlmostEqual(w_back / w_fwd, 1.5, places=3)

    def test_edge_weight_formula(self):
        """weight = 1 / (confidence × log(success_count + 2))"""
        edge = GraphEdge(
            id="e", from_id="a", to_id="b",
            confidence=0.9, success_count=3,
        )
        expected = 1.0 / (0.9 * math.log(5))
        self.assertAlmostEqual(GraphDB._compute_weight(edge), expected, places=4)

    def test_list_apps(self):
        home, display = _sample_nodes()
        self.db.save_node(home)
        self.db.save_node(display)
        other = GraphNode(id="app.chrome", app_id="chrome", type="APP", label="Chrome")
        self.db.save_node(other)
        apps = self.db.list_apps()
        self.assertIn("settings", apps)
        self.assertIn("chrome", apps)


class TestMemoryManagerFuzzyRecall(unittest.TestCase):

    def setUp(self):
        # Use temp file for MemoryManager (it needs a real path)
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        self.mem = MemoryManager(db_path=self._tmp.name)
        db = self.mem.get_db()

        # Seed test data
        home = GraphNode(id="settings.home", app_id="settings", type="APP", label="Settings Home")
        display = GraphNode(id="settings.display", app_id="settings", type="PAGE", label="Display Settings")
        db.save_node(home)
        db.save_node(display)
        db.save_edge(_sample_edge())

    def tearDown(self):
        self.mem.close()
        os.unlink(self._tmp.name)

    def test_recall_exact_trigger(self):
        path = self.mem.recall("open display settings")
        self.assertIsNotNone(path)
        self.assertGreater(len(path.edges), 0)

    def test_recall_partial_trigger(self):
        path = self.mem.recall("display settings")
        self.assertIsNotNone(path)

    def test_recall_no_match(self):
        path = self.mem.recall("completely unrelated request xyz")
        self.assertIsNone(path)

    def test_relevant_context_returns_string(self):
        ctx = self.mem.get_relevant_context("display settings")
        self.assertIsInstance(ctx, str)
        self.assertIn("display", ctx.lower())


class TestStateComparator(unittest.TestCase):

    def setUp(self):
        self.comp = StateComparator()

    def test_empty_expected_always_matches(self):
        self.assertTrue(self.comp.matches({"a": 1}, {}))

    def test_exact_match(self):
        state = {"CheckBox:WiFi": 1, "ComboBox:Resolution": "1920x1080"}
        self.assertTrue(self.comp.matches(state, state))

    def test_noise_keys_ignored(self):
        actual = {"CheckBox:WiFi": 1, "Text:clock": "12:34"}
        expected = {"CheckBox:WiFi": 1}
        self.assertTrue(self.comp.matches(actual, expected))

    def test_slider_tolerance(self):
        # Slider values within ±10 should match
        actual = {"Slider:Brightness": 55}
        expected = {"Slider:Brightness": 50}
        self.assertTrue(self.comp.matches(actual, expected))

    def test_mismatch_below_threshold(self):
        actual = {"CheckBox:WiFi": 0}
        expected = {"CheckBox:WiFi": 1}
        self.assertFalse(self.comp.matches(actual, expected, threshold=0.8))

    def test_diff_returns_mismatched_keys(self):
        actual = {"CheckBox:WiFi": 0}
        expected = {"CheckBox:WiFi": 1}
        diff = self.comp.diff(actual, expected)
        self.assertIn("CheckBox:WiFi", diff)


class TestSemanticMemory(unittest.TestCase):

    def setUp(self):
        self.sem = SemanticMemory()

    def test_seed_facts_loaded(self):
        facts = self.sem.query("devtools")
        self.assertGreater(len(facts), 0)
        self.assertIn("F12", facts[0].value)

    def test_query_by_app(self):
        facts = self.sem.query("vscode")
        self.assertGreater(len(facts), 0)

    def test_as_context_string(self):
        ctx = self.sem.as_context("chrome")
        self.assertIsInstance(ctx, str)


class TestTaskMemory(unittest.TestCase):

    def setUp(self):
        self.tasks = TaskMemory()

    def test_create_and_retrieve_task(self):
        task = self.tasks.create_task("Setup Python env", ["install python", "install pip", "install pytest"])
        active = self.tasks.get_active()
        self.assertIn(task, active)
        self.assertEqual(task.label, "Setup Python env")

    def test_next_step(self):
        task = self.tasks.create_task("Test task", ["step1", "step2"])
        self.assertEqual(task.next_step, "step1")
        self.tasks.advance(task.id)
        self.assertEqual(task.next_step, "step2")

    def test_task_completes(self):
        task = self.tasks.create_task("Short task", ["only step"])
        self.tasks.advance(task.id)
        self.assertEqual(task.status, "completed")
        self.assertIsNone(task.next_step)

    def test_find_by_label(self):
        self.tasks.create_task("Install dev tools", ["step1"])
        found = self.tasks.find_by_label("dev tools")
        self.assertIsNotNone(found)


if __name__ == "__main__":
    unittest.main(verbosity=2)
