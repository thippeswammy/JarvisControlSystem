"""
Jarvis Test Suite — Master Runner
===================================
Runs all unit + integration tests (pytest) then the live sequences.

Usage:
  python TEST/run_tests.py                  # unit + integration only (safe)
  python TEST/run_tests.py --live           # also run live scenarios
  python TEST/run_tests.py --live --scenario 1 2   # specific live scenarios
  python TEST/run_tests.py --dry-run        # live tests in parse-only mode
  python TEST/run_tests.py --unit-only      # only unit/integration pytest
"""
import sys
import os
import subprocess
import argparse
import time

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, PROJECT_ROOT)


def run_pytest(label: str, test_path: str) -> bool:
    """Run pytest on a directory and return True if all passed."""
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")

    result = subprocess.run(
        [sys.executable, "-m", "pytest", test_path, "-v", "--tb=short", "--no-header"],
        cwd=PROJECT_ROOT,
    )
    return result.returncode == 0


def run_live_tests(scenario_ids=None, dry_run=False) -> bool:
    """Run the live sequence tests."""
    print(f"\n{'='*60}")
    print(f"  LIVE SEQUENCE TESTS {'(DRY RUN)' if dry_run else '(REAL WINDOWS)'}")
    print(f"{'='*60}")

    cmd = [sys.executable, "TEST/live/test_live_sequence.py"]
    if scenario_ids:
        cmd += ["--scenario"] + [str(s) for s in scenario_ids]
    if dry_run:
        cmd += ["--dry-run"]

    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Jarvis Master Test Runner")
    parser.add_argument("--live", action="store_true",
                        help="Also run live sequence tests (interacts with Windows)")
    parser.add_argument("--unit-only", action="store_true",
                        help="Only run unit + integration pytest")
    parser.add_argument("--scenario", "-s", type=int, nargs="+",
                        help="Which live scenario IDs to run")
    parser.add_argument("--dry-run", "-d", action="store_true",
                        help="Live tests: parse-only, no Windows interaction")
    args = parser.parse_args()

    results = {}
    t0 = time.time()

    # ── 1. Unit tests ────────────────────────
    results["Unit: Intent Engine"] = run_pytest(
        "UNIT — Intent Engine", "TEST/unit/test_intent_engine.py"
    )

    # ── 2. Unit: Registry ────────────────────
    results["Unit: Action Registry"] = run_pytest(
        "UNIT — Action Registry", "TEST/unit/test_action_registry.py"
    )

    # ── 3. Integration ───────────────────────
    results["Integration: Pipeline"] = run_pytest(
        "INTEGRATION — Full Pipeline", "TEST/integration/test_pipeline.py"
    )

    # ── 4. Live (optional) ───────────────────
    if args.live and not args.unit_only:
        results["Live Sequences"] = run_live_tests(
            scenario_ids=args.scenario,
            dry_run=args.dry_run,
        )
    elif args.dry_run and not args.unit_only:
        # Dry-run without --live is implied
        results["Live Sequences (dry)"] = run_live_tests(
            scenario_ids=args.scenario,
            dry_run=True,
        )

    # ── Summary ──────────────────────────────
    total_time = time.time() - t0
    print(f"\n{'═'*60}")
    print(f"  MASTER RESULTS  ({total_time:.1f}s total)")
    print(f"{'═'*60}")
    all_ok = True
    for name, passed in results.items():
        icon = "✅" if passed else "❌"
        print(f"  {icon} {name}")
        if not passed:
            all_ok = False
    print(f"{'═'*60}")
    if all_ok:
        print("  🎉 ALL TESTS PASSED")
    else:
        print("  ⚠️  SOME TESTS FAILED — check output above")
    print(f"{'═'*60}\n")

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
