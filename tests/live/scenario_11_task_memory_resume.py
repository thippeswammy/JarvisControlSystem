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
from jarvis.brain.orchestrator import Orchestrator
from jarvis.llm.llm_router import LLMRouter
from jarvis.memory.memory_manager import MemoryManager
from jarvis.skills.skill_bus import SkillBus
from jarvis.memory.layers.task import TaskMemory


class Scenario11(LiveScenario):
    scenario_name = "11 — Task Memory Resume"

    def setup(self):
        self.orch = Orchestrator(memory=MemoryManager(), router=LLMRouter.from_config(), bus=SkillBus())
        self.orch._task_memory = TaskMemory()
        # Create a mock task
        # Create a much longer task
        steps = [
            "open notepad", 
            "type Step 1 done", 
            "set volume to 20",
            "open calculator", 
            "minimize window", 
            "maximize window",
            "type Step 7 is here",
            "open file explorer",
            "snap window left",
            "unmute"
        ]
        task = self.orch._task_memory.create_task("Complex Multi-Step Task", steps=steps)
        self.task_id = task.id
        self.orch.boot()

    def _run(self, cmd: str):
        result = self.orch.process(cmd)
        assert result.success, f"Failed: {cmd!r} → {result.message}"

    def __init__(self):
        super().__init__()
        self.orch = None
        self.steps = [
            StepDef("start_task",    lambda: self._run("start task"), timeout_s=30),
            StepDef("wait_mid",      lambda: time.sleep(1.0), timeout_s=5),
            StepDef("resume_1",      lambda: self._run("continue task"), timeout_s=25),
            StepDef("resume_2",      lambda: self._run("resume my task"), timeout_s=25),
            StepDef("resume_3",      lambda: self._run("next step please"), timeout_s=25),
            StepDef("resume_4",      lambda: self._run("continue"), timeout_s=25),
            # StepDef("close_notepad", lambda: self._run("close notepad"), timeout_s=15),
        ]


if __name__ == "__main__":
    sys.exit(0 if Scenario11().run().passed else 1)
