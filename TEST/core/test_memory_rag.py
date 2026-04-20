import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from Jarvis.core.jarvis_memory import MemoryManager, MemoryRecipe, MEMORY_DIR
from Jarvis.core.context_collector import ContextSnapshot

class TestMemoryRAG(unittest.TestCase):
    def setUp(self):
        # We instantiate MemoryManager. It will create dummy files if they don't exist.
        self.memory = MemoryManager()

    def test_dynamic_rag_filtering(self):
        """
        Verify that get_relevant_context() correctly filters out
        unrelated text matches even if the context is a perfect match.
        """
        
        # We manually inject some recipes into the memory manager's internal state
        # instead of writing to disk to keep the test clean, but since get_relevant_context 
        # reads from disk, we will mock `_load_all_recipes`.
        
        recipes = [
            MemoryRecipe(
                command="open advanced display",
                steps=["open settings system", "open settings display", "scroll down", "click advanced display"],
                precondition_app="settings",
                precondition_location="display",
                category="navigation"
            ),
            MemoryRecipe(
                command="go to network adapter",
                steps=["open settings network", "scroll down", "click advanced network settings", "click network adapters"],
                precondition_app="settings",
                precondition_location="network",
                category="settings" 
            ),
            MemoryRecipe(
                command="open network share folder",
                steps=["open file explorer", "type in address bar \\\\Server\\Share"],
                precondition_app="explorer",
                precondition_location="documents",
                category="folders"
            )
        ]

        # Patch _load_all_recipes on the instance
        self.memory._load_all_recipes = lambda: recipes

        # Scenario: User is in Settings -> Network page, and says: "open network configurator"
        snap = ContextSnapshot(
            active_app="settings",
            current_location="network",
            active_window_title="Settings - Network"
        )

        result_md = self.memory.get_relevant_context("open network configurator", snap, top_n=3)

        # "go to network adapter" shares 'network', and is in correct context. -> SHOULD BE INCLUDED
        self.assertIn("go to network adapter", result_md)
        
        # "open network share folder" shares 'network' text, but context is totally wrong (explorer).
        # It might still score high enough to be included if text match is strong enough.
        self.assertIn("open network share folder", result_md)

        # "open advanced display" has NO text in common with "open network configurator".
        # EVEN THOUGH it's in the "settings" app context, it must be completely dropped because text_score < 0.15.
        self.assertNotIn("open advanced display", result_md)

    def test_dynamic_category_saving(self):
        """
        Test that giving a custom category creates a new file rather than defaulting to navigation.
        """
        import uuid
        test_cat = f"test_cat_{uuid.uuid4().hex[:6]}"
        
        snap = ContextSnapshot()
        
        self.memory.save(
            command="test dynamic category output",
            steps=["step 1"],
            snapshot=snap,
            category=test_cat
        )
        
        expected_file = os.path.join(MEMORY_DIR, f"{test_cat}.md")
        self.assertTrue(os.path.exists(expected_file))
        
        # Cleanup
        os.remove(expected_file)


if __name__ == "__main__":
    unittest.main()
