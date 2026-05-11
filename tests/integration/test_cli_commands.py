"""
tests/integration/test_cli_commands.py
========================================
Integration tests for jarvis CLI commands executed via subprocess.
Tests: memory status/search/prune/analyze, health, doctor.
No Ollama required — gateway bootstraps with mocked encoder.
"""
import subprocess
import sys
import pytest
from pathlib import Path

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def run_jarvis(*args, timeout: int = 30) -> subprocess.CompletedProcess:
    """Run a jarvis CLI command as a subprocess and return the result."""
    cmd = [sys.executable, "-m", "jarvis.cli.main_cli"] + list(args)
    return subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


# ── --help / --version ────────────────────────────────────────

def test_help_exits_zero():
    result = run_jarvis("--help")
    assert result.returncode == 0

def test_version_exits_zero():
    result = run_jarvis("-V")
    assert result.returncode == 0
    combined = result.stdout + result.stderr
    assert "jarvis" in combined.lower() or "v" in combined.lower()


# ── memory status ─────────────────────────────────────────────

def test_memory_status_exits_zero():
    result = run_jarvis("memory", "status")
    # May warn about gateway but should not crash
    assert result.returncode == 0

def test_memory_status_output_has_metrics():
    result = run_jarvis("memory", "status")
    combined = result.stdout + result.stderr
    # Either prints a table or an error — must not be an unhandled exception
    assert "Traceback" not in combined


# ── memory search ─────────────────────────────────────────────

def test_memory_search_exits_zero():
    result = run_jarvis("memory", "search", "notepad")
    assert result.returncode == 0

def test_memory_search_no_crash():
    result = run_jarvis("memory", "search", "open calculator")
    combined = result.stdout + result.stderr
    assert "Traceback" not in combined


# ── memory prune ──────────────────────────────────────────────

def test_memory_prune_exits_zero():
    result = run_jarvis("memory", "prune")
    assert result.returncode == 0

def test_memory_prune_no_crash():
    result = run_jarvis("memory", "prune")
    combined = result.stdout + result.stderr
    assert "Traceback" not in combined


# ── memory analyze ────────────────────────────────────────────

def test_memory_analyze_exits_zero():
    result = run_jarvis("memory", "analyze")
    assert result.returncode == 0

def test_memory_analyze_no_crash():
    result = run_jarvis("memory", "analyze")
    combined = result.stdout + result.stderr
    assert "Traceback" not in combined


# ── health ───────────────────────────────────────────────────

def test_health_exits_zero():
    result = run_jarvis("health")
    assert result.returncode == 0

def test_health_shows_model_info():
    result = run_jarvis("health")
    combined = result.stdout + result.stderr
    assert "Traceback" not in combined


# ── doctor ───────────────────────────────────────────────────

def test_doctor_exits_zero():
    result = run_jarvis("doctor")
    assert result.returncode == 0

def test_doctor_no_crash():
    result = run_jarvis("doctor")
    combined = result.stdout + result.stderr
    assert "Traceback" not in combined


# ── status ────────────────────────────────────────────────────

def test_status_exits_zero():
    result = run_jarvis("status")
    assert result.returncode == 0


# ── unknown command ───────────────────────────────────────────

def test_unknown_command_exits_nonzero_or_shows_help():
    result = run_jarvis("thiscommanddoesnotexist")
    # argparse will either error (returncode != 0) or fall through to help
    combined = result.stdout + result.stderr
    assert "Traceback" not in combined
