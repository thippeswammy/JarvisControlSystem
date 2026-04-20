import sys
import os
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from Jarvis.core.jarvis_engine import JarvisEngine
from Jarvis.core.action_registry import ActionResult, registry
from Jarvis.core.intent_engine import ActionType, Intent
from Jarvis.core.jarvis_memory import MemoryManager, MemoryRecipe, MEMORY_DIR

class TestLearningFlow(unittest.TestCase):
    def setUp(self):
        # Initialize engine in mock mode
        self.engine = JarvisEngine(enable_window_tracking=False)
        self.engine._llm_fallback.use_mock = True
        self.engine._context_mgr.context.is_active = True
        
        # Clear memory directory for clean tests
        if os.path.exists(MEMORY_DIR):
            import shutil
            shutil.rmtree(MEMORY_DIR)
        os.makedirs(MEMORY_DIR)

    @patch.object(registry, 'dispatch')
    def test_sequence_learning_and_recall(self, mock_dispatch):
        """
        Scenario:
        1. User says "open secret page" -> fails
        2. User says "open settings" -> success
        3. User says "click privacy" -> success
        4. User says "remember that as open secret page" -> Jarvis learns
        5. User says "open secret page" again -> Jarvis replays 2 steps
        """
        # 1. Failure (Wait, "open secret page" might be a known Intent, so we mock dispatch to fail)
        mock_dispatch.return_value = ActionResult.fail("Not found")
        self.engine.process("open secret page")
        self.assertEqual(self.engine._fallback_original_command, "open secret page")

        # 2. Step 1: success
        mock_dispatch.return_value = ActionResult.ok("Opened settings")
        self.engine.process("open settings")
        
        # 3. Step 2: success
        mock_dispatch.return_value = ActionResult.ok("Clicked privacy")
        self.engine.process("click privacy")
        self.assertEqual(len(self.engine._fallback_steps_taken), 2)

        # 4. Learning
        learn_intent = Intent(
            action=ActionType.LEARN,
            target="open secret page",
            category="navigation",
            confidence=1.0
        )
        # Mock LLM to return the learn intent
        with patch.object(self.engine._llm_fallback, 'analyze', return_value=(learn_intent, None)):
            result = self.engine.process("remember that as open secret page")
            self.assertTrue(result.success)

        # 5. Recall / Replay
        # Reset counters for replay validation
        mock_dispatch.reset_mock()
        mock_dispatch.return_value = ActionResult.ok("Step Success")
        
        # Execute the high-level command
        result = self.engine.process("open secret page")
        self.assertTrue(result.success)
        
        # VERIFY: Dispatch should have been called TWICE (for "open settings" and "click privacy")
        self.assertEqual(mock_dispatch.call_count, 2)
        
    def tearDown(self):
        self.engine.shutdown()

if __name__ == "__main__":
    unittest.main()
