"""
tests/regression/test_regression.py
======================================
Converts the regression_runner into proper pytest test functions.
Run with: pytest -v -m regression

Does NOT execute live scenarios (requires running Ollama + real desktop).
Instead, tests the structural integrity of the baseline and the crash
detection machinery itself.
"""
import json
import time
import pytest
from pathlib import Path

pytestmark = pytest.mark.regression

BASELINE_PATH = Path(__file__).parent / "baseline_v1.json"

EXPECTED_SCENARIO_NAMES = [
    "01 \u2014 System Controls and Session",
    "02 \u2014 Notepad Full Lifecycle",
    "03 \u2014 Multi-App Window Management",
    "04 \u2014 File Explorer Navigation",
    "05 \u2014 Edge Browsing and Search",
    "06 \u2014 Settings: Display and Sound",
    "07 \u2014 Settings: Bluetooth and Wi-Fi",
    "08 \u2014 Settings: Personalization",
    "09 \u2014 Self-Learning Demo",
    "10 \u2014 Episodic Memory Query",
    "11 \u2014 Task Memory Resume",
    "12 \u2014 Compound Commands",
]


# ── Baseline format validation ────────────────────────────────

def test_baseline_file_exists():
    """Baseline JSON must exist on disk."""
    assert BASELINE_PATH.exists(), (
        f"baseline_v1.json not found at {BASELINE_PATH}. "
        "Run the regression runner with --save-baseline first."
    )


def test_baseline_is_valid_json(baseline):
    """Baseline must be parseable JSON with top-level 'scenarios' key."""
    assert "scenarios" in baseline, "Missing 'scenarios' key in baseline"
    assert isinstance(baseline["scenarios"], dict)


def test_baseline_has_all_12_scenarios(baseline, scenario_names):
    """All 12 expected scenario keys must be present in the baseline."""
    missing = [name for name in scenario_names if name not in baseline["scenarios"]]
    assert missing == [], f"Missing scenarios in baseline: {missing}"


def test_baseline_scenarios_have_passed_field(baseline):
    """Every scenario entry must have a 'passed' boolean field."""
    for name, data in baseline["scenarios"].items():
        assert "passed" in data, f"Scenario '{name}' missing 'passed' field"
        assert isinstance(data["passed"], bool), (
            f"Scenario '{name}'.passed must be bool, got {type(data['passed'])}"
        )


def test_baseline_scenarios_have_steps(baseline):
    """Every scenario entry must have a non-empty 'steps' dict."""
    for name, data in baseline["scenarios"].items():
        assert "steps" in data, f"Scenario '{name}' missing 'steps'"
        assert isinstance(data["steps"], dict), f"Scenario '{name}'.steps must be dict"
        assert len(data["steps"]) > 0, f"Scenario '{name}' has empty steps"


def test_baseline_all_scenarios_passed(baseline):
    """All scenarios in the saved baseline must have passed=True."""
    failed = [name for name, data in baseline["scenarios"].items() if not data["passed"]]
    assert failed == [], f"Baseline has failed scenarios: {failed}"


# ── CrashDetector unit tests ──────────────────────────────────

def test_crash_detector_imports():
    """CrashDetector must be importable."""
    from tests.regression.crash_detector import CrashDetector
    assert CrashDetector is not None


def test_crash_detector_passes_fast_step():
    """A step that completes instantly should pass."""
    from tests.regression.crash_detector import CrashDetector
    detector = CrashDetector(step_timeout=5.0)
    result = detector.run_scenario("Fast Step", [
        ("noop", lambda: None),
    ])
    assert result.passed
    assert len(result.steps) == 1
    assert result.steps[0].passed


def test_crash_detector_catches_exception():
    """A step that raises an exception should be marked as failed."""
    from tests.regression.crash_detector import CrashDetector
    detector = CrashDetector(step_timeout=5.0)
    result = detector.run_scenario("Failing Step", [
        ("bad_step", lambda: (_ for _ in ()).throw(ValueError("boom"))),
    ])
    assert not result.passed
    assert not result.steps[0].passed
    assert result.steps[0].error is not None


def test_crash_detector_timeout_flags_step():
    """A step that hangs beyond timeout must be flagged as timed_out."""
    from tests.regression.crash_detector import CrashDetector
    detector = CrashDetector(step_timeout=0.3)  # very short timeout

    def hang():
        time.sleep(10)  # will be killed by timeout

    result = detector.run_scenario("Hanging Step", [("hang", hang)])
    assert not result.passed
    assert result.steps[0].timed_out is True


def test_crash_detector_stops_after_first_failure():
    """CrashDetector must not run subsequent steps after one fails."""
    from tests.regression.crash_detector import CrashDetector
    executed = []

    detector = CrashDetector(step_timeout=5.0)
    result = detector.run_scenario("Stop On Fail", [
        ("step1_fails", lambda: (_ for _ in ()).throw(RuntimeError("fail"))),
        ("step2_skipped", lambda: executed.append("step2")),
    ])
    assert not result.passed
    assert len(result.steps) == 1       # stopped after step 1
    assert "step2" not in executed      # step2 never ran


def test_scenario_result_summary_format():
    """ScenarioResult.summary() must return a non-empty string."""
    from tests.regression.crash_detector import CrashDetector
    detector = CrashDetector(step_timeout=5.0)
    result = detector.run_scenario("Summary Test", [("ok", lambda: None)])
    summary = result.summary()
    assert isinstance(summary, str)
    assert len(summary) > 0
    assert "Summary Test" in summary


# ── compare_to_baseline (structural only) ────────────────────

def test_compare_to_baseline_passes_with_no_prior_run():
    """
    compare_to_baseline must return True when there are no current results
    to compare (graceful: no results == no regressions detected).
    """
    from tests.regression.regression_runner import RegressionRunner
    runner = RegressionRunner()
    # _results is empty — no scenarios ran
    ok = runner.compare_to_baseline(path=BASELINE_PATH)
    assert ok is True  # no regressions == all good
