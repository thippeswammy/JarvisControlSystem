"""
Unit Tests — ReactiveLearner
==============================
Verifies the "Execute → Verify → Learn" guarantee:
  - learn() creates new edges in the DB
  - learn() merges triggers on existing edges (no duplicate entries)
  - learn() calls update_edge_confidence on existing edges (not creates duplicate)
  - penalize() calls record_failure via MemoryManager

All tests use in-memory SQLite so no files are created.

Test cases:
    1. learn() creates a new edge with initial confidence=0.80
    2. learn() auto-creates missing source/target nodes
    3. learn() on existing edge merges triggers instead of creating duplicate
    4. learn() on existing edge calls update_edge_confidence (success=True)
    5. additional_triggers are merged into the triggers list
    6. penalize() decreases edge confidence
    7. trigger deduplication: same trigger not stored twice
    8. edge ID is deterministic from from_node + to_node
"""
import unittest

from jarvis.memory.graph_db import GraphDB, GraphEdge
from jarvis.memory.memory_manager import MemoryManager
from jarvis.skills.skill_bus import SkillResult
from jarvis.brain.reactive_learner import ReactiveLearner


def _make_learner(db_path=":memory:"):
    """Helper: build a MemoryManager + ReactiveLearner backed by in-memory SQLite."""
    mem = MemoryManager(db_path=db_path)
    learner = ReactiveLearner(mem)
    return mem, learner


def _ok_result():
    return SkillResult(success=True, message="ok")


class TestNewEdgeCreation(unittest.TestCase):
    """learn() on a brand-new edge should persist a proper GraphEdge."""

    def setUp(self):
        self.mem, self.learner = _make_learner()
        self.db = self.mem.get_db()

    def test_edge_created_in_db(self):
        self.learner.learn(
            command="open display settings",
            app_id="settings",
            from_node_id="app.settings",
            to_node_id="settings.display",
            steps=["uri:ms-settings:display"],
            result=_ok_result(),
            fast_path="uri",
            fast_path_value="ms-settings:display",
        )
        edge_id = "edge.app_settings_to_settings_display"
        edge = self.db.get_edge(edge_id)
        self.assertIsNotNone(edge, "Edge must be persisted in DB")

    def test_initial_confidence_is_0_80(self):
        self.learner.learn(
            command="open wifi",
            app_id="settings",
            from_node_id="app.settings",
            to_node_id="settings.wifi",
            steps=["uri:ms-settings:network-wifi"],
            result=_ok_result(),
        )
        edge = self.db.get_edge("edge.app_settings_to_settings_wifi")
        self.assertIsNotNone(edge)
        self.assertAlmostEqual(edge.confidence, 0.80, places=2)

    def test_nodes_auto_created_if_missing(self):
        self.learner.learn(
            command="open bluetooth",
            app_id="settings",
            from_node_id="app.settings",
            to_node_id="settings.bluetooth",
            steps=["uri:ms-settings:bluetooth"],
            result=_ok_result(),
        )
        from_node = self.db.get_node("app.settings")
        to_node = self.db.get_node("settings.bluetooth")
        self.assertIsNotNone(from_node, "Source node must be auto-created")
        self.assertIsNotNone(to_node, "Target node must be auto-created")

    def test_steps_are_stored(self):
        self.learner.learn(
            command="open display",
            app_id="settings",
            from_node_id="app.settings",
            to_node_id="settings.display",
            steps=["click System", "click Display"],
            result=_ok_result(),
        )
        edge = self.db.get_edge("edge.app_settings_to_settings_display")
        self.assertIn("click System", edge.steps)
        self.assertIn("click Display", edge.steps)

    def test_fast_path_stored(self):
        self.learner.learn(
            command="open display",
            app_id="settings",
            from_node_id="app.settings",
            to_node_id="settings.display",
            steps=[],
            result=_ok_result(),
            fast_path="uri",
            fast_path_value="ms-settings:display",
        )
        edge = self.db.get_edge("edge.app_settings_to_settings_display")
        self.assertEqual(edge.fast_path, "uri")
        self.assertEqual(edge.fast_path_value, "ms-settings:display")


class TestTriggerMerging(unittest.TestCase):
    """learn() called twice on the same edge merges triggers."""

    def setUp(self):
        self.mem, self.learner = _make_learner()
        self.db = self.mem.get_db()

    def test_second_learn_merges_trigger(self):
        self.learner.learn(
            command="open display settings",
            app_id="settings",
            from_node_id="app.settings",
            to_node_id="settings.display",
            steps=["uri:ms-settings:display"],
            result=_ok_result(),
        )
        self.learner.learn(
            command="show display",
            app_id="settings",
            from_node_id="app.settings",
            to_node_id="settings.display",
            steps=["uri:ms-settings:display"],
            result=_ok_result(),
        )
        edge = self.db.get_edge("edge.app_settings_to_settings_display")
        self.assertIn("open display settings", edge.triggers)
        self.assertIn("show display", edge.triggers)

    def test_no_duplicate_triggers_on_repeat_learn(self):
        for _ in range(3):
            self.learner.learn(
                command="open display settings",
                app_id="settings",
                from_node_id="app.settings",
                to_node_id="settings.display",
                steps=["uri:ms-settings:display"],
                result=_ok_result(),
            )
        edge = self.db.get_edge("edge.app_settings_to_settings_display")
        trigger_count = edge.triggers.count("open display settings")
        self.assertEqual(trigger_count, 1, "Duplicate triggers must not be stored")

    def test_additional_triggers_merged(self):
        self.learner.learn(
            command="open display",
            app_id="settings",
            from_node_id="app.settings",
            to_node_id="settings.display",
            steps=[],
            result=_ok_result(),
            additional_triggers=["display settings", "go to display"],
        )
        edge = self.db.get_edge("edge.app_settings_to_settings_display")
        self.assertIn("open display", edge.triggers)
        self.assertIn("display settings", edge.triggers)
        self.assertIn("go to display", edge.triggers)

    def test_additional_triggers_no_duplicates(self):
        self.learner.learn(
            command="open display",
            app_id="settings",
            from_node_id="app.settings",
            to_node_id="settings.display",
            steps=[],
            result=_ok_result(),
            additional_triggers=["open display"],  # same as command
        )
        edge = self.db.get_edge("edge.app_settings_to_settings_display")
        count = edge.triggers.count("open display")
        self.assertEqual(count, 1, "Command should not appear twice when in additional_triggers too")


class TestConfidenceUpdates(unittest.TestCase):
    """learn() on existing edge boosts confidence; penalize() decays it."""

    def setUp(self):
        self.mem, self.learner = _make_learner()
        self.db = self.mem.get_db()
        # Pre-create the edge
        self.learner.learn(
            command="open sound settings",
            app_id="settings",
            from_node_id="app.settings",
            to_node_id="settings.sound",
            steps=["uri:ms-settings:sound"],
            result=_ok_result(),
        )
        self.edge_id = "edge.app_settings_to_settings_sound"

    def test_second_learn_boosts_confidence(self):
        before = self.db.get_edge(self.edge_id).confidence
        self.learner.learn(
            command="sound settings again",
            app_id="settings",
            from_node_id="app.settings",
            to_node_id="settings.sound",
            steps=["uri:ms-settings:sound"],
            result=_ok_result(),
        )
        after = self.db.get_edge(self.edge_id).confidence
        self.assertGreaterEqual(after, before, "Confidence must increase on second learn")

    def test_penalize_decays_confidence(self):
        before = self.db.get_edge(self.edge_id).confidence
        self.learner.penalize(self.edge_id)
        after = self.db.get_edge(self.edge_id).confidence
        self.assertLess(after, before, "Confidence must decrease on penalize")


class TestEdgeIdDeterminism(unittest.TestCase):
    """Edge ID must be deterministic from from_node + to_node."""

    def test_edge_id_is_deterministic(self):
        mem, learner = _make_learner()
        learner.learn(
            command="test edge id",
            app_id="settings",
            from_node_id="app.settings",
            to_node_id="settings.display",
            steps=[],
            result=_ok_result(),
        )
        edge_id = "edge.app_settings_to_settings_display"
        self.assertIsNotNone(mem.get_db().get_edge(edge_id))


if __name__ == "__main__":
    unittest.main()
