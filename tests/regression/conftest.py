"""
tests/regression/conftest.py — Regression fixtures
====================================================
Fixtures for baseline loading and scenario name validation.
"""
import json
import pytest
from pathlib import Path

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


@pytest.fixture(scope="session")
def baseline():
    """Loads and returns the parsed baseline_v1.json dict."""
    assert BASELINE_PATH.exists(), f"Baseline not found: {BASELINE_PATH}"
    with open(BASELINE_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def scenario_names():
    """Returns the list of expected scenario keys."""
    return EXPECTED_SCENARIO_NAMES
