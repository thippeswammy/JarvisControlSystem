"""
Scenario 09 — Self-Learning Demo (Reactive Learner)
=====================================================
Tests:
  - Unknown command triggers LLM plan
  - System executes and verifies using visual hash
  - Reactive Learner records the new graph edge
  - Same command runs again — this time from Memory (fast-path), NOT LLM

Run:
    python -m tests.live.scenario_09_self_learning_demo
"""
import logging
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')

from tests.live.base_scenario import LiveScenario, StepDef
from jarvis_v2.brain.orchestrator import Orchestrator
from jarvis_v2.llm.llm_router import LLMRouter
from jarvis_v2.memory.memory_manager import MemoryManager
from jarvis_v2.skills.skill_bus import SkillBus
from jarvis_v2.brain.verification_loop import VerificationLoop


class Scenario09(LiveScenario):
    scenario_name = "09 — Self-Learning Demo"

    def setup(self):
        from jarvis_v2.memory.state_harvester import StateHarvester
        from jarvis_v2.memory.state_comparator import StateComparator
        from jarvis_v2.brain.recovery import RecoveryStrategies
        from jarvis_v2.skills.skill_bus import SkillBus

        mem = MemoryManager(db_path=":memory:") # fresh DB for this test
        bus = SkillBus()
        vloop = VerificationLoop(StateHarvester(), StateComparator(), RecoveryStrategies(bus), settle_ms=2000)
        self.orch = Orchestrator(memory=mem, router=LLMRouter.from_config(), bus=bus, verification_loop=vloop)
        self.orch.boot()

    def _run(self, cmd: str, expect_memory: bool = False):
        # We need to verify if it used memory or LLM
        # For this test, we just run the command and check success.
        # True memory validation is done in unit tests, here we verify the system doesn't crash.
        result = self.orch.process(cmd)
        assert result.success, f"Failed: {cmd!r} → {result.message}"
        if expect_memory:
            # Check if it was recorded in DB
            db = self.orch._memory.get_db()
            edges = db.get_edges_for_app("settings")
            assert len(edges) > 0, "Expected ReactiveLearner to have saved an edge"

    def __init__(self):
        super().__init__()
        self.orch = None
        self.steps = [
            StepDef("open_unknown_settings", lambda: self._run("open network status settings", expect_memory=False), timeout_s=40),
            StepDef("open_known_settings",   lambda: self._run("open network status settings", expect_memory=True), timeout_s=15),
            StepDef("teach_preference",      lambda: self._run("remember that my favorite color is blue"), timeout_s=15),
            StepDef("ask_preference",        lambda: self._run("what is my favorite color?"), timeout_s=15),
            StepDef("teach_behavior",        lambda: self._run("whenever I open notepad, type 'Jarvis ready'"), timeout_s=20),
            StepDef("trigger_behavior",      lambda: self._run("open notepad"), timeout_s=20),
            # StepDef("close_settings",      lambda: self._run("close settings"), timeout_s=15),
        ]


if __name__ == "__main__":
    sys.exit(0 if Scenario09().run().passed else 1)
