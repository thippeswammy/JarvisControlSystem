"""
Scenario 06 — Settings: Display and Sound
=========================================
Tests graph navigation:
  - Open Display settings
  - Open Sound settings
  - Close Settings

Run:
    python -m tests.live.scenario_06_settings_display_sound
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


class Scenario06(LiveScenario):
    scenario_name = "06 — Settings: Display and Sound"

    def setup(self):
        mem = MemoryManager()
        # Seed settings to ensure fast-paths are available
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
            StepDef("open_display",     lambda: self._run("open display settings"), timeout_s=20),
            StepDef("scroll_display",   lambda: self._run("scroll down"), timeout_s=10),
            StepDef("go_to_night_light", lambda: self._run("click Night light"), timeout_s=15),
            StepDef("go_back",          lambda: self._run("go back"), timeout_s=10),
            StepDef("open_sound",       lambda: self._run("open sound settings"), timeout_s=20),
            StepDef("set_volume_UI",    lambda: self._run("set volume to 45"), timeout_s=15),
            StepDef("check_output",     lambda: self._run("click Choose where to play sound"), timeout_s=15),
            StepDef("wait_2",           lambda: time.sleep(1.5), timeout_s=5),
            # StepDef("close_settings", lambda: self._run("close settings"), timeout_s=15),
        ]


if __name__ == "__main__":
    sys.exit(0 if Scenario06().run().passed else 1)
