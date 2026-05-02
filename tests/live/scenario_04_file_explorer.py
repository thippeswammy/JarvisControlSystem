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
import winreg
import shutil

def _get_docs_path() -> Path:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders") as key:
            return Path(winreg.QueryValueEx(key, "Personal")[0])
    except Exception:
        return Path.home() / "Documents"

def _create_test_folder():
    (_get_docs_path() / "JarvisTest").mkdir(exist_ok=True)
    return True

def _rename_test_folder():
    src = _get_docs_path() / "JarvisTest"
    dst = _get_docs_path() / "JarvisDevel"
    if src.exists():
        src.rename(dst)
    return True


class Scenario04(LiveScenario):
    scenario_name = "04 — File Explorer Navigation"

    def setup(self):
        p_test = _get_docs_path() / "JarvisTest"
        p_devel = _get_docs_path() / "JarvisDevel"
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
            StepDef("go_to_documents",  lambda: self._run("click Documents"), timeout_s=15),
            StepDef("create_folder_os", lambda: _create_test_folder(), timeout_s=5),
            StepDef("enter_folder",     lambda: self._run("double click JarvisTest"), timeout_s=15),
            StepDef("rename_folder_os", lambda: _rename_test_folder(), timeout_s=5),
            StepDef("go_back",          lambda: self._run("go back"), timeout_s=10),
            StepDef("go_back_again",    lambda: self._run("go back"), timeout_s=10),
            # StepDef("close_explorer", lambda: self._run("close file explorer"), timeout_s=15),
        ]


if __name__ == "__main__":
    sys.exit(0 if Scenario04().run().passed else 1)
