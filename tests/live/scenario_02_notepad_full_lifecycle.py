"""
Scenario 02 — Notepad Full Lifecycle
======================================
Tests:
  - Open Notepad
  - Type text
  - Press keyboard shortcuts (Ctrl+A, Ctrl+C)
  - Save (Ctrl+S) — skip if dialog appears
  - Close Notepad

Design plan: scenario_02_notepad_full_lifecycle.py (merged: 3+7+9)

Run:
    python -m tests.live.scenario_02_notepad_full_lifecycle
"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from tests.live.base_scenario import LiveScenario, StepDef
from jarvis_v2.brain.orchestrator import Orchestrator
from jarvis_v2.llm.llm_router import LLMRouter
from jarvis_v2.memory.memory_manager import MemoryManager
from jarvis_v2.skills.skill_bus import SkillBus


class Scenario02(LiveScenario):
    scenario_name = "02 — Notepad Full Lifecycle"

    def setup(self):
        mem = MemoryManager()
        router = LLMRouter.from_config()
        bus = SkillBus()
        self.orch = Orchestrator(memory=mem, router=router, bus=bus)
        self.orch.boot()

    def _run(self, cmd: str):
        result = self.orch.process(cmd)
        assert result.success, f"Command failed: {cmd!r} → {result.message}"

    def __init__(self):
        super().__init__()
        self.orch = None
        self.steps = [
            StepDef("open_notepad",       lambda: self._run("open notepad"), timeout_s=20),
            StepDef("wait_for_notepad",   lambda: time.sleep(1.5),          timeout_s=5),
            StepDef("type_hello_world",   lambda: self._run("type Hello, Jarvis v2 is live!"), timeout_s=10),
            StepDef("select_all",         lambda: self._run("press ctrl+a"), timeout_s=5),
            StepDef("copy",               lambda: self._run("press ctrl+c"), timeout_s=5),
            StepDef("move_to_end",        lambda: self._run("press ctrl+end"), timeout_s=5),
            StepDef("type_second_line",   lambda: self._run("type\\nSecond line here."), timeout_s=10),
            StepDef("save_ctrl_s",        lambda: self._run("press ctrl+s"), timeout_s=10),
            StepDef("close_notepad",      lambda: self._run("close notepad"), timeout_s=15),
        ]


if __name__ == "__main__":
    result = Scenario02().run()
    sys.exit(0 if result.passed else 1)
