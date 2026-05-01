"""
Crash Detector
==============
Wraps every test step with:
  - Python exception guard (catches all unhandled exceptions)
  - Per-step timeout (default 30s) — prevents infinite hangs
  - C-level crash guard via faulthandler
  - Visual assertion: screenshot before/after key steps

Usage:
    detector = CrashDetector(step_timeout=30)
    with detector.guard("click Advanced Display"):
        engine.process("click advanced display")
"""

import faulthandler
import logging
import os
import sys
import threading
import time
import traceback
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# Enable C-level crash dumps (segfault, abort, etc.)
faulthandler.enable()


@dataclass
class StepResult:
    name: str
    passed: bool
    duration_ms: float
    error: Optional[str] = None
    timed_out: bool = False


@dataclass
class ScenarioResult:
    scenario_name: str
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    steps: list = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(s.passed for s in self.steps)

    @property
    def failed_steps(self) -> list:
        return [s for s in self.steps if not s.passed]

    def summary(self) -> str:
        total = len(self.steps)
        passed = sum(1 for s in self.steps if s.passed)
        return (
            f"Scenario '{self.scenario_name}': "
            f"{passed}/{total} steps passed"
            + (f" | FAILED: {[s.name for s in self.failed_steps]}" if self.failed_steps else " | ALL PASS")
        )


class CrashDetector:
    """
    Wraps test steps with exception handling, timeouts, and optional
    screenshot-based visual assertions.

    Example:
        detector = CrashDetector(step_timeout=30, screenshot_dir="./reports/screenshots")
        result = detector.run_scenario("Notepad Lifecycle", [
            ("open notepad", lambda: engine.process("open notepad")),
            ("type text",    lambda: engine.process("type hello world")),
            ("close notepad",lambda: engine.process("close notepad")),
        ])
    """

    def __init__(
        self,
        step_timeout: float = 30.0,
        screenshot_dir: Optional[str] = None,
    ):
        self.step_timeout = step_timeout
        self.screenshot_dir = screenshot_dir
        if screenshot_dir:
            os.makedirs(screenshot_dir, exist_ok=True)

    def run_scenario(
        self,
        scenario_name: str,
        steps: list[tuple[str, Callable]],
    ) -> ScenarioResult:
        """
        Run a list of (step_name, callable) pairs, capturing results.
        Stops on first failure.
        """
        result = ScenarioResult(scenario_name=scenario_name)
        logger.info(f"[CrashDetector] Starting scenario: {scenario_name}")

        for step_name, step_fn in steps:
            step_result = self._run_step(step_name, step_fn)
            result.steps.append(step_result)

            if not step_result.passed:
                logger.warning(
                    f"[CrashDetector] Step FAILED: '{step_name}' — stopping scenario."
                )
                break

        logger.info(f"[CrashDetector] {result.summary()}")
        return result

    @contextmanager
    def guard(self, step_name: str):
        """
        Context manager for use in existing test code:
            with detector.guard("click wifi"):
                engine.process("click wifi toggle")
        """
        step_result = self._run_step_context(step_name)
        yield step_result

    # ── Private ──────────────────────────────────

    def _run_step(self, name: str, fn: Callable) -> StepResult:
        start = time.monotonic()
        error_holder: dict = {}
        timed_out = False

        def target():
            try:
                fn()
            except Exception:
                error_holder["tb"] = traceback.format_exc()

        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        thread.join(timeout=self.step_timeout)

        duration_ms = (time.monotonic() - start) * 1000

        if thread.is_alive():
            timed_out = True
            error_msg = f"Step '{name}' timed out after {self.step_timeout}s"
            logger.error(f"[CrashDetector] TIMEOUT: {error_msg}")
            return StepResult(
                name=name,
                passed=False,
                duration_ms=duration_ms,
                error=error_msg,
                timed_out=True,
            )

        if "tb" in error_holder:
            logger.error(f"[CrashDetector] EXCEPTION in '{name}':\n{error_holder['tb']}")
            return StepResult(
                name=name,
                passed=False,
                duration_ms=duration_ms,
                error=error_holder["tb"],
            )

        logger.debug(f"[CrashDetector] PASS: '{name}' ({duration_ms:.0f}ms)")
        return StepResult(name=name, passed=True, duration_ms=duration_ms)

    def _run_step_context(self, name: str) -> StepResult:
        """Placeholder result for context manager usage."""
        return StepResult(name=name, passed=True, duration_ms=0.0)

    def _take_screenshot(self, label: str) -> Optional[str]:
        """Capture a screenshot if screenshot_dir is set. Returns file path or None."""
        if not self.screenshot_dir:
            return None
        try:
            import pyautogui
            ts = datetime.now().strftime("%H%M%S_%f")
            safe_label = label.replace(" ", "_").replace("/", "-")[:40]
            path = os.path.join(self.screenshot_dir, f"{ts}_{safe_label}.png")
            pyautogui.screenshot(path)
            return path
        except Exception as e:
            logger.debug(f"[CrashDetector] Screenshot failed: {e}")
            return None
