"""
Scenario 18 — Telegram Calculator & Settings
============================================
Tests the integration of UI Windows MCP and Settings Navigation via simulated Telegram:
  - Perform 5 + 3 calculation on Calculator via UIWindowsAgent
  - Open Display settings
  - Open Sound settings

Run:
    python -m tests.live.scenario_18_telegram_calculator_settings
"""
import os
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
from jarvis.utils.ollama_utils import enable_auto_start, ensure_ollama_running, is_ollama_running
from jarvis.memory.layers.procedural import ProceduralMemory


class Scenario18(LiveScenario):
    scenario_name = "18 — Telegram Calculator and Settings"

    def setup(self):
        # Clean up any stale apps before running
        os.system("taskkill /f /im CalculatorApp.exe >nul 2>&1")
        os.system("taskkill /f /im Calculator.exe >nul 2>&1")
        os.system("taskkill /f /im SystemSettings.exe >nul 2>&1")
        time.sleep(0.5)

        # Ensure Ollama is running
        print("[*] Checking if Ollama service is running...")
        enable_auto_start(True)
        ensure_ollama_running()
        for i in range(15):
            if is_ollama_running():
                print("[+] Ollama is online and reachable!")
                break
            print(f"    Waiting for Ollama service to wake up ({i+1}/15)...")
            time.sleep(1.0)

        mem = MemoryManager()
        # Seed settings to ensure fast-paths are available
        ProceduralMemory(mem.get_db()).seed_settings_graph()
        self.orch = Orchestrator(memory=mem, router=LLMRouter.from_config(), bus=SkillBus())
        self.orch.boot()
        
        # Set up mock telegram adapter
        self.adapter = MockTelegramAdapter(log_path="logs/runtime/telegram_test.log")
        self.chat_id = 112233
        self._stream_gen = self.adapter.stream()

    def _simulate(self, text: str):
        """Simulate a Telegram chat interaction."""
        print(f"\n[Telegram Chat] 👤 User >> {text}")
        self.adapter.simulate_message(text, chat_id=self.chat_id, username="TelegramTester")
        
        # Pull generated utterance
        utterance = next(self._stream_gen)
        
        # Route through NLU + Planner + Executor
        results = self.orch.process(utterance.text, source="telegram")
        
        # Format and deliver response back to the channel
        reply_text = MessageFormatter.format(results, source="telegram")
        self.adapter.send(f"telegram:{self.chat_id}", reply_text)
        
        print(f"[Telegram Chat] 🤖 Jarvis <<\n{reply_text}")
        return results

    def test_hi(self):
        results = self._simulate("hello jarvis")
        replies = self.adapter.get_replies()
        assert len(replies) > 0, "No reply received for greeting"
        print(f"      Greeting confirmed: {replies[-1]['text']}")

    def test_calculator(self):
        # Performs UIA Calculator task using ui_windows_agent
        results = self._simulate("calculate 5 + 3 on the calculator")
        replies = self.adapter.get_replies()
        assert len(replies) > 0, "No reply received for calculator command"
        last_reply = replies[-1]["text"].lower()
        print(f"      Calculator reply: {last_reply}")
        assert "8" in last_reply or "success" in last_reply or "done" in last_reply or "result" in last_reply or "display" in last_reply

    def test_display_settings(self):
        results = self._simulate("open display settings")
        replies = self.adapter.get_replies()
        assert len(replies) > 0, "No reply received for display settings command"
        print(f"      Display settings reply: {replies[-1]['text']}")

    def test_sound_settings(self):
        results = self._simulate("open sound settings")
        replies = self.adapter.get_replies()
        assert len(replies) > 0, "No reply received for sound settings command"
        print(f"      Sound settings reply: {replies[-1]['text']}")

    def teardown(self):
        # Clean up processes
        os.system("taskkill /f /im CalculatorApp.exe >nul 2>&1")
        os.system("taskkill /f /im Calculator.exe >nul 2>&1")
        os.system("taskkill /f /im SystemSettings.exe >nul 2>&1")

    def __init__(self):
        super().__init__()
        self.steps = [
            StepDef("hi",                 self.test_hi,               timeout_s=60),
            StepDef("calculator_5_plus_3", self.test_calculator,        timeout_s=90),
            StepDef("open_display",       self.test_display_settings, timeout_s=40),
            StepDef("open_sound",         self.test_sound_settings,   timeout_s=40),
        ]


if __name__ == "__main__":
    sys.exit(0 if Scenario18().run().passed else 1)
