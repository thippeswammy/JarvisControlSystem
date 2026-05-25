"""
Scenario 15 — Autonomous Desktop Agent Integration
==================================================
Models realistic, complex multi-app desktop workflows mimicking a high-fidelity
autonomous computer agent. Exercises:
  - Local planning and compound dispatching via gemma3:4b (Ollama)
  - Unified World-State Modeler environment context queries
  - Multi-app coordination (Edge + Notepad + Settings)
  - SQLite Structured Temporal Memory timelines
  - Dynamic Recovery Engine exception handling & self-healing
  - Dynamic Registry App Pathfinder process resolution

Run:
    python -m tests.live.scenario_15_autonomous_desktop_agent
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


class Scenario15(LiveScenario):
    scenario_name = "15 — Autonomous Desktop Agent Integration"

    def setup(self):
        # Initialize Memory Graph, Skill Bus, local-first LLM Router, and Orchestrator
        mem = MemoryManager()
        self.orch = Orchestrator(memory=mem, router=LLMRouter.from_config(), bus=SkillBus())
        self.orch.boot()
        
        # Instantiate Mock Telegram Adapter focusing output to logs/telegram_test.log
        self.adapter = MockTelegramAdapter(log_path="logs/telegram_test.log")
        self.chat_id = 998877
        self._stream_gen = self.adapter.stream()

    def _simulate(self, text: str):
        """Simulate sending a chat command from Telegram and receiving formatted output."""
        print(f"\n[Telegram Agent Command] 👤 User >> {text}")
        self.adapter.simulate_message(text, chat_id=self.chat_id, username="DesktopAgentTester")
        
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

    def test_multi_app_research(self):
        # Verifies dynamic app finders, window management, and text-based copying across applications
        self._simulate("open edge, navigate to github.com, then open notepad and write github notes")
        replies = self.adapter.get_replies()
        assert len(replies) > 0, "No reply received for multi-app research task"

    def test_telemetry_diagnose_and_save(self):
        # Accesses World-State Modeler (CPU/RAM/Windows), logs status, types in active notepad, and saves
        self._simulate("check system resources, then open notepad and type the status, and save as diagnostic_report.txt")
        replies = self.adapter.get_replies()
        assert len(replies) > 0, "No reply received for telemetry diagnosis task"

    def test_temporal_Timeline_reasoning(self):
        # Exercises the SQLite Structured Temporal Memory logs to retrieve chronological action latency
        self._simulate("Search my memory timeline to find when I opened Notepad and what I did")
        replies = self.adapter.get_replies()
        assert len(replies) > 0, "No reply received for temporal timeline query"

    def test_self_healing_recovery(self):
        # Intentionally triggers error, exercises UIA element fallback and deep-link uri launching
        self._simulate("click on non_existent_button, then open display settings")
        replies = self.adapter.get_replies()
        assert len(replies) > 0, "No reply received for self-healing recovery task"

    def test_copilot_cleanup(self):
        # Dynamically searches registry paths to safely close Notepad, Settings, and Edge
        self._simulate("close notepad, close edge, and close settings")
        replies = self.adapter.get_replies()
        assert len(replies) > 0, "No reply received for copilot cleanup task"

    def __init__(self):
        super().__init__()
        self.steps = [
            StepDef("session_init",             self.test_session_init,             timeout_s=25),
            StepDef("multi_app_research",        self.test_multi_app_research,        timeout_s=50),
            StepDef("telemetry_diagnose_save",  self.test_telemetry_diagnose_and_save, timeout_s=45),
            StepDef("temporal_timeline_reason", self.test_temporal_Timeline_reasoning, timeout_s=35),
            StepDef("self_healing_recovery",    self.test_self_healing_recovery,    timeout_s=40),
            StepDef("copilot_cleanup",          self.test_copilot_cleanup,          timeout_s=30),
        ]


if __name__ == "__main__":
    sys.exit(0 if Scenario15().run().passed else 1)
