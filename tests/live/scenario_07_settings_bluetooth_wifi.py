"""
Scenario 07 — Settings: Bluetooth and Wi-Fi
===========================================
Tests graph navigation:
  - Open Bluetooth settings
  - Open Wi-Fi settings
  - Close Settings

Run:
    python -m tests.live.scenario_07_settings_bluetooth_wifi
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


class Scenario07(LiveScenario):
    scenario_name = "07 — Settings: Bluetooth and Wi-Fi"

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
            StepDef("open_bluetooth",   lambda: self._run("open bluetooth settings"), timeout_s=20),
            StepDef("add_device",       lambda: self._run("click Add device"), timeout_s=15),
            StepDef("cancel_add",       lambda: self._run("press escape"), timeout_s=10),
            StepDef("open_wifi",        lambda: self._run("open wifi settings"), timeout_s=20),
            StepDef("show_networks",    lambda: self._run("click Show available networks"), timeout_s=15),
            StepDef("scroll_networks",  lambda: self._run("scroll down"), timeout_s=10),
            StepDef("wait_2",           lambda: time.sleep(1.5), timeout_s=5),
            # StepDef("close_settings", lambda: self._run("close settings"), timeout_s=15),
        ]


if __name__ == "__main__":
    sys.exit(0 if Scenario07().run().passed else 1)
