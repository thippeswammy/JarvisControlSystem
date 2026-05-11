"""
tests/unit/test_logs_cmd.py
==============================
Unit tests for jarvis.cli.commands.logs_cmd.LogAnalyzer.
"""
import pytest
from pathlib import Path
from jarvis.cli.commands.logs_cmd import LogAnalyzer

pytestmark = pytest.mark.unit

SAMPLE_LOG = """\
16:00:01 [INFO] jarvis.gateway.gateway \u2014 [Gateway] Bootstrapping
16:00:02 [INFO] jarvis.memory.memory_manager \u2014 [MemoryManager] DB opened
16:00:03 [WARNING] jarvis.llm.llm_router \u2014 [LLMRouter] tunneled unavailable
16:00:04 [ERROR] jarvis.brain.planner \u2014 Unexpected NoneType in plan
16:00:05 [DEBUG] jarvis.skills.skill_bus \u2014 Discovered 12 skills
16:00:06 [INFO] jarvis.gateway.channel_manager \u2014 Received utterance from cli
"""


@pytest.fixture
def log_file(tmp_path):
    """Write sample log to a temp file and return LogAnalyzer."""
    p = tmp_path / "jarvis.log"
    p.write_text(SAMPLE_LOG, encoding="utf-8")
    return LogAnalyzer(str(p))


@pytest.fixture
def missing_log(tmp_path):
    """LogAnalyzer pointing to a non-existent file."""
    return LogAnalyzer(str(tmp_path / "nonexistent.log"))


# ── tail ─────────────────────────────────────────────────────

def test_tail_returns_lines(log_file):
    lines = log_file.tail(n=3, color=False)
    assert len(lines) == 3

def test_tail_returns_all_when_n_exceeds_file(log_file):
    lines = log_file.tail(n=100, color=False)
    assert len(lines) == 6  # exactly 6 lines in sample

def test_tail_missing_file_returns_error_message(missing_log):
    result = missing_log.tail(n=5, color=False)
    assert len(result) == 1
    assert "not found" in result[0].lower() or "\u274c" in result[0]

def test_tail_color_returns_rich_text_objects(log_file):
    from rich.text import Text
    lines = log_file.tail(n=6, color=True)
    assert all(isinstance(l, Text) for l in lines)


# ── analyze ──────────────────────────────────────────────────

def test_analyze_returns_dict(log_file):
    stats = log_file.analyze()
    assert isinstance(stats, dict)

def test_analyze_counts_total_lines(log_file):
    stats = log_file.analyze()
    assert stats["total_lines"] == 6

def test_analyze_counts_log_levels(log_file):
    stats = log_file.analyze()
    assert stats["levels"]["INFO"] >= 3
    assert stats["levels"]["WARNING"] == 1
    assert stats["levels"]["ERROR"] == 1

def test_analyze_captures_errors(log_file):
    stats = log_file.analyze()
    assert len(stats["errors"]) == 1
    assert "NoneType" in stats["errors"][0]

def test_analyze_missing_file_returns_error_dict(missing_log):
    result = missing_log.analyze()
    assert "error" in result


# ── clear ────────────────────────────────────────────────────

def test_clear_truncates_file(log_file, tmp_path):
    p = tmp_path / "jarvis.log"
    log_file.clear()
    content = p.read_text(encoding="utf-8")
    assert "cleared" in content.lower()

def test_clear_missing_file_returns_false(missing_log):
    assert missing_log.clear() is False
