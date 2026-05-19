"""
Scenario 13 — Log Report Fixes Regression Test
====================================================
Tests:
  - Synonym mapping ("Open notebook" -> Notepad)
  - Strict verb mapping ("Close notepad")
  - Log analysis subsystem ("Analyze the logs")
  - Conversational routing ("Ok can open apps")
  - Quoted block protection

Run:
    python -m tests.live.scenario_13_log_report_fixes
"""
import sys
from pathlib import Path
import time
import argparse
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from tests.live.base_scenario import LiveScenario, StepDef
from jarvis.brain.orchestrator import Orchestrator
from jarvis.llm.llm_router import LLMRouter
from jarvis.memory.memory_manager import MemoryManager
from jarvis.skills.skill_bus import SkillBus


class Scenario13(LiveScenario):
    scenario_name = "13 — Log Report Fixes"

    def setup(self, learning_enabled: bool = False):
        mem = MemoryManager()
        router = LLMRouter.from_config()
        bus = SkillBus()
        self.orch = Orchestrator(memory=mem, router=router, bus=bus, learning_enabled=learning_enabled)
        self.orch.boot()

    def _run(self, cmd: str, expect_success: bool = True):
        results = self.orch.process(cmd)
        if not results:
            assert not expect_success, f"Command produced no results: {cmd!r}"
            return
            
        success = all(r.success for r in results)
        
        # Output the actions taken to manually verify the message formatter
        for r in results:
            print(f"   [Action]: {r.action_taken or r.message}")
            
        if expect_success:
            assert success, f"Command failed: {cmd!r}"
        else:
            assert not success, f"Command succeeded when expected to fail: {cmd!r}"

    def __init__(self):
        super().__init__()
        self.orch = None
        self.steps = [
            StepDef(
                name="open_notebook_synonym",
                fn=lambda: self._run("Open notebook"),
                timeout_s=15,
            ),
            StepDef(
                name="wait_for_notepad",
                fn=lambda: time.sleep(2),
                timeout_s=5,
            ),
            StepDef(
                name="type_text_into_notepad",
                fn=lambda: self._run("Type hello world into notepad"),
                timeout_s=15,
            ),
            StepDef(
                name="wait_for_type",
                fn=lambda: time.sleep(1),
                timeout_s=5,
            ),
            StepDef(
                name="close_notepad_strict_verb",
                fn=lambda: self._run("Close notepad"),
                timeout_s=10,
            ),
            StepDef(
                name="analyze_the_logs",
                fn=lambda: self._run("Analyze the logs"),
                timeout_s=20, # Can be slow if logs are large
            ),
            StepDef(
                name="conversational_understanding",
                fn=lambda: self._run("Ok can open apps"),
                timeout_s=15,
            ),
            StepDef(
                name="quoted_block_protection",
                fn=lambda: self._run("Summarize this: \"open notepad and then close settings\""),
                timeout_s=15,
            ),
        ]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scenario 13 — Log Report Fixes")
    parser.add_argument(
        "--learn-macros",
        action="store_true",
        default=False,
        help="Enable macro learning (default: OFF — prevents test pollution)",
    )
    args = parser.parse_args()

    scenario = Scenario13()
    scenario.setup(learning_enabled=args.learn_macros)
    result = scenario.run()
    sys.exit(0 if result.passed else 1)
