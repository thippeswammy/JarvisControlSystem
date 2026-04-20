import sys
import os
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from Jarvis.core.jarvis_engine import JarvisEngine
from Jarvis.core.action_registry import ActionResult
from Jarvis.core.intent_engine import ActionType, Intent
from Jarvis.core.jarvis_memory import MemoryManager, MemoryRecipe, MEMORY_DIR

class TestLearningFlow(unittest.TestCase):
    def setUp(self):
        # Initialize engine in mock mode
        self.engine = JarvisEngine(enable_window_tracking=False)
        self.engine._llm_fallback.use_mock = True
        
        # Mock the context manager to be active
        self.engine._context_mgr.context.is_active = True
        
        # Clear memory for test
        if os.path.exists(MEMORY_DIR):
            for f in os.listdir(MEMORY_DIR):
                if f.startswith("test_") or f == "navigation.md":
                    try:
                        # We won't actually delete navigation.md but we will check contents
                        pass
                    except: pass

    @patch('Jarvis.core.action_registry.ActionRegistry.dispatch')
    def test_sequence_learning_and_recall(self, mock_dispatch):
        """
        Scenario:
        1. User says "open secret page" -> fails (unknown)
        2. User says "open settings" -> success
        3. User says "click privacy" -> success
        4. User says "remember that as open secret page" -> Jarvis learns
        5. User says "open secret page" again -> Jarvis replays 2 steps
        """
        # 1. Failure
        mock_dispatch.return_value = ActionResult.fail("Not found")
        self.engine.process("open secret page")
        self.assertEqual(self.engine._fallback_original_command, "open secret page")
        self.assertEqual(len(self.engine._fallback_steps_taken), 0)

        # 2. Step 1: success
        mock_dispatch.return_value = ActionResult.ok("Opened settings")
        self.engine.process("open settings")
        self.assertIn("open settings", self.engine._fallback_steps_taken)

        # 3. Step 2: success
        mock_dispatch.return_value = ActionResult.ok("Clicked privacy")
        self.engine.process("click privacy")
        self.assertIn("click privacy", self.engine._fallback_steps_taken)
        self.assertEqual(len(self.engine._fallback_steps_taken), 2)

        # 4. Learning
        # We need to mock the LLM to return a LEARN intent
        learn_intent = Intent(
            action=ActionType.LEARN,
            target="open secret page",
            category="navigation",
            confidence=1.0
        )
        with patch.object(self.engine._llm_fallback, 'analyze', return_value=(learn_intent, None)):
            result = self.engine.process("remember that as open secret page")
            self.assertTrue(result.success)
            self.assertIn("Learned recipe", result.message)

        # Verify it's in memory
        recipe = self.engine._memory.recall("open secret page", self.engine._context_collector.collect())
        self.assertIsNotNone(recipe)
        self.assertEqual(recipe.steps, ["open settings", "click privacy"])

        # 5. Recall / Replay
        # Reset counters
        mock_dispatch.reset_mock()
        mock_dispatch.return_value = ActionResult.ok("Step done")
        
        # When we process "open secret page" now, it should recall and dispatch 2 steps
        # Note: process() will check memory first
        result = self.engine.process("open secret page")
        self.assertTrue(result.success)
        # Should have called dispatch twice (once for each step)
        self.assertEqual(mock_dispatch.call_count, 2)
        
    def tearDown(self):
        self.engine.shutdown()

if __name__ == "__main__":
    unittest.main()
