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
        
        # Instantiate Mock Telegram Adapter focusing output to logs/runtime/telegram_test.log
        self.adapter = MockTelegramAdapter(log_path = "logs/runtime/telegram_test.log")
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
        # Abstract: User gives high-level goal, agent must resolve to Edge and Notepad
        self._simulate("I want to research the GitHub website. Please launch Microsoft Edge, go to github.com, then summarize my notes in Notepad.")
        replies = self.adapter.get_replies()
        assert len(replies) > 0, "No reply received for multi-app research task"

    def test_telemetry_diagnose_and_save(self):
        # Abstract: Needs resources, writing app (Notepad), and saving it in %TEMP%
        import os
        temp_dir = os.path.expandvars("%TEMP%")
        target_file = os.path.join(temp_dir, "resource_check.txt")
        # Ensure clean state prior to test
        if os.path.exists(target_file):
            try: os.remove(target_file)
            except: pass

        self._simulate(f"I need a full check of my computer's resources. Save this diagnostic report as '{target_file}' using my writing application.")
        replies = self.adapter.get_replies()
        assert len(replies) > 0, "No reply received for telemetry diagnosis task"

    def test_file_explorer_verification(self):
        # Abstract: Navigate folders and verify file exists in File Explorer
        self._simulate("Please open my file explorer, navigate to my temp folder, and verify that the file resource_check.txt was created successfully.")
        replies = self.adapter.get_replies()
        assert len(replies) > 0, "No reply received for file explorer verification task"

    def test_settings_deep_navigation(self):
        # Abstract: Deeper settings and personalization checks
        self._simulate("My display options feel incorrect. Open my personalization settings to help me configure it, but make sure to check display settings as well.")
        replies = self.adapter.get_replies()
        assert len(replies) > 0, "No reply received for deep settings task"

    def test_temporal_timeline_reasoning(self):
        # Exercises timeline queries in SQLite Structured Temporal Memory
        self._simulate("Search my action history timeline to see when I worked on Notepad and resource_check.txt today.")
        replies = self.adapter.get_replies()
        assert len(replies) > 0, "No reply received for temporal timeline query"

    def test_copilot_cleanup(self):
        # Gracefully terminates Notepad, Settings, Edge, and File Explorer
        self._simulate("Close all the programs we opened to keep my desktop clean.")
        replies = self.adapter.get_replies()
        assert len(replies) > 0, "No reply received for copilot cleanup task"

    def __init__(self):
        super().__init__()
        self.steps = [
            StepDef("session_init",              self.test_session_init,             timeout_s=25),
            StepDef("multi_app_research",         self.test_multi_app_research,         timeout_s=60),
            StepDef("telemetry_diagnose_save",   self.test_telemetry_diagnose_and_save,  timeout_s=60),
            StepDef("file_explorer_verify",      self.test_file_explorer_verification,  timeout_s=45),
            StepDef("settings_deep_navigation",  self.test_settings_deep_navigation,  timeout_s=50),
            StepDef("temporal_timeline_reason",  self.test_temporal_timeline_reasoning, timeout_s=35),
            StepDef("copilot_cleanup",           self.test_copilot_cleanup,           timeout_s=35),
        ]


if __name__ == "__main__":
    sys.exit(0 if Scenario15().run().passed else 1)
