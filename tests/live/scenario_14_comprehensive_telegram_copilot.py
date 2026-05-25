"""
Scenario 14 — Comprehensive Telegram Copilot
============================================
Tests the entire OS Cognition & Communication stack:
  - Local NLU & Planning via gemma3:4b (Ollama)
  - Dynamic App Pathfinder registry mapping
  - Screen focus & keyboard text simulation
  - SQLite Structured Temporal Memory queries
  - Simulated chat interface matching Telegram adapter formatting

Run:
    python -m tests.live.scenario_14_comprehensive_telegram_copilot
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


class Scenario14(LiveScenario):
    scenario_name = "14 — Comprehensive Telegram Copilot"

    def setup(self):
        # Build orchestrator connected to the active LLM router (configured for local Ollama primary)
        mem = MemoryManager()
        self.orch = Orchestrator(memory=mem, router=LLMRouter.from_config(), bus=SkillBus())
        self.orch.boot()
        
        # Set up mock telegram adapter focused on telegram_test.log
        self.adapter = MockTelegramAdapter(log_path="logs/telegram_test.log")
        self.chat_id = 998877
        self._stream_gen = self.adapter.stream()

    def _simulate(self, text: str):
        """Simulate a Telegram chat interaction."""
        print(f"\n[Telegram Chat] 👤 User >> {text}")
        self.adapter.simulate_message(text, chat_id=self.chat_id, username="TelegramCopilotTester")
        
        # Pull generated utterance
        utterance = next(self._stream_gen)
        
        # Route through NLU + Planner + Executor
        results = self.orch.process(utterance.text, source="telegram")
        
        # Format and deliver response back to the channel
        reply_text = MessageFormatter.format(results, source="telegram")
        self.adapter.send(f"telegram:{self.chat_id}", reply_text)
        
        print(f"[Telegram Chat] 🤖 Jarvis <<\n{reply_text}")
        return results

    def test_greet(self):
        results = self._simulate("hello jarvis")
        replies = self.adapter.get_replies()
        assert len(replies) > 0, "No reply received for greeting"
        assert "hello" in replies[-1]["text"].lower() or "assist" in replies[-1]["text"].lower(), "Greeting reply did not contain hello/assist context"

    def test_dynamic_open(self):
        results = self._simulate("open notepad")
        replies = self.adapter.get_replies()
        assert any("notepad" in r["text"].lower() or "launched" in r["text"].lower() for r in replies), "Failed to confirm Notepad launch"

    def test_typing(self):
        results = self._simulate("write a short note about the advantages of local AI models in notepad")
        replies = self.adapter.get_replies()
        assert len(replies) > 0, "No reply received for typing action"

    def test_temporal_lookup(self):
        # Querying history using the brand new SQLite Structured Temporal Memory Graph!
        results = self._simulate("What was my very first command in this session?")
        replies = self.adapter.get_replies()
        assert len(replies) > 0, "No reply received for temporal memory lookup"

    def test_close(self):
        results = self._simulate("close notepad")
        replies = self.adapter.get_replies()
        assert any("notepad" in r["text"].lower() or "closed" in r["text"].lower() for r in replies), "Failed to confirm Notepad close"

    def __init__(self):
        super().__init__()
        self.steps = [
            StepDef("greet",           self.test_greet,           timeout_s=25),
            StepDef("dynamic_open",    self.test_dynamic_open,    timeout_s=30),
            StepDef("typing",          self.test_typing,          timeout_s=40),
            StepDef("temporal_lookup", self.test_temporal_lookup, timeout_s=30),
            StepDef("close",           self.test_close,           timeout_s=25),
        ]


if __name__ == "__main__":
    sys.exit(0 if Scenario14().run().passed else 1)
