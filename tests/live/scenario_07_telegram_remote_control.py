"""
Scenario 07 — Telegram Remote Control (Mock)
============================================
Tests the Telegram integration using a Mock adapter:
  - Input: Simulated message "hello jarvis"
  - Output: Verify reply is received
  - Action: "open notepad"
  - Output: Verify reply confirms action

Run:
    python -m tests.live.scenario_07_telegram_remote_control
"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from tests.live.base_scenario import LiveScenario, StepDef
from jarvis.brain.orchestrator import Orchestrator
from jarvis.llm.llm_router import LLMRouter
from jarvis.memory.memory_manager import MemoryManager
from jarvis.skills.skill_bus import SkillBus
from jarvis.input.adapters import MockTelegramAdapter

class Scenario07(LiveScenario):
    scenario_name = "07 — Telegram Remote Control"

    def setup(self):
        mem = MemoryManager()
        self.orch = Orchestrator(memory=mem, router=LLMRouter.from_config(), bus=SkillBus())
        self.orch.boot()
        self.adapter = MockTelegramAdapter(log_path="logs/telegram_test.log")
        self.chat_id = 998877
        self._stream_gen = self.adapter.stream()

    def _simulate(self, text: str):
        """Inject message and process it via the adapter."""
        self.adapter.simulate_message(text, chat_id=self.chat_id)
        # Pull the utterance from the active generator
        utterance = next(self._stream_gen)
        
        result = self.orch.process(utterance.text, source="telegram")
        
        reply_text = f"{'✅' if result.success else '❌'} {result.message or result.action_taken}"
        self.adapter.send_message(self.chat_id, reply_text)
        
        return result

    def test_greeting(self):
        self._simulate("hello jarvis")
        replies = self.adapter.get_replies()
        assert len(replies) > 0
        assert self.chat_id == replies[-1]["chat_id"]
        print(f"      Reply received: {replies[-1]['text']}")

    def test_command(self):
        self._simulate("open notepad")
        replies = self.adapter.get_replies()
        # Find if any reply contains notepad (might have multiple steps)
        assert any("notepad" in r["text"].lower() for r in replies)
        print(f"      Action confirmed in reply: {replies[-1]['text']}")

    def __init__(self):
        super().__init__()
        self.steps = [
            StepDef("greeting", self.test_greeting, timeout_s=15),
            StepDef("open_notepad", self.test_command, timeout_s=30),
        ]

if __name__ == "__main__":
    sys.exit(0 if Scenario07().run().passed else 1)
