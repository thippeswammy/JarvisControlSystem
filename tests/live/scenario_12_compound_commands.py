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
from jarvis.brain.orchestrator import Orchestrator
from jarvis.llm.llm_router import LLMRouter
from jarvis.memory.memory_manager import MemoryManager
from jarvis.skills.skill_bus import SkillBus


class Scenario12(LiveScenario):
    scenario_name = "12 — Compound Commands"

    def setup(self):
        self.orch = Orchestrator(memory=MemoryManager(), router=LLMRouter.from_config(), bus=SkillBus())
        self.orch.boot()

    def _run(self, cmd: str):
        result = self.orch.process(cmd)
        assert result.success, f"Failed: {cmd!r} → {result.message}"

    def __init__(self):
        super().__init__()
        self.orch = None
        self.steps = [
            StepDef("triple_command",    lambda: self._run("open notepad, type 'Compound depth 3', and set volume to 55"), timeout_s=40),
            StepDef("wait_1",           lambda: time.sleep(2.0), timeout_s=5),
            StepDef("quadruple_command", lambda: self._run("open calculator, minimize it, then open edge and navigate to bing.com"), timeout_s=50),
            StepDef("wait_2",           lambda: time.sleep(2.0), timeout_s=5),
            StepDef("penta_command",     lambda: self._run("open notepad, type 'Jarvis is evolving', press ctrl+a, press ctrl+c, and then mute volume"), timeout_s=60),
            StepDef("close_all",   lambda: self._run("close all"), timeout_s=15),
        ]


if __name__ == "__main__":
    sys.exit(0 if Scenario12().run().passed else 1)
