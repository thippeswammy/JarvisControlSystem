import sys
import os
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from Jarvis.core.jarvis_llm import LLMFallbackModule
from Jarvis.core.intent_engine import ActionType
from Jarvis.core.jarvis_engine import JarvisEngine
from Jarvis.core.action_registry import ActionRegistry, ActionResult, registry

class TestLLMFallbackMock(unittest.TestCase):
    def setUp(self):
        self.llm = LLMFallbackModule(use_mock=True)

    def test_mock_successful_fuzzy_match(self):
        from Jarvis.core.context_manager import Context
        ctx = Context(active_app="explorer")
        context_data = {"available_targets": ["Arduino", "Python"]}
        
        intent, user_prompt = self.llm.analyze("open folder rduino", ActionType.UNKNOWN, ctx, context_data)
        
        self.assertIsNotNone(intent)
        self.assertIsNone(user_prompt)
        self.assertEqual(intent.action, ActionType.NAVIGATE_LOCATION)
        self.assertEqual(intent.target, "Arduino")
        self.assertEqual(intent.confidence, 0.98)

    def test_mock_unsuccessful_fuzzy_match_asks_user(self):
        from Jarvis.core.context_manager import Context
        ctx = Context(active_app="explorer")
        context_data = {"available_targets": ["Python"]}
        
        intent, user_prompt = self.llm.analyze("open folder rduino", ActionType.UNKNOWN, ctx, context_data)
        
        self.assertIsNone(intent)
        self.assertIsNotNone(user_prompt)
        self.assertIn("clarify", user_prompt)

    @patch('Jarvis.navigator.explorer_handler.ExplorerHandler.navigate_to_path')
    @patch('Jarvis.navigator.explorer_handler.ExplorerHandler.navigate_to_named_location')
    def test_jarvis_engine_integration(self, mock_named, mock_path):
        # We want the original handlers to fail navigating to "rduino"
        mock_named.return_value = False
        mock_path.return_value = False
        
        # When it tries to navigate to "Arduino" (the LLM corrected target), it succeeds
        def path_side_effect(target):
            if "Arduino" in target:
                return True
            return False
            
        mock_path.side_effect = path_side_effect
        mock_named.return_value = False
        
        # Disable window tracking for test
        engine = JarvisEngine(enable_window_tracking=False)
        engine.context.active_app = "explorer"
        engine.context.is_active = True
        
        # "open folder rduino" parses to ActionType.NAVIGATE_LOCATION, target="rduino"
        # The registry dispatches it, it fails (because mock_path returns False).
        # Fallback intercepts it. In mock mode, context active_app="explorer" gives ["Arduino", ...].
        # The Fallback returns {"action": "NAVIGATE_LOCATION", "target": "Arduino", "confidence": 0.98}.
        # Engine dispatches corrected intent, mock_path("Arduino") returns True.
        # It succeeds!
        
        res = engine.process("open folder rduino")
        
        self.assertTrue(res.success)
        self.assertEqual(res.message, "Navigated to Arduino.")

if __name__ == "__main__":
    unittest.main()
