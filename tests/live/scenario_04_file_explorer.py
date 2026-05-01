"""
Scenario 04 — File Explorer Navigation
======================================
Tests:
  - Open File Explorer
  - Navigate to Documents
  - Scroll down
  - Go back
  - Close File Explorer

Run:
    python -m tests.live.scenario_04_file_explorer
"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from tests.live.base_scenario import LiveScenario, StepDef
from jarvis_v2.brain.orchestrator import Orchestrator
from jarvis_v2.llm.llm_router import LLMRouter
from jarvis_v2.memory.memory_manager import MemoryManager
from jarvis_v2.skills.skill_bus import SkillBus


class Scenario04(LiveScenario):
    scenario_name = "04 — File Explorer Navigation"

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
            StepDef("open_explorer", lambda: self._run("open file explorer"), timeout_s=20),
            StepDef("wait_1", lambda: time.sleep(1.0), timeout_s=5),
            StepDef("go_to_documents", lambda: self._run("click documents"), timeout_s=15),
            StepDef("scroll_down", lambda: self._run("scroll down"), timeout_s=10),
            StepDef("go_back", lambda: self._run("go back"), timeout_s=10),
            StepDef("close_explorer", lambda: self._run("close file explorer"), timeout_s=15),
        ]


if __name__ == "__main__":
    sys.exit(0 if Scenario04().run().passed else 1)
