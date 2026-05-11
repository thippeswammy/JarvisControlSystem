import subprocess
import pytest
import sys
from pathlib import Path

# Project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

def run_jarvis(args):
    """Run jarvis command via subprocess and return output."""
    cmd = [sys.executable, "-m", "jarvis.cli.main_cli"] + args
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(_PROJECT_ROOT),
        encoding='utf-8'
    )
    return result

def test_cli_help():
    """Test that 'jarvis --help' prints help."""
    result = run_jarvis(["--help"])
    assert result.returncode == 0
    assert "Jarvis" in result.stdout
    assert "Iron Man Architecture CLI" in result.stdout
    assert "Commands" in result.stdout

def test_cli_version():
    """Test that 'jarvis -V' prints version."""
    result = run_jarvis(["-V"])
    assert result.returncode == 0
    assert "Jarvis" in result.stdout

def test_cli_status():
    """Test that 'jarvis status' prints system snapshot."""
    result = run_jarvis(["status"])
    assert result.returncode == 0
    assert "Jarvis System Status" in result.stdout
    assert "Gateway: Offline" in result.stdout

def test_cli_health():
    """Test that 'jarvis health' prints health check."""
    result = run_jarvis(["health"])
    assert result.returncode == 0
    assert "Jarvis Health Check" in result.stdout
    assert "Checking subsystems" in result.stdout

def test_cli_unimplemented():
    """Test that unimplemented commands show a fallback message."""
    result = run_jarvis(["config", "get", "test_key"])
    assert result.returncode == 0
    assert "is registered but not yet implemented" in result.stdout

def test_cli_no_args():
    """Test that running with no args shows help."""
    result = run_jarvis([])
    assert result.returncode == 0
    assert "usage: main_cli.py" in result.stdout
