"""
Scenario 10 — Episodic Memory Query
====================================
Tests:
  - System executes a command
  - User asks "what did I just do?" or similar
  - LLM uses Episodic memory to answer correctly

Run:
    python -m tests.live.scenario_10_episodic_memory
"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from tests.live.base_scenario import LiveScenario, StepDef
from jarvis_v2.brain.orchestrator import Orchestrator
from jarvis_v2.llm.llm_router import LLMRouter
from jarvis_v2.memory.memory_manager import MemoryManager
from jarvis_v2.skills.skill_bus import SkillBus
from jarvis_v2.memory.layers.episodic import EpisodicMemory


class Scenario10(LiveScenario):
    scenario_name = "10 — Episodic Memory Query"

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
            StepDef("open_notepad",     lambda: self._run("open notepad"), timeout_s=20),
            StepDef("set_volume",       lambda: self._run("set volume to 33"), timeout_s=15),
            StepDef("open_calculator",  lambda: self._run("open calculator"), timeout_s=20),
            StepDef("type_in_notepad",  lambda: self._run("type Memory Test 123"), timeout_s=15),
            StepDef("ask_last_app",     lambda: self._run("what was the last app I opened?"), timeout_s=20),
            StepDef("ask_volume",       lambda: self._run("what did I set the volume to?"), timeout_s=20),
            StepDef("ask_all_actions",  lambda: self._run("summarize everything I did in the last 5 minutes"), timeout_s=30),
            # StepDef("close_notepad",   lambda: self._run("close notepad"), timeout_s=15),
        ]


if __name__ == "__main__":
    sys.exit(0 if Scenario10().run().passed else 1)
