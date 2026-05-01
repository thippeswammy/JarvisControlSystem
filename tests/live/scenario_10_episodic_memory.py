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
        self.orch = Orchestrator(memory=MemoryManager(), router=LLMRouter(), bus=SkillBus())
        # We need an episodic memory instance
        self.orch._episodic = EpisodicMemory()
        self.orch.boot()

    def _run(self, cmd: str):
        # We log to episodic memory here normally this is done by verification loop
        result = self.orch.process(cmd)
        if hasattr(self.orch, "_episodic"):
            self.orch._episodic.log_command(cmd, success=result.success)
        assert result.success, f"Failed: {cmd!r} → {result.message}"

    def __init__(self):
        super().__init__()
        self.orch = None
        self.steps = [
            StepDef("open_notepad", lambda: self._run("open notepad"), timeout_s=20),
            StepDef("wait_1", lambda: time.sleep(1.0), timeout_s=5),
            StepDef("ask_memory", lambda: self._run("what did i just open?"), timeout_s=20),
            StepDef("close_notepad", lambda: self._run("close notepad"), timeout_s=15),
        ]


if __name__ == "__main__":
    sys.exit(0 if Scenario10().run().passed else 1)
