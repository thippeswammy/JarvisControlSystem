"""
Scenario 12 — Compound Commands
================================
Tests:
  - Issue compound command: "open notepad and type hello world"
  - Planner should split into two SkillCalls
  - Verify execution

Run:
    python -m tests.live.scenario_12_compound_commands
"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from tests.live.base_scenario import LiveScenario, StepDef
from jarvis_v2.brain.orchestrator import Orchestrator
from jarvis_v2.llm.llm_router import LLMRouter
from jarvis_v2.memory.memory_manager import MemoryManager
from jarvis_v2.skills.skill_bus import SkillBus


class Scenario12(LiveScenario):
    scenario_name = "12 — Compound Commands"

    def setup(self):
        self.orch = Orchestrator(memory=MemoryManager(), router=LLMRouter(), bus=SkillBus())
        self.orch.boot()

    def _run(self, cmd: str):
        result = self.orch.process(cmd)
        assert result.success, f"Failed: {cmd!r} → {result.message}"

    def __init__(self):
        super().__init__()
        self.orch = None
        self.steps = [
            StepDef("compound_command", lambda: self._run("open notepad and type compound test"), timeout_s=30),
            StepDef("wait_1", lambda: time.sleep(1.5), timeout_s=5),
            StepDef("close_notepad", lambda: self._run("close notepad"), timeout_s=15),
        ]


if __name__ == "__main__":
    sys.exit(0 if Scenario12().run().passed else 1)
