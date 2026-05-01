"""
Live Scenario Framework
=======================
Base class and utilities for all live/integration test scenarios.

Every live scenario:
  1. Extends LiveScenario
  2. Defines self.steps: list[StepDef]
  3. Each step is wrapped with CrashDetector (timeout + exception guard)
  4. Results are logged to console AND written to reports/

Usage (run individual scenario):
    python -m tests.live.scenario_01_system_and_session

Usage (run all via regression runner):
    python -m tests.regression.regression_runner --live
"""
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

logger = logging.getLogger(__name__)

_REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "reports"


@dataclass
class StepResult:
    """Result of a single scenario step."""
    step_name: str
    passed: bool
    duration_s: float
    error: str = ""
    skip_reason: str = ""

    @property
    def skipped(self) -> bool:
        return bool(self.skip_reason)


@dataclass
class ScenarioResult:
    """Aggregate result of a complete scenario run."""
    scenario_name: str
    steps: list[StepResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(s.passed or s.skipped for s in self.steps)

    @property
    def total(self) -> int:
        return len(self.steps)

    @property
    def pass_count(self) -> int:
        return sum(1 for s in self.steps if s.passed)

    @property
    def fail_count(self) -> int:
        return sum(1 for s in self.steps if not s.passed and not s.skipped)

    @property
    def skip_count(self) -> int:
        return sum(1 for s in self.steps if s.skipped)

    def summary(self) -> str:
        status = "✅ PASS" if self.passed else "❌ FAIL"
        return (
            f"{status} [{self.scenario_name}] "
            f"{self.pass_count}/{self.total} passed, "
            f"{self.fail_count} failed, "
            f"{self.skip_count} skipped"
        )


@dataclass
class StepDef:
    """Definition of one scenario step."""
    name: str
    fn: Callable[[], None]
    timeout_s: float = 30.0
    skip_if: Optional[Callable[[], bool]] = None  # skip if this returns True
    skip_reason: str = ""


class LiveScenario:
    """
    Base class for all live scenario tests.

    Subclasses define:
        self.scenario_name = "01 — System and Session"
        self.steps = [StepDef(...), ...]
        def setup(self): ...      # optional, run before all steps
        def teardown(self): ...   # optional, run after all steps

    The CrashDetector from tests.regression.crash_detector wraps each step.
    """

    scenario_name: str = "Unnamed Scenario"

    def __init__(self):
        self.steps: list[StepDef] = []
        self._result: Optional[ScenarioResult] = None
        self._setup_logging()

    def _setup_logging(self) -> None:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )

    def setup(self) -> None:
        """Override to run setup before all steps."""

    def teardown(self) -> None:
        """Override to run teardown after all steps (even if steps fail)."""

    def run(self) -> ScenarioResult:
        """Execute all steps and return the aggregate result."""
        from tests.regression.crash_detector import CrashDetector

        result = ScenarioResult(scenario_name=self.scenario_name)
        self._result = result

        logger.info(f"\n{'='*60}")
        logger.info(f"▶ SCENARIO: {self.scenario_name}")
        logger.info(f"{'='*60}")

        # Setup
        try:
            self.setup()
        except Exception as exc:
            logger.error(f"[Setup] FAILED: {exc}")
            result.steps.append(StepResult(
                step_name="setup",
                passed=False,
                duration_s=0.0,
                error=str(exc),
            ))
            return result

        # Run each step
        for step_def in self.steps:
            # Skip check
            if step_def.skip_if and step_def.skip_if():
                result.steps.append(StepResult(
                    step_name=step_def.name,
                    passed=True,
                    duration_s=0.0,
                    skip_reason=step_def.skip_reason or "condition met",
                ))
                logger.info(f"  ⏭ SKIP  [{step_def.name}]")
                continue

            logger.info(f"  ▶ STEP  [{step_def.name}]")
            t0 = time.perf_counter()

            detector = CrashDetector(step_timeout=step_def.timeout_s)
            step_result_obj = detector._run_step(
                name=step_def.name,
                fn=step_def.fn,
            )

            duration = time.perf_counter() - t0
            passed = getattr(step_result_obj, "passed", False)
            error = getattr(step_result_obj, "error", "")

            icon = "  ✅ PASS" if passed else "  ❌ FAIL"
            logger.info(f"{icon} [{step_def.name}] ({duration:.2f}s)")
            if error:
                logger.error(f"       Error: {error}")

            result.steps.append(StepResult(
                step_name=step_def.name,
                passed=passed,
                duration_s=duration,
                error=error,
            ))

        # Teardown
        try:
            self.teardown()
        except Exception as exc:
            logger.warning(f"[Teardown] Exception (non-fatal): {exc}")

        # Summary
        logger.info(f"\n{result.summary()}")
        self._save_report(result)
        return result

    def _save_report(self, result: ScenarioResult) -> None:
        """Write a simple .txt report to reports/."""
        _REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        safe_name = self.scenario_name.replace(" ", "_").replace("—", "-")
        report_path = _REPORTS_DIR / f"{safe_name}.txt"
        lines = [result.summary(), ""]
        for step in result.steps:
            if step.skipped:
                lines.append(f"  ⏭ SKIP  {step.step_name} ({step.skip_reason})")
            elif step.passed:
                lines.append(f"  ✅ PASS  {step.step_name} ({step.duration_s:.2f}s)")
            else:
                lines.append(f"  ❌ FAIL  {step.step_name}: {step.error}")
        report_path.write_text("\n".join(lines), encoding="utf-8")
        logger.debug(f"[LiveScenario] Report saved: {report_path}")
