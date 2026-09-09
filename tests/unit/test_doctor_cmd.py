"""
tests/unit/test_doctor_cmd.py
================================
Unit tests for jarvis.cli.commands.doctor_cmd.run_doctor().
"""
import io
import sys

import pytest
from unittest.mock import MagicMock, patch
import os

from rich.console import Console as RealConsole

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_gateway_for_doctor(tmp_path, fake_gateway):
    """Gateway mock tailored for doctor_cmd requirements."""
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("jarvis:\n  input_mode: text\n", encoding="utf-8")

    fake_gateway._config_path = str(cfg_file)
    fake_gateway.router = MagicMock()
    fake_gateway.router.status.return_value = {"local": True}
    fake_gateway.router._primary = MagicMock()
    fake_gateway.router._primary.name = "local"

    db_file = tmp_path / "jarvis.db"
    db_file.write_text("")  # create empty file
    fake_gateway.memory = MagicMock()
    fake_gateway.memory.get_db_path.return_value = str(db_file)

    return fake_gateway


# ── run_doctor — does not raise ──────────────────────────────

def test_run_doctor_does_not_raise(mock_gateway_for_doctor):
    from jarvis.cli.commands.doctor_cmd import run_doctor
    # Should print a rich table without throwing
    with patch("jarvis.cli.commands.doctor_cmd.Console"):
        run_doctor(mock_gateway_for_doctor)  # no exception = pass


# ── run_doctor — router check ────────────────────────────────

def test_run_doctor_with_no_router(mock_gateway_for_doctor):
    mock_gateway_for_doctor.router = None
    from jarvis.cli.commands.doctor_cmd import run_doctor
    with patch("jarvis.cli.commands.doctor_cmd.Console"):
        run_doctor(mock_gateway_for_doctor)  # graceful degradation


# ── run_doctor — missing config ───────────────────────────────

def test_run_doctor_with_missing_config(mock_gateway_for_doctor):
    mock_gateway_for_doctor._config_path = "/nonexistent/path.yaml"
    from jarvis.cli.commands.doctor_cmd import run_doctor
    with patch("jarvis.cli.commands.doctor_cmd.Console"):
        run_doctor(mock_gateway_for_doctor)  # should still run, show ❌


# ── run_doctor — missing memory ───────────────────────────────

def test_run_doctor_with_no_memory(mock_gateway_for_doctor):
    mock_gateway_for_doctor.memory = None
    from jarvis.cli.commands.doctor_cmd import run_doctor
    with patch("jarvis.cli.commands.doctor_cmd.Console"):
        run_doctor(mock_gateway_for_doctor)  # graceful degradation


# ── run_doctor — content assertions ───────────────────────────────────
# The tests above only check "does not raise". These use a real rich
# Console redirected to an in-memory buffer (instead of a MagicMock) so we
# can assert on the actual diagnostic text that gets printed for each check.

@pytest.fixture
def doctor_output():
    """Patch doctor_cmd's Console with a real Console writing to an
    in-memory, non-tty buffer. Rich disables ANSI styling for non-tty
    output, so the buffer contains plain text and markup like
    '[green]OK[/green]' renders down to just 'OK'."""
    buffer = io.StringIO()
    console = RealConsole(file=buffer, width=200)
    with patch("jarvis.cli.commands.doctor_cmd.Console", return_value=console):
        yield buffer


def test_run_doctor_reports_python_version(mock_gateway_for_doctor, doctor_output):
    from jarvis.cli.commands.doctor_cmd import run_doctor
    run_doctor(mock_gateway_for_doctor)

    output = doctor_output.getvalue()
    expected_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    assert "Python" in output
    assert expected_ver in output
    assert "OK" in output


def test_run_doctor_config_exists_shows_ok_and_filename(mock_gateway_for_doctor, doctor_output):
    from jarvis.cli.commands.doctor_cmd import run_doctor
    run_doctor(mock_gateway_for_doctor)

    output = doctor_output.getvalue()
    assert "config.yaml" in output
    assert "Missing!" not in output


def test_run_doctor_config_missing_shows_missing_marker(mock_gateway_for_doctor, doctor_output):
    mock_gateway_for_doctor._config_path = "/nonexistent/path.yaml"
    from jarvis.cli.commands.doctor_cmd import run_doctor
    run_doctor(mock_gateway_for_doctor)

    output = doctor_output.getvalue()
    assert "Missing!" in output
    assert "Run `jarvis setup`" in output  # recommendation fired


def test_run_doctor_router_healthy_shows_healthy_status(mock_gateway_for_doctor, doctor_output):
    mock_gateway_for_doctor.router.status.return_value = {"local": True}
    from jarvis.cli.commands.doctor_cmd import run_doctor
    run_doctor(mock_gateway_for_doctor)

    output = doctor_output.getvalue()
    assert "Healthy" in output
    assert "local" in output
    assert "Down" not in output
    assert "Check if Ollama is running" not in output


def test_run_doctor_router_down_shows_down_and_recommendation(mock_gateway_for_doctor, doctor_output):
    mock_gateway_for_doctor.router.status.return_value = {"local": False}
    from jarvis.cli.commands.doctor_cmd import run_doctor
    run_doctor(mock_gateway_for_doctor)

    output = doctor_output.getvalue()
    assert "Down" in output
    assert "Check if Ollama is running" in output


def test_run_doctor_no_router_shows_failed_and_recommendation(mock_gateway_for_doctor, doctor_output):
    mock_gateway_for_doctor.router = None
    from jarvis.cli.commands.doctor_cmd import run_doctor
    run_doctor(mock_gateway_for_doctor)

    output = doctor_output.getvalue()
    assert "Failed" in output
    assert "Router Init" in output
    assert "Check if Ollama is running" in output


def test_run_doctor_memory_connected_shows_size_kb(mock_gateway_for_doctor, doctor_output, tmp_path):
    db_file = tmp_path / "sized.db"
    db_file.write_bytes(b"x" * 2048)  # exactly 2 KB
    mock_gateway_for_doctor.memory.get_db_path.return_value = str(db_file)

    from jarvis.cli.commands.doctor_cmd import run_doctor
    run_doctor(mock_gateway_for_doctor)

    output = doctor_output.getvalue()
    assert "Connected" in output
    assert "2 KB" in output


def test_run_doctor_memory_missing_file_shows_missing(mock_gateway_for_doctor, doctor_output, tmp_path):
    mock_gateway_for_doctor.memory.get_db_path.return_value = str(tmp_path / "does_not_exist.db")

    from jarvis.cli.commands.doctor_cmd import run_doctor
    run_doctor(mock_gateway_for_doctor)

    output = doctor_output.getvalue()
    assert "Missing file" in output


def test_run_doctor_no_memory_shows_failed_initialization(mock_gateway_for_doctor, doctor_output):
    mock_gateway_for_doctor.memory = None
    from jarvis.cli.commands.doctor_cmd import run_doctor
    run_doctor(mock_gateway_for_doctor)

    output = doctor_output.getvalue()
    assert "Initialization" in output
    assert "Failed" in output


def test_run_doctor_ollama_installed_shows_installed(mock_gateway_for_doctor, doctor_output):
    from jarvis.cli.commands.doctor_cmd import run_doctor
    with patch("jarvis.cli.commands.doctor_cmd.shutil.which", return_value=r"C:\tools\ollama.exe"):
        run_doctor(mock_gateway_for_doctor)

    output = doctor_output.getvalue()
    assert "Installed" in output
    assert "Not found in PATH" not in output


def test_run_doctor_ollama_missing_shows_not_found(mock_gateway_for_doctor, doctor_output):
    from jarvis.cli.commands.doctor_cmd import run_doctor
    with patch("jarvis.cli.commands.doctor_cmd.shutil.which", return_value=None):
        run_doctor(mock_gateway_for_doctor)

    output = doctor_output.getvalue()
    assert "Not found in PATH" in output


def test_run_doctor_no_recommendations_when_healthy(mock_gateway_for_doctor, doctor_output):
    """Router healthy + config present → recs list stays empty, so the
    'Recommendations:' section should not print at all."""
    mock_gateway_for_doctor.router.status.return_value = {"local": True}
    from jarvis.cli.commands.doctor_cmd import run_doctor
    run_doctor(mock_gateway_for_doctor)

    output = doctor_output.getvalue()
    assert "Recommendations:" not in output


def test_run_doctor_recommendations_include_both_when_router_down_and_config_missing(
    mock_gateway_for_doctor, doctor_output
):
    mock_gateway_for_doctor.router.status.return_value = {"local": False}
    mock_gateway_for_doctor._config_path = "/nonexistent/path.yaml"
    from jarvis.cli.commands.doctor_cmd import run_doctor
    run_doctor(mock_gateway_for_doctor)

    output = doctor_output.getvalue()
    assert "Recommendations:" in output
    assert "Check if Ollama is running" in output
    assert "Run `jarvis setup`" in output
