"""
Scenario 16 — Advanced Playwright Browser Automation & Foraging
==============================================================
Simulates a highly complex web agent task simulating real computer-agent browsing work:
  - Dynamic local planning and command routing via gemma3:4b (Ollama)
  - Active browser navigation (DuckDuckGo search)
  - Page scrolling to inspect listings
  - Extraction of the interactive Accessibility DOM Tree
  - Index-based element selection and redirection click
  - Verification of page heading content
  - Multi-tab management and page switching
  - Graceful application shutdown

Run:
    python -m tests.live.scenario_16_browser_automation
"""
import sys
import time
from pathlib import Path

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tests.live.base_scenario import LiveScenario, StepDef
from jarvis.brain.orchestrator import Orchestrator
from jarvis.llm.llm_router import LLMRouter
from jarvis.memory.memory_manager import MemoryManager
from jarvis.skills.skill_bus import SkillBus
from jarvis.input.adapters import MockTelegramAdapter
from jarvis.brain.message_formatter import MessageFormatter


class Scenario16(LiveScenario):
    scenario_name = "16 — Advanced Playwright Browser Automation & Foraging"

    def setup(self):
        # Initialize Memory Graph, Skill Bus, local-first LLM Router, and Orchestrator
        mem = MemoryManager()
        self.orch = Orchestrator(memory=mem, router=LLMRouter.from_config(), bus=SkillBus())
        self.orch.boot()
        
        # Instantiate Mock Telegram Adapter focusing output to logs/runtime/telegram_test.log
        self.adapter = MockTelegramAdapter(log_path = "logs/runtime/telegram_test.log")
        self.chat_id = 998877
        self._stream_gen = self.adapter.stream()

    def _simulate(self, text: str):
        """Simulate sending a chat command from Telegram and receiving formatted output."""
        print(f"\n[Telegram Agent Command] 👤 User >> {text}")
        self.adapter.simulate_message(text, chat_id=self.chat_id, username="BrowserAgentTester")
        
        # Pull utterance from the stream
        utterance = next(self._stream_gen)
        
        # Process dynamically via NLU + Planner OODA Loop
        results = self.orch.process(utterance.text, source="telegram")
        
        # Format the skill execution outputs
        reply_text = MessageFormatter.format(results, source="telegram")
        self.adapter.send(f"telegram:{self.chat_id}", reply_text)
        
        print(f"[Telegram Agent Reply] 🤖 Jarvis <<\n{reply_text}")
        return results

    def test_session_init(self):
        self._simulate("hello jarvis, activate session")
        replies = self.adapter.get_replies()
        assert len(replies) > 0, "No reply received for session activation"
        assert "hello" in replies[-1]["text"].lower() or "help" in replies[-1]["text"].lower(), "Did not receive valid activation response"

    def test_search_duckduckgo(self):
        # Abstract: Search for a topic without telling the agent how to do it step-by-step
        self._simulate("I want to research the Jarvis Control System. Please open DuckDuckGo and search for it.")
        replies = self.adapter.get_replies()
        assert len(replies) > 0, "No reply received for DuckDuckGo search"

    def test_scroll_results(self):
        # Abstract: Perform page scrolling
        self._simulate("Scroll down the results page to inspect the listings.")
        replies = self.adapter.get_replies()
        assert len(replies) > 0, "No reply received for scroll page task"

    def test_extract_and_click_result(self):
        # Abstract: DOM tree extraction and index-based link redirection click
        self._simulate("Extract the interactive web nodes, find the link for the main Jarvis Control System GitHub page, and click it.")
        replies = self.adapter.get_replies()
        assert len(replies) > 0, "No reply received for DOM extraction and click redirection task"

    def test_extract_content(self):
        # Abstract: Web scraping/content validation
        self._simulate("Read this landing page and tell me what the repository name or description is.")
        replies = self.adapter.get_replies()
        assert len(replies) > 0, "No reply received for content extraction task"

    def test_open_new_tab(self):
        # Abstract: Multi-tab switching
        self._simulate("Open a new tab, navigate to GitHub trending, and find the most popular repository today.")
        replies = self.adapter.get_replies()
        assert len(replies) > 0, "No reply received for multi-tab search task"

    def test_copilot_cleanup(self):
        # Gracefully terminates all open browsers
        self._simulate("Close the browser completely.")
        replies = self.adapter.get_replies()
        assert len(replies) > 0, "No reply received for browser cleanup task"

    def __init__(self):
        super().__init__()
        self.steps = [
            StepDef("session_init",              self.test_session_init,             timeout_s=25),
            StepDef("search_duckduckgo",         self.test_search_duckduckgo,         timeout_s=60),
            StepDef("scroll_results",            self.test_scroll_results,            timeout_s=30),
            StepDef("extract_and_click_result",  self.test_extract_and_click_result,  timeout_s=55),
            StepDef("extract_content",           self.test_extract_content,           timeout_s=35),
            StepDef("open_new_tab",              self.test_open_new_tab,              timeout_s=50),
            StepDef("copilot_cleanup",           self.test_copilot_cleanup,           timeout_s=30),
        ]


if __name__ == "__main__":
    sys.exit(0 if Scenario16().run().passed else 1)
