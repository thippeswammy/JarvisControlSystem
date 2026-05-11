"""
tests/unit/test_doctor_cmd.py
================================
Unit tests for jarvis.cli.commands.doctor_cmd.run_doctor().
"""
import pytest
from unittest.mock import MagicMock, patch
import os

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
