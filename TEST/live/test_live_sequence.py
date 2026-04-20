"""
Live Sequence Test Runner
=========================
Runs real command sequences against the actual Jarvis engine.
These tests ACTUALLY INTERACT WITH WINDOWS.

Each scenario is a list of (command, wait_seconds, description) steps.
The runner executes them in order, tracks pass/fail, and prints a report.

Usage:
  python TEST/live/test_live_sequence.py                  # run all scenarios
  python TEST/live/test_live_sequence.py --scenario 1     # run only scenario 1
  python TEST/live/test_live_sequence.py --list           # list all scenarios
  python TEST/live/test_live_sequence.py --dry-run        # parse only, no execution
"""

import sys
import os
import time
import argparse
import logging
from dataclasses import dataclass, field
from typing import Optional

# ── Setup path ──────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pyautogui
from PIL import ImageChops
try:
    from TEST.live.eval_report_generator import VisualReportGenerator
except ImportError:
    VisualReportGenerator = None

# ── Minimal logging during live tests ───────
logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s: %(message)s"
)

from Jarvis.core.jarvis_engine import JarvisEngine
from Jarvis.core.intent_engine import IntentEngine

# ─────────────────────────────────────────────
#  Step & Scenario Structures
# ─────────────────────────────────────────────

@dataclass
class Step:
    command: str
    wait: float = 1.5          # seconds to wait AFTER sending command
    description: str = ""      # human label for the report
    expect_success: bool = True
    expect_visual_change: bool = False


@dataclass
class Scenario:
    id: int
    name: str
    description: str
    steps: list[Step]
    cleanup: list[str] = field(default_factory=list)   # commands to run after, win or lose


@dataclass
class StepResult:
    step: Step
    success: bool
    message: str
    duration: float
    img_before: Optional[object] = None
    img_after: Optional[object] = None


@dataclass
class ScenarioResult:
    scenario: Scenario
    step_results: list[StepResult] = field(default_factory=list)
    total_time: float = 0.0

    @property
    def passed(self) -> bool:
        return all(
            r.success == r.step.expect_success
            for r in self.step_results
        )

    @property
    def pass_count(self) -> int:
        return sum(1 for r in self.step_results if r.success == r.step.expect_success)

    @property
    def fail_count(self) -> int:
        return len(self.step_results) - self.pass_count


# ─────────────────────────────────────────────
#  SCENARIOS
#  Each scenario tests a specific real-world interaction flow.
# ─────────────────────────────────────────────

SCENARIOS: list[Scenario] = [

    # ──────────────────────────────────────────
    Scenario(
        id=1,
        name="Session Activation & Shutdown",
        description="Tests basic Jarvis on/off cycle",
        steps=[
            Step("hi jarvis",        wait=0.5, description="Activate Jarvis"),
            Step("hi jarvis",        wait=0.5, description="Activate again (already active)"),
            Step("close jarvis",     wait=0.5, description="Deactivate Jarvis"),
            Step("open notepad",     wait=0.5, description="Rejected — not active", expect_success=False),
            Step("hi jarvis",        wait=0.5, description="Re-activate"),
            Step("close jarvis",     wait=0.5, description="Final deactivate"),
        ],
    ),

    # ──────────────────────────────────────────
    Scenario(
        id=2,
        name="System Controls Chain",
        description="Volume and brightness: set, increase, decrease",
        steps=[
            Step("hi jarvis",                    wait=0.3, description="Activate"),
            Step("set volume to 50",             wait=0.5, description="Set volume 50%"),
            Step("increase volume by 20",        wait=0.5, description="Volume → 70%"),
            Step("decrease volume 10",           wait=0.5, description="Volume → 60%"),
            Step("set brightness to 80",         wait=0.5, description="Brightness 80%"),
            Step("decrease brightness by 30",    wait=0.5, description="Brightness → 50%"),
            Step("increase brightness 10",       wait=0.5, description="Brightness → 60%"),
            Step("close jarvis",                 wait=0.3, description="Deactivate"),
        ],
    ),

    # ──────────────────────────────────────────
    Scenario(
        id=3,
        name="Open App → In-App Navigation → Close",
        description="Open Notepad, navigate menus, close. Full app lifecycle.",
        steps=[
            Step("hi jarvis",                    wait=0.5,  description="Activate"),
            Step("open notepad",                 wait=2.5,  description="Open Notepad"),
            Step("maximize window",              wait=0.8,  description="Maximize Notepad"),
            Step("click file",                   wait=1.0,  description="Click File menu"),
            Step("press escape",                 wait=0.5,  description="Close menu with ESC"),
            Step("start typing",                 wait=0.3,  description="Start typing mode"),
            Step("Hello from Jarvis! Testing in-app typing.", wait=0.5, description="Type text"),
            Step("stop typing",                  wait=0.3,  description="Stop typing mode"),
            Step("press ctrl s",                 wait=1.5,  description="Save (Ctrl+S) → dialog"),
            Step("press escape",                 wait=0.5,  description="Cancel save dialog"),
            Step("close window",                 wait=1.0,  description="Close Notepad window"),
            Step("press tab",                    wait=0.5,  description="Tab in save dialog (Don't Save)"),
            Step("press enter",                  wait=0.5,  description="Confirm Don't Save"),
            Step("close jarvis",                 wait=0.3,  description="Deactivate"),
        ],
        cleanup=["close notepad"],
    ),

    # ──────────────────────────────────────────
    Scenario(
        id=4,
        name="App Chaining — Open Multiple, Switch Between",
        description="Open multiple apps and switch window focus between them",
        steps=[
            Step("hi jarvis",                    wait=0.5,  description="Activate"),
            Step("open notepad",                 wait=2.5,  description="Open Notepad"),
            Step("open calculator",              wait=2.5,  description="Open Calculator"),
            Step("switch window",                wait=1.0,  description="Switch to Notepad"),
            Step("switch window",                wait=1.0,  description="Switch to Calculator"),
            Step("switch window",                wait=1.0,  description="Switch back"),
            Step("minimize window",              wait=0.8,  description="Minimize active"),
            Step("maximize window",              wait=0.8,  description="Maximize"),
            Step("snap left",                    wait=0.8,  description="Snap left"),
            Step("snap right",                   wait=0.8,  description="Snap right"),
            Step("close window",                 wait=0.8,  description="Close first app"),
            Step("close window",                 wait=0.8,  description="Close second app"),
            Step("close jarvis",                 wait=0.3,  description="Deactivate"),
        ],
        cleanup=["close notepad", "close calculator"],
    ),

    # ──────────────────────────────────────────
    Scenario(
        id=5,
        name="File Explorer Navigation Chain",
        description="Open Explorer and navigate to different locations",
        steps=[
            Step("hi jarvis",                    wait=0.5,  description="Activate"),
            Step("open explorer",                wait=2.5,  description="Open File Explorer"),
            Step("go to documents",              wait=1.5,  description="Navigate to Documents"),
            Step("go to downloads",              wait=1.5,  description="Navigate to Downloads"),
            Step("go to desktop",                wait=1.5,  description="Navigate to Desktop"),
            Step("navigate to c drive",          wait=1.5,  description="Navigate to C:\\"),
            Step("go to this pc",                wait=1.5,  description="Open This PC"),
            Step("close window",                 wait=0.8,  description="Close Explorer"),
            Step("close jarvis",                 wait=0.3,  description="Deactivate"),
        ],
        cleanup=["close explorer"],
    ),

    # ──────────────────────────────────────────
    Scenario(
        id=6,
        name="Windows Settings Navigation Chain",
        description="Open Settings and navigate through different pages",
        steps=[
            Step("hi jarvis",                    wait=0.5,  description="Activate"),
            Step("open settings",                wait=2.0,  description="Open Settings home"),
            Step("open settings display",        wait=1.5,  description="Go to Display settings"),
            Step("open settings sound",          wait=1.5,  description="Go to Sound settings"),
            Step("open settings bluetooth",      wait=1.5,  description="Go to Bluetooth"),
            Step("open settings wifi",           wait=1.5,  description="Go to WiFi/Network"),
            Step("open settings windows update", wait=1.5,  description="Go to Windows Update"),
            Step("close settings",               wait=1.0,  description="Close Settings"),
            Step("close jarvis",                 wait=0.3,  description="Deactivate"),
        ],
        cleanup=["close settings"],
    ),

    # ──────────────────────────────────────────
    Scenario(
        id=7,
        name="Keyboard Automation Chain",
        description="Press, hold, release, and type sequences",
        steps=[
            Step("hi jarvis",                    wait=0.5,  description="Activate"),
            Step("open notepad",                 wait=2.5,  description="Open Notepad"),
            Step("press ctrl a",                 wait=0.5,  description="Select All"),
            Step("press delete",                 wait=0.3,  description="Clear"),
            Step("start typing",                 wait=0.3,  description="Start typing mode"),
            Step("Line 1: Jarvis keyboard test", wait=0.5,  description="Type line 1"),
            Step("stop typing",                  wait=0.3,  description="Stop typing mode"),
            Step("press enter",                  wait=0.3,  description="New line"),
            Step("start typing",                 wait=0.3,  description="Start typing again"),
            Step("Line 2: More text here",       wait=0.5,  description="Type line 2"),
            Step("stop typing",                  wait=0.3,  description="Stop typing"),
            Step("press ctrl a",                 wait=0.3,  description="Select all text"),
            Step("press ctrl c",                 wait=0.3,  description="Copy"),
            Step("press end",                    wait=0.3,  description="Go to end"),
            Step("press ctrl v",                 wait=0.5,  description="Paste (duplicate)"),
            Step("close window",                 wait=0.8,  description="Close Notepad"),
            Step("press tab",                    wait=0.3,  description="Tab to 'Don't Save'"),
            Step("press enter",                  wait=0.5,  description="Don't save"),
            Step("close jarvis",                 wait=0.3,  description="Deactivate"),
        ],
        cleanup=["close notepad"],
    ),

    # ──────────────────────────────────────────
    Scenario(
        id=8,
        name="Full End-to-End Task — Write, Save, Close",
        description=(
            "Complete user task: create a file in Notepad, type content, "
            "save to a specific name, then clean up."
        ),
        steps=[
            Step("hi jarvis",                    wait=0.5,  description="Activate Jarvis"),
            Step("open notepad",                 wait=2.5,  description="Open Notepad"),
            Step("maximize window",              wait=0.8,  description="Maximize"),
            Step("start typing",                 wait=0.3,  description="Start typing mode"),
            Step("Jarvis Control System Test\nCreated by Jarvis AI\nDate: 2026\n",
                                                 wait=1.0,  description="Type document content"),
            Step("stop typing",                  wait=0.3,  description="Stop typing mode"),
            Step("press ctrl s",                 wait=1.5,  description="Save As dialog opens"),
            Step("start typing",                 wait=0.3,  description="Type filename mode"),
            Step("jarvis_test_output.txt",       wait=0.5,  description="Type filename"),
            Step("stop typing",                  wait=0.3,  description="Stop typing mode"),
            Step("press enter",                  wait=1.0,  description="Confirm save"),
            Step("close window",                 wait=0.8,  description="Close Notepad"),
            Step("close jarvis",                 wait=0.3,  description="Deactivate Jarvis"),
        ],
        cleanup=["close notepad"],
    ),

    # ──────────────────────────────────────────
    Scenario(
        id=9,
        name="Click UI Elements in Any App",
        description="Open Notepad and click UI elements using AppNavigator",
        steps=[
            Step("hi jarvis",                    wait=0.5,  description="Activate"),
            Step("open notepad",                 wait=2.5,  description="Open Notepad"),
            Step("click file",                   wait=1.0,  description="Click File menu"),
            Step("click new",                    wait=1.0,  description="Click New"),
            Step("click file",                   wait=1.0,  description="Click File again"),
            Step("click new",                    wait=1.0,  description="Toggle back"),
            Step("click view",                   wait=1.0,  description="Click View menu"),
            Step("press escape",                 wait=0.5,  description="Escape menu"),
            Step("scroll down",                  wait=0.5,  description="Scroll down"),
            Step("scroll up",                    wait=0.5,  description="Scroll up"),
            Step("close window",                 wait=0.8,  description="Close Notepad"),
            Step("press enter",                  wait=0.5,  description="Don't save confirm"),
            Step("close jarvis",                 wait=0.3,  description="Deactivate"),
        ],
        cleanup=["close notepad"],
    ),

    # ──────────────────────────────────────────
    Scenario(
        id=10,
        name="Full Stress Test — All Categories",
        description="Rapid-fire test covering every command category in one run",
        steps=[
            # Session
            Step("hi jarvis",                    wait=0.5,  description="[Session] Activate"),
            # System
            Step("set volume to 60",             wait=0.5,  description="[System] Volume 60"),
            Step("increase volume 10",           wait=0.5,  description="[System] Volume +10"),
            # Window mgmt
            Step("open notepad",                 wait=2.0,  description="[App] Open Notepad"),
            Step("maximize window",              wait=0.5,  description="[Window] Maximize"),
            Step("snap left",                    wait=0.5,  description="[Window] Snap left"),
            Step("snap right",                   wait=0.5,  description="[Window] Snap right"),
            # Keyboard
            Step("press ctrl a",                 wait=0.3,  description="[Key] Select all"),
            # Typing
            Step("start typing",                 wait=0.3,  description="[Typing] Start"),
            Step("Stress test passed!",          wait=0.5,  description="[Typing] Type"),
            Step("stop typing",                  wait=0.3,  description="[Typing] Stop"),
            # Navigation
            Step("open explorer",                wait=2.0,  description="[Explorer] Open"),
            Step("go to documents",              wait=1.2,  description="[Explorer] Documents"),
            Step("close window",                 wait=0.5,  description="[Explorer] Close"),
            # Settings
            Step("open settings display",        wait=1.5,  description="[Settings] Display"),
            Step("close settings",               wait=0.8,  description="[Settings] Close"),
            # Search
            Step("search for python",            wait=1.5,  description="[Search] Python"),
            Step("press escape",                 wait=0.5,  description="[Search] Close"),
            # Cleanup
            Step("close window",                 wait=0.5,  description="Close Notepad"),
            Step("press tab",                    wait=0.3,  description="Don't save tab"),
            Step("press enter",                  wait=0.5,  description="Don't save confirm"),
            Step("close jarvis",                 wait=0.3,  description="[Session] Deactivate"),
        ],
        cleanup=["close notepad", "close explorer", "close settings"],
    ),

    # ──────────────────────────────────────────
    Scenario(
        id=11,
        name="Special Settings UI Navigation Test",
        description="Open settings -> system -> display -> click advanced display -> snap left -> minimize all",
        steps=[
            Step("hi jarvis",                    wait=0.5,  description="Activate"),
            Step("open settings system",         wait=2.0,  description="Open Settings System page"),
            Step("open settings display",        wait=1.5,  description="Go to Display"),
            Step("scroll down",                  wait=1.0,  description="Scroll down to reveal options"),
            Step("click advanced display",       wait=1.5,  description="Click Advanced Display via pywinauto"),
            Step("snap left",                    wait=1.0,  description="Snap window to the left"),
            Step("press win m",                  wait=0.8,  description="Minimize all windows (Win+M)"),
            Step("close jarvis",                 wait=0.3,  description="Deactivate"),
        ],
        cleanup=["close settings"],
    ),

    # ──────────────────────────────────────────
    Scenario(
        id=12,
        name="Special File Explorer UI Navigation Test",
        description="Open file explorer -> maximize -> go to documents -> scroll -> open Arduino -> minimize all",
        steps=[
            Step("hi jarvis",                    wait=0.5,  description="Activate"),
            Step("open file explorer",           wait=2.5,  description="Open File Explorer", expect_visual_change=True),
            Step("maximize window",              wait=1.0,  description="Maximize window", expect_visual_change=True),
            Step("go to documents",              wait=1.5,  description="Navigate to Documents", expect_visual_change=True),
            Step("scroll down",                  wait=1.0,  description="Scroll down to reveal files", expect_visual_change=True),
            Step("open folder Arduino",           wait=1.5,  description="Open Arduino folder (intentional typo to trigger LLM fallback)", expect_visual_change=True),
            Step("press win m",                  wait=0.8,  description="Minimize all windows (Win+M)", expect_visual_change=True),
            Step("close jarvis",                 wait=0.3,  description="Deactivate"),
        ],
        cleanup=["close explorer"],
    ),

    # ──────────────────────────────────────────
    Scenario(
        id=13,
        name="Extensive Settings Coverage Test",
        description="Open various Windows Settings pages sequentially to demonstrate capabilities",
        steps=[
            Step("hi jarvis",                    wait=0.5,  description="Activate"),
            Step("open settings",                wait=2.0,  description="Open Settings home"),
            Step("open settings system",         wait=1.0,  description="Go to System"),
            Step("open settings bluetooth",      wait=1.0,  description="Go to Bluetooth"),
            Step("open settings network",        wait=1.0,  description="Go to Network"),
            Step("open settings personalization",wait=1.0,  description="Go to Personalization"),
            Step("open settings apps",           wait=1.0,  description="Go to Apps"),
            Step("open settings accounts",       wait=1.0,  description="Go to Accounts"),
            Step("open settings time",           wait=1.0,  description="Go to Time & Language"),
            Step("open settings gaming",         wait=1.0,  description="Go to Gaming"),
            Step("open settings accessibility",  wait=1.0,  description="Go to Accessibility"),
            Step("open settings privacy",        wait=1.0,  description="Go to Privacy"),
            Step("open settings update",         wait=1.0,  description="Go to Windows Update"),
            Step("close settings",               wait=1.0,  description="Close Settings"),
            Step("close jarvis",                 wait=0.3,  description="Deactivate"),
        ],
        cleanup=["close settings"],
    ),
    
    # ──────────────────────────────────────────
    Scenario(
        id=14,
        name="Extensive Settings Coverage Test",
        description="Open various Windows Settings pages sequentially to demonstrate capabilities",
        steps=[
            Step("hi jarvis",                    wait=0.5,  description="Activate"),
            Step("open linkedln",                wait=2.0,  description="Open Settings home"),
            Step("clink thippeswammy ",         wait=1.0,  description="Go to System"),
            # Step("open settings bluetooth",      wait=1.0,  description="Go to Bluetooth"),
            # Step("open settings network",        wait=1.0,  description="Go to Network"),
            # Step("open settings personalization",wait=1.0,  description="Go to Personalization"),
            # Step("open settings apps",           wait=1.0,  description="Go to Apps"),
            # Step("open settings accounts",       wait=1.0,  description="Go to Accounts"),
            # Step("open settings time",           wait=1.0,  description="Go to Time & Language"),
            # Step("open settings gaming",         wait=1.0,  description="Go to Gaming"),
            # Step("open settings accessibility",  wait=1.0,  description="Go to Accessibility"),
            # Step("open settings privacy",        wait=1.0,  description="Go to Privacy"),
            # Step("open settings update",         wait=1.0,  description="Go to Windows Update"),
            # Step("close settings",               wait=1.0,  description="Close Settings"),
            # Step("close jarvis",                 wait=0.3,  description="Deactivate"),
        ],
        cleanup=["close settings"],
    ),
]


# ─────────────────────────────────────────────
#  Test Runner
# ─────────────────────────────────────────────

class LiveTestRunner:

    PASS  = "✅ PASS"
    FAIL  = "❌ FAIL"
    SKIP  = "⏭  SKIP"
    SEP   = "─" * 70

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self._engine: Optional[JarvisEngine] = None

    def _get_engine(self) -> JarvisEngine:
        if self._engine is None:
            print("  Initializing Jarvis Engine...")
            self._engine = JarvisEngine(
                feedback_fn=lambda msg: print(f"    [Jarvis] {msg}"),
                enable_window_tracking=True,
            )
        return self._engine

    def _shutdown(self):
        if self._engine:
            self._engine.shutdown()
            self._engine = None

    # ── Run single step ──────────────────────
    def run_step(self, step: Step, engine: JarvisEngine) -> StepResult:
        t0 = time.time()
        if self.dry_run:
            # Parse only — show what would happen
            intent = IntentEngine().parse(step.command)
            return StepResult(
                step=step,
                success=True,
                message=f"[DRY] → {intent.action.name}({intent.target!r})",
                duration=0.0,
            )
            
        img_before = None
        img_after = None
        
        try:
            img_before = pyautogui.screenshot()
            
            result = engine.process(step.command)
            time.sleep(step.wait)
            
            img_after = pyautogui.screenshot()
            duration = time.time() - t0
            
            actual_success = result.success
            message = result.message or "(no message)"
            
            if actual_success and step.expect_visual_change:
                diff = ImageChops.difference(img_before.convert("RGB"), img_after.convert("RGB")).getbbox()
                if diff is None:
                    actual_success = False
                    message = "FAILED VISUAL ASSERTION: Engine returned PASS but screen did not change."
                    print(f"        → [Visual Alert] Step failed because screen did not update visually!")

            return StepResult(
                step=step,
                success=actual_success,
                message=message,
                duration=duration,
                img_before=img_before,
                img_after=img_after
            )
        except Exception as e:
            duration = time.time() - t0
            return StepResult(
                step=step, success=False,
                message=f"EXCEPTION: {e}",
                duration=duration,
                img_before=img_before,
                img_after=img_after
            )

    # ── Run single scenario ──────────────────
    def run_scenario(self, scenario: Scenario) -> ScenarioResult:
        print(f"\n{self.SEP}")
        print(f"  SCENARIO {scenario.id}: {scenario.name}")
        print(f"  {scenario.description}")
        print(f"  Steps: {len(scenario.steps)}")
        print(self.SEP)

        engine = self._get_engine()
        s_result = ScenarioResult(scenario=scenario)
        t0 = time.time()

        for idx, step in enumerate(scenario.steps, 1):
            label = step.description or step.command
            print(f"  [{idx:02d}] {label}")
            print(f"        → Command: {step.command!r}")

            step_result = self.run_step(step, engine)

            status = self.PASS if step_result.success == step.expect_success else self.FAIL
            expect_tag = "(expected fail)" if not step.expect_success else ""

            print(f"        → {status} {expect_tag}  [{step_result.duration:.1f}s]")
            if step_result.message:
                print(f"           {step_result.message}")

            s_result.step_results.append(step_result)

        # Run cleanup steps silently
        if scenario.cleanup and not self.dry_run:
            print(f"\n  Cleanup...")
            for cmd in scenario.cleanup:
                try:
                    engine.process(cmd)
                    time.sleep(0.5)
                except Exception:
                    pass

        s_result.total_time = time.time() - t0
        return s_result

    def run_all(self, scenario_ids: list[int] = None) -> list[ScenarioResult]:
        targets = [s for s in SCENARIOS if (scenario_ids is None or s.id in scenario_ids)]

        print("\n" + "═" * 70)
        print("  JARVIS LIVE TEST SUITE")
        print(f"  Mode: {'DRY RUN (parse only)' if self.dry_run else 'LIVE (real Windows interaction)'}")
        print(f"  Scenarios to run: {len(targets)}")
        print("═" * 70)

        all_results = []
        if not self.dry_run:
            report_gen = VisualReportGenerator()
        else:
            report_gen = None

        for scenario in targets:
            result = self.run_scenario(scenario)
            all_results.append(result)
            
            if report_gen:
                report_gen.add_scenario(scenario.name, result.passed)
                for sr in result.step_results:
                    report_gen.add_step(
                        command=sr.step.command,
                        desc=sr.step.description,
                        expect_success=sr.step.expect_success,
                        expect_visual=sr.step.expect_visual_change,
                        success=sr.success,
                        message=sr.message,
                        img_before=sr.img_before,
                        img_after=sr.img_after
                    )
                report_gen.end_scenario()

        self._print_summary(all_results)
        
        if report_gen:
            report_path = report_gen.save()
            print(f"\n  [✔] Visual Evaluation Report Generated at: {report_path}")
            
        self._shutdown()
        return all_results

    # ── Summary Report ───────────────────────
    def _print_summary(self, results: list[ScenarioResult]):
        print("\n" + "═" * 70)
        print("  RESULTS SUMMARY")
        print("═" * 70)

        total_steps = 0
        total_passed = 0
        total_failed = 0

        for r in results:
            icon = "✅" if r.passed else "❌"
            print(f"  {icon} Scenario {r.scenario.id}: {r.scenario.name}")
            print(f"       Steps: {r.pass_count}/{len(r.step_results)} passed  |  Time: {r.total_time:.1f}s")
            if not r.passed:
                # Show failed steps
                for sr in r.step_results:
                    if sr.success != sr.step.expect_success:
                        print(f"       ❌ FAILED: {sr.step.description or sr.step.command!r}")
                        print(f"          → {sr.message}")
            total_steps  += len(r.step_results)
            total_passed += r.pass_count
            total_failed += r.fail_count

        print(self.SEP)
        pct = (total_passed / total_steps * 100) if total_steps else 0
        print(f"  TOTAL: {total_passed}/{total_steps} steps passed ({pct:.0f}%)")
        scenarios_ok = sum(1 for r in results if r.passed)
        print(f"  SCENARIOS: {scenarios_ok}/{len(results)} passed")
        print("═" * 70 + "\n")


# ─────────────────────────────────────────────
#  CLI Entry Point
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Jarvis Live Sequence Test Runner"
    )
    parser.add_argument(
        "--scenario", "-s", type=int, nargs="+",
        help="Run specific scenario IDs (e.g. --scenario 1 3 5)",
    )
    parser.add_argument(
        "--list", "-l", action="store_true",
        help="List all scenarios and exit",
    )
    parser.add_argument(
        "--dry-run", "-d", action="store_true",
        help="Parse commands only, do not interact with Windows",
    )
    args = parser.parse_args()

    if args.list:
        print("\nAvailable Scenarios:")
        for s in SCENARIOS:
            print(f"  {s.id:2d}. {s.name}")
            print(f"      {s.description}")
            print(f"      Steps: {len(s.steps)}")
        return

    # Change working dir to project root
    os.chdir(os.path.join(os.path.dirname(__file__), '..', '..'))

    runner = LiveTestRunner(dry_run=args.dry_run)
    runner.run_all(scenario_ids=args.scenario)


if __name__ == "__main__":
    main()
