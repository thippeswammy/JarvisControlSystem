"""
Scenario 08 — Settings: Personalization
=========================================
Tests graph navigation:
  - Open Personalization settings
  - Open Background settings
  - Close Settings

Run:
    python -m tests.live.scenario_08_settings_personalization
"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from tests.live.base_scenario import LiveScenario, StepDef
from jarvis_v2.brain.orchestrator import Orchestrator
from jarvis_v2.llm.llm_router import LLMRouter
from jarvis_v2.memory.memory_manager import MemoryManager
from jarvis_v2.skills.skill_bus import SkillBus
from jarvis_v2.memory.layers.procedural import ProceduralMemory


class Scenario08(LiveScenario):
    scenario_name = "08 — Settings: Personalization"

    def setup(self):
        mem = MemoryManager()
        ProceduralMemory(mem.get_db()).seed_settings_graph()
        self.orch = Orchestrator(memory=mem, router=LLMRouter.from_config(), bus=SkillBus())
        self.orch.boot()

    def _run(self, cmd: str):
        result = self.orch.process(cmd)
        assert result.success, f"Failed: {cmd!r} → {result.message}"

    def __init__(self):
        super().__init__()
        self.orch = None
        self.steps = [
            StepDef("open_personalization", lambda: self._run("open personalization settings"), timeout_s=20),
            StepDef("go_to_colors",         lambda: self._run("click Colors"), timeout_s=15),
            StepDef("toggle_mode",          lambda: self._run("change system mode to dark"), timeout_s=20),
            StepDef("wait_1",               lambda: time.sleep(2.0), timeout_s=5),
            StepDef("toggle_mode_light",    lambda: self._run("change system mode to light"), timeout_s=20),
            StepDef("go_to_themes",         lambda: self._run("click Themes"), timeout_s=15),
            StepDef("scroll_themes",        lambda: self._run("scroll down"), timeout_s=10),
            StepDef("wait_2",               lambda: time.sleep(1.5), timeout_s=5),
            # StepDef("close_settings",     lambda: self._run("close settings"), timeout_s=15),
        ]


if __name__ == "__main__":
    sys.exit(0 if Scenario08().run().passed else 1)
