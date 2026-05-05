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
        
        results = self.orch.process(utterance.text, source="telegram")
        
        from jarvis.brain.message_formatter import MessageFormatter
        reply_text = MessageFormatter.format(results, source="telegram")
        self.adapter.send_message(self.chat_id, reply_text)
        
        # Return the last result for assertions (or first if needed)
        return results[-1] if results else SkillResult(success=False)


    def test_hi(self):
        self._simulate("hi")
        replies = self.adapter.get_replies()
        assert len(replies) > 0
        print(f"      Reply received: {replies[-1]['text']}")

    def test_status(self):
        self._simulate("System status")
        replies = self.adapter.get_replies()
        assert any("cpu" in r["text"].lower() or "memory" in r["text"].lower() for r in replies)
        print(f"      Status received: {replies[-1]['text']}")

    def test_command(self):
        self._simulate("open notepad")
        replies = self.adapter.get_replies()
        assert any("notepad" in r["text"].lower() for r in replies)
        print(f"      Action confirmed: {replies[-1]['text']}")

    def test_type(self):
        self._simulate("type I am ready")
        replies = self.adapter.get_replies()
        assert any("typed" in r["text"].lower() or "✅" in r["text"] for r in replies)
        print(f"      Type confirmed: {replies[-1]['text']}")

    def test_gpu_info(self):
        # This will likely use the LLM to generate a description of the GPU and then Jarvis might type it or just reply.
        # If the user says "write about the GPU", Jarvis should probably type it into the active notepad.
        self._simulate("write a short sentence about the GPU in notepad")
        replies = self.adapter.get_replies()
        assert len(replies) > 0
        print(f"      GPU Task result: {replies[-1]['text']}")

    def __init__(self):
        super().__init__()
        self.steps = [
            StepDef("hi",            self.test_hi,       timeout_s=15),
            StepDef("status",        self.test_status,   timeout_s=15),
            StepDef("open_notepad",  self.test_command,  timeout_s=30),
            StepDef("type_ready",    self.test_type,     timeout_s=20),
            StepDef("write_gpu",     self.test_gpu_info, timeout_s=40),
        ]

if __name__ == "__main__":
    sys.exit(0 if Scenario07().run().passed else 1)
