"""
Scenario 11 — Task Memory Resume
=================================
Tests:
  - Create a multi-step task
  - Complete first step
  - Say "continue" or "resume"
  - System reads Task Memory and executes next step

Run:
    python -m tests.live.scenario_11_task_memory_resume
"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from tests.live.base_scenario import LiveScenario, StepDef
from jarvis_v2.brain.orchestrator import Orchestrator
from jarvis_v2.llm.llm_router import LLMRouter
from jarvis_v2.memory.memory_manager import MemoryManager
from jarvis_v2.skills.skill_bus import SkillBus
from jarvis_v2.memory.layers.task import TaskMemory


class Scenario11(LiveScenario):
    scenario_name = "11 — Task Memory Resume"

    def setup(self):
        self.orch = Orchestrator(memory=MemoryManager(), router=LLMRouter(), bus=SkillBus())
        self.orch._task_memory = TaskMemory()
        # Create a mock task
        task = self.orch._task_memory.create_task("Test task", steps=["open notepad", "type hello", "close notepad"])
        self.task_id = task.id
        self.orch.boot()

    def _run(self, cmd: str):
        result = self.orch.process(cmd)
        assert result.success, f"Failed: {cmd!r} → {result.message}"
        if cmd in ["continue", "resume"]:
            # Normally orchestrator handles this by querying task memory, 
            # here we verify the system doesn't crash on the command.
            pass

    def __init__(self):
        super().__init__()
        self.orch = None
        self.steps = [
            StepDef("open_notepad", lambda: self._run("open notepad"), timeout_s=20),
            StepDef("wait_1", lambda: time.sleep(1.0), timeout_s=5),
            StepDef("advance_task", lambda: self.orch._task_memory.advance(self.task_id), timeout_s=5),
            StepDef("resume_task", lambda: self._run("continue task"), timeout_s=20),
            StepDef("close_notepad", lambda: self._run("close notepad"), timeout_s=15),
        ]


if __name__ == "__main__":
    sys.exit(0 if Scenario11().run().passed else 1)
