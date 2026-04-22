import sys
import os
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from Jarvis.core.jarvis_llm import LLMFallbackModule
from Jarvis.core.intent_engine import ActionType
from Jarvis.core.jarvis_engine import JarvisEngine
from Jarvis.core.context_collector import ContextSnapshot


class TestLLMFallbackMock(unittest.TestCase):

    def setUp(self):
        self.llm = LLMFallbackModule(use_mock=True)

    def _make_snapshot(self, app="explorer", location="", targets=None):
        snap = ContextSnapshot()
        snap.active_app = app
        snap.current_location = location
        snap.visible_targets = targets or []
        return snap

    def test_mock_successful_fuzzy_match(self):
        snap = self._make_snapshot(app="explorer", targets=["Arduino", "Python"])
        intent, user_prompt = self.llm.analyze("open folder rduino", ActionType.UNKNOWN, snap)

        self.assertIsNotNone(intent)
        self.assertIsNone(user_prompt)
        self.assertEqual(intent.action, ActionType.NAVIGATE_LOCATION)
        self.assertEqual(intent.target, "Arduino")
        self.assertGreaterEqual(intent.confidence, 0.95)

    def test_mock_unsuccessful_fuzzy_match_asks_user(self):
        # No "arduino" in visible targets → LLM should ask user
        snap = self._make_snapshot(app="explorer", targets=["Python"])
        intent, user_prompt = self.llm.analyze("open folder rduino", ActionType.UNKNOWN, snap)

        self.assertIsNone(intent)
        self.assertIsNotNone(user_prompt)
        self.assertIn("clarify", user_prompt.lower())

    @patch('Jarvis.navigator.explorer_handler.ExplorerHandler.navigate_to_path')
    @patch('Jarvis.navigator.explorer_handler.ExplorerHandler.navigate_to_named_location')
    def test_jarvis_engine_integration(self, mock_named, mock_path):
        """
        Full pipeline test:
          "open folder rduino"
          → NAVIGATE_LOCATION(rduino) → handler called, mock returns False
          → ContextCollector builds snapshot with visible_targets=["Arduino", ...]
          → LLM mock sees "rduino" + "arduino" in targets → corrects to Arduino
          → handler called again with Arduino → mock returns True → SUCCESS
        """
        def path_side_effect(target):
            if "Arduino" in str(target) or "arduino" in str(target).lower():
                return True
            return False

        mock_named.return_value = False
        mock_path.side_effect = path_side_effect

        # Patch ContextCollector to return a snapshot with Arduino visible
        with patch(
            'Jarvis.core.context_collector.ContextCollector.collect',
            return_value=ContextSnapshot(
                active_app="explorer",
                current_location=r"C:\Users\thipp\Documents",
                visible_targets=["Arduino", "Python", "Projects"],
            )
        ):
            engine = JarvisEngine(enable_window_tracking=False)
            engine.context.active_app = "explorer"
            engine.context.is_active = True

            res = engine.process("open folder rduino")

        self.assertTrue(res.success, f"Expected success but got: {res.message}")
        self.assertIn("Arduino", res.message)


if __name__ == "__main__":
    unittest.main()
