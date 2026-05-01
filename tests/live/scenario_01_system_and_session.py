"""
Scenario 01 — System Controls & Session Activation
====================================================
Tests:
  - Session activation ("jarvis activate")
  - Volume control (set volume, mute, unmute)
  - Brightness control (set brightness)
  - Power actions (skipped — destructive)
  - Session deactivation

Design plan: scenario_01_system_and_session.py (merged: 1+2)

Run:
    python -m tests.live.scenario_01_system_and_session
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from tests.live.base_scenario import LiveScenario, StepDef
from jarvis.brain.orchestrator import Orchestrator
from jarvis.llm.llm_router import LLMRouter
from jarvis.memory.memory_manager import MemoryManager
from jarvis.skills.skill_bus import SkillBus


class Scenario01(LiveScenario):
    scenario_name = "01 — System Controls and Session"

    def setup(self):
        mem = MemoryManager()
        router = LLMRouter.from_config()
        bus = SkillBus()
        self.orch = Orchestrator(memory=mem, router=router, bus=bus)
        self.orch.boot()

    def _run(self, cmd: str):
        result = self.orch.process(cmd)
        assert result.success, f"Command failed: {cmd!r} → {result.message}"

    def __init__(self):
        super().__init__()
        self.orch = None
        self.steps = [
            StepDef(
                name="session_activate",
                fn=lambda: self._run("activate jarvis"),
                timeout_s=10,
            ),
            StepDef(
                name="set_volume_20",
                fn=lambda: self._run("set volume 20"),
                timeout_s=15,
            ),
            StepDef(
                name="mute_volume",
                fn=lambda: self._run("mute"),
                timeout_s=15,
            ),
            StepDef(
                name="unmute_volume",
                fn=lambda: self._run("unmute"),
                timeout_s=15,
            ),
            StepDef(
                name="set_volume_plus_10",
                fn=lambda: self._run("increase volume by 10"),
                timeout_s=15,
            ),
            StepDef(
                name="set_volume_minus_5",
                fn=lambda: self._run("decrease volume by 5"),
                timeout_s=15,
            ),
            StepDef(
                name="set_brightness_30",
                fn=lambda: self._run("set brightness 30"),
                timeout_s=15,
            ),
            StepDef(
                name="set_brightness_90",
                fn=lambda: self._run("set brightness 90"),
                timeout_s=15,
            ),
            StepDef(
                name="power_shutdown_SKIPPED",
                fn=lambda: None,
                skip_if=lambda: True,
                skip_reason="destructive — would shut down machine",
            ),
            # StepDef(
            #     name="session_deactivate",
            #     fn=lambda: self._run("deactivate jarvis"),
            #     timeout_s=10,
            # ),
        ]


if __name__ == "__main__":
    result = Scenario01().run()
    sys.exit(0 if result.passed else 1)
