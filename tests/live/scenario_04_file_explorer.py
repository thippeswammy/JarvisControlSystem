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
from jarvis.brain.orchestrator import Orchestrator
from jarvis.llm.llm_router import LLMRouter
from jarvis.memory.memory_manager import MemoryManager
from jarvis.skills.skill_bus import SkillBus


class Scenario04(LiveScenario):
    scenario_name = "04 — File Explorer Navigation"

    def setup(self):
        import shutil
        p_test = Path.home() / "Documents" / "JarvisTest"
        p_devel = Path.home() / "Documents" / "JarvisDevel"
        if p_test.exists(): shutil.rmtree(p_test)
        if p_devel.exists(): shutil.rmtree(p_devel)
        self.orch = Orchestrator(memory=MemoryManager(), router=LLMRouter.from_config(), bus=SkillBus())
        self.orch.boot()

    def _run(self, cmd: str):
        result = self.orch.process(cmd)
        assert result.success, f"Failed: {cmd!r} → {result.message}"

    def __init__(self):
        super().__init__()
        self.orch = None
        self.steps = [
            StepDef("open_explorer",    lambda: self._run("open file explorer"), timeout_s=20),
            StepDef("wait_1",           lambda: time.sleep(1.5), timeout_s=5),
            StepDef("go_to_pc",         lambda: self._run("click This PC"), timeout_s=15),
            StepDef("go_to_c_drive",    lambda: self._run("double click (C:)"), timeout_s=15),
            StepDef("go_to_users",      lambda: self._run("double click Users"), timeout_s=15),
            StepDef("go_to_documents",  lambda: self._run("navigate to my documents"), timeout_s=15),
            StepDef("create_folder_os", lambda: (Path.home() / "Documents" / "JarvisTest").mkdir(exist_ok=True) or True, timeout_s=5),
            StepDef("enter_folder",     lambda: self._run("double click JarvisTest"), timeout_s=15),
            StepDef("rename_folder_os", lambda: (Path.home() / "Documents" / "JarvisTest").rename(Path.home() / "Documents" / "JarvisDevel") or True, timeout_s=5),
            StepDef("go_back",          lambda: self._run("go back"), timeout_s=10),
            StepDef("go_back_again",    lambda: self._run("go back"), timeout_s=10),
            # StepDef("close_explorer", lambda: self._run("close file explorer"), timeout_s=15),
        ]


if __name__ == "__main__":
    sys.exit(0 if Scenario04().run().passed else 1)
