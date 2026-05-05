import sys
import re
import time
import logging
from pathlib import Path
from typing import Dict, List

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from jarvis.main import build_orchestrator
from jarvis.input.adapters import MockTelegramAdapter
from jarvis.brain.message_formatter import MessageFormatter

# Configure logging to be quiet for the runner
logging.getLogger("jarvis").setLevel(logging.WARNING)

class TelegramTestRunner:
    def __init__(self, test_md_path: str = "test.md"):
        self.test_md_path = PROJECT_ROOT / test_md_path
        self.categories = self._parse_test_md()
        self.orch = build_orchestrator()
        self.adapter = MockTelegramAdapter()
        self.chat_id = 12345
        self.username = "LocalTester"

    def _parse_test_md(self) -> Dict[str, List[str]]:
        """Parses test.md into a dictionary of categories and their test cases."""
        if not self.test_md_path.exists():
            print(f"❌ Error: {self.test_md_path} not found.")
            return {}

        content = self.test_md_path.read_text(encoding="utf-8")
        categories = {}
        
        # Match headers like ## 🔵 1. CHAT CASES
        current_cat = None
        
        lines = content.splitlines()
        in_code_block = False
        
        for line in lines:
            line = line.strip()
            if line.startswith("##"):
                current_cat = line.replace("##", "").strip()
                categories[current_cat] = []
                continue
            
            if line.startswith("```"):
                in_code_block = not in_code_block
                continue
            
            if in_code_block and line and current_cat:
                categories[current_cat].append(line)
        
        return categories

    def display_menu(self):
        print("\n" + "="*60)
        print(" 🤖 JARVIS TELEGRAM TEST RUNNER (MOCK MODE) ")
        print("="*60)
        
        flat_list = []
        cat_idx = 1
        for cat, cases in self.categories.items():
            print(f"\n{cat}")
            for i, case in enumerate(cases, 1):
                idx = len(flat_list) + 1
                print(f"  {idx:2d}. {case}")
                flat_list.append((case, cat))
        
        print("\n" + "-"*60)
        print("  0. Exit")
        print("  R. Run All (Summary mode)")
        print("-"*60)
        return flat_list

    def run_case(self, text: str, category: str = ""):
        print(f"\n[{category}]")
        print(f"👤 User >> {text}")
        
        # Inject into adapter
        self.adapter.simulate_message(text, chat_id=self.chat_id, username=self.username)
        
        # Extract from stream (this mimics the main.py loop logic)
        try:
            utterance = next(self.adapter.stream())
            
            # Start "typing" simulation UI-side
            print("⏳ Jarvis is typing...", end="\r")
            
            # Process via orchestrator
            results = self.orch.process(
                utterance.text, 
                source="telegram",
                typing_callback=lambda: None # Mock doesn't need real typing
            )
            
            # Clear typing line
            print(" " * 30, end="\r")
            
            reply_text = MessageFormatter.format(results, source="telegram")
            
            # Simulate real Telegram reply behavior
            print(f"🤖 Jarvis << \n{reply_text}")
            
            return results
        except StopIteration:
            print("❌ Stream stopped unexpectedly.")
            return None

    def start(self):
        while True:
            flat_list = self.display_menu()
            choice = input("\nSelect test number (or 0/R): ").strip().upper()
            
            if choice == "0":
                break
            
            if choice == "R":
                print("\n🚀 Running all cases...")
                for case, cat in flat_list:
                    self.run_case(case, cat)
                    time.sleep(1)
                print("\n✅ All tests completed.")
                break
            
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(flat_list):
                    case, cat = flat_list[idx]
                    self.run_case(case, cat)
                    input("\nPress Enter to return to menu...")
                else:
                    print("❌ Invalid selection.")
            except ValueError:
                print("❌ Please enter a number.")

if __name__ == "__main__":
    runner = TelegramTestRunner()
    runner.start()
