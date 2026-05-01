"""
Scenario 03 — Multi-App Window Management
==========================================
Tests:
  - Open two apps (Notepad + Calculator)
  - Window snap left / right
  - Switch between apps (Alt+Tab)
  - Minimize / maximize
  - Close both apps

Design plan: scenario_03_multi_app_window_mgmt.py (was 4)

Run:
    python -m tests.live.scenario_03_multi_app_window_mgmt
"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from tests.live.base_scenario import LiveScenario, StepDef
from jarvis_v2.brain.orchestrator import Orchestrator
from jarvis_v2.llm.llm_router import LLMRouter
from jarvis_v2.memory.memory_manager import MemoryManager
from jarvis_v2.skills.skill_bus import SkillBus


class Scenario03(LiveScenario):
    scenario_name = "03 — Multi-App Window Management"

    def setup(self):
        mem = MemoryManager()
        self.orch = Orchestrator(memory=mem, router=LLMRouter(), bus=SkillBus())
        self.orch.boot()

    def _run(self, cmd: str):
        result = self.orch.process(cmd)
        assert result.success, f"Failed: {cmd!r} → {result.message}"

    def __init__(self):
        super().__init__()
        self.orch = None
        self.steps = [
            StepDef("open_notepad",      lambda: self._run("open notepad"),     timeout_s=20),
            StepDef("wait_1",            lambda: time.sleep(1.0),               timeout_s=5),
            StepDef("open_calculator",   lambda: self._run("open calculator"),  timeout_s=20),
            StepDef("wait_2",            lambda: time.sleep(1.0),               timeout_s=5),
            StepDef("snap_left",         lambda: self._run("snap left"),        timeout_s=10),
            StepDef("alt_tab",           lambda: self._run("switch window"),    timeout_s=5),
            StepDef("snap_right",        lambda: self._run("snap right"),       timeout_s=10),
            StepDef("minimize_all",      lambda: self._run("minimize window"),  timeout_s=10),
            StepDef("maximize_notepad",  lambda: self._run("maximize window"),  timeout_s=10),
            StepDef("close_calculator",  lambda: self._run("close calculator"), timeout_s=15),
            StepDef("close_notepad",     lambda: self._run("close notepad"),    timeout_s=15),
        ]


if __name__ == "__main__":
    result = Scenario03().run()
    sys.exit(0 if result.passed else 1)
