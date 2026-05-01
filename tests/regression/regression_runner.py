"""
Regression Runner
=================
Runs all test scenarios, compares results to a saved baseline,
and flags any NEW failures as regressions.

Usage:
    python -m tests.regression.regression_runner --save-baseline
    python -m tests.regression.regression_runner --compare

The baseline JSON format:
{
  "created_at": "2026-05-01T...",
  "scenarios": {
    "scenario_name": {
      "passed": true,
      "steps": {
        "step_name": {"passed": true, "duration_ms": 120.5}
      }
    }
  }
}
"""

import argparse
import importlib
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from tests.regression.crash_detector import CrashDetector, ScenarioResult

logger = logging.getLogger(__name__)

BASELINE_PATH = Path(__file__).parent / "baseline_v1.json"
REPORTS_DIR = Path(__file__).parent.parent.parent / "reports"


class RegressionRunner:
    def __init__(self, step_timeout: float = 30.0):
        self.detector = CrashDetector(
            step_timeout=step_timeout,
            screenshot_dir=str(REPORTS_DIR / "screenshots"),
        )
        self._results: list[ScenarioResult] = []

    def run_all(self) -> list[ScenarioResult]:
        """Discover and run all scenario modules in tests/live/."""
        live_dir = Path(__file__).parent.parent / "live"
        if not live_dir.exists():
            logger.warning(f"No live/ directory found at {live_dir}")
            return []

        scenario_files = sorted(live_dir.glob("scenario_*.py"))
        logger.info(f"Found {len(scenario_files)} scenario files.")

        for f in scenario_files:
            module_name = f"tests.live.{f.stem}"
            try:
                mod = importlib.import_module(module_name)
                if hasattr(mod, "run") and callable(mod.run):
                    result = mod.run(self.detector)
                    self._results.append(result)
                    print(result.summary())
                else:
                    logger.warning(f"Module {module_name} has no run(detector) function.")
            except Exception as e:
                logger.error(f"Failed to run {module_name}: {e}")

        return self._results

    def save_baseline(self, path: Path = BASELINE_PATH) -> None:
        """Save current results as the new baseline."""
        baseline = {
            "created_at": datetime.now().isoformat(),
            "scenarios": {
                r.scenario_name: {
                    "passed": r.passed,
                    "steps": {
                        s.name: {"passed": s.passed, "duration_ms": round(s.duration_ms, 1)}
                        for s in r.steps
                    },
                }
                for r in self._results
            },
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(baseline, f, indent=2)
        print(f"\n[Baseline] Saved to {path}")

    def compare_to_baseline(self, path: Path = BASELINE_PATH) -> bool:
        """
        Compare current run against saved baseline.
        Returns True if no regressions (new failures), False if regressions found.
        """
        if not path.exists():
            print(f"[Baseline] No baseline found at {path}. Run with --save-baseline first.")
            return True  # Not a failure — just no baseline yet

        with open(path) as f:
            baseline = json.load(f)

        regressions = []
        for result in self._results:
            name = result.scenario_name
            if name not in baseline["scenarios"]:
                continue  # New scenario — not in baseline, skip comparison

            baseline_passed = baseline["scenarios"][name]["passed"]
            if baseline_passed and not result.passed:
                # Was passing, now failing = REGRESSION
                regressions.append(name)
                print(f"  ❌ REGRESSION: '{name}' was passing, now failing!")
                for s in result.failed_steps:
                    print(f"      Step failed: '{s.name}' — {s.error or 'timeout' if s.timed_out else ''}")

        if regressions:
            print(f"\n[Regression] {len(regressions)} regression(s) found. BLOCKED.")
            return False

        print("\n[Regression] No new regressions. ✅")
        return True

    def print_summary(self) -> None:
        total = len(self._results)
        passed = sum(1 for r in self._results if r.passed)
        print(f"\n{'='*50}")
        print(f"Results: {passed}/{total} scenarios passed")
        print(f"{'='*50}")
        for r in self._results:
            icon = "✅" if r.passed else "❌"
            print(f"  {icon} {r.scenario_name}")


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

    parser = argparse.ArgumentParser(description="Jarvis Regression Runner")
    parser.add_argument("--save-baseline", action="store_true",
                        help="Run all scenarios and save results as new baseline")
    parser.add_argument("--compare", action="store_true",
                        help="Run scenarios and compare against saved baseline")
    parser.add_argument("--timeout", type=float, default=30.0,
                        help="Per-step timeout in seconds (default: 30)")
    args = parser.parse_args()

    runner = RegressionRunner(step_timeout=args.timeout)
    runner.run_all()
    runner.print_summary()

    if args.save_baseline:
        runner.save_baseline()
    elif args.compare:
        ok = runner.compare_to_baseline()
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
