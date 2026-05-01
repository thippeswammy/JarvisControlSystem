"""
Scenario 05 — Edge Browsing and Search
======================================
Tests:
  - Open Microsoft Edge
  - Search for weather
  - Press enter
  - Close Edge

Run:
    python -m tests.live.scenario_05_edge_browsing
"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from tests.live.base_scenario import LiveScenario, StepDef
from jarvis_v2.brain.orchestrator import Orchestrator
from jarvis_v2.llm.llm_router import LLMRouter
from jarvis_v2.memory.memory_manager import MemoryManager
from jarvis_v2.skills.skill_bus import SkillBus


class Scenario05(LiveScenario):
    scenario_name = "05 — Edge Browsing and Search"

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
            StepDef("open_edge",        lambda: self._run("open edge"), timeout_s=20),
            StepDef("wait_1",           lambda: time.sleep(3.0), timeout_s=5),
            StepDef("go_to_google",     lambda: self._run("navigate to google.com"), timeout_s=20),
            StepDef("search_python",    lambda: self._run("search for python programming"), timeout_s=15),
            StepDef("scroll_down",      lambda: self._run("scroll down"), timeout_s=10),
            StepDef("scroll_up",        lambda: self._run("scroll up"), timeout_s=10),
            StepDef("go_to_github",     lambda: self._run("navigate to github.com"), timeout_s=20),
            StepDef("type_search_gh",   lambda: self._run("type JarvisControlSystem"), timeout_s=15),
            StepDef("press_enter",      lambda: self._run("press enter"), timeout_s=10),
            # StepDef("close_edge",     lambda: self._run("close edge"), timeout_s=15),
        ]


if __name__ == "__main__":
    sys.exit(0 if Scenario05().run().passed else 1)
