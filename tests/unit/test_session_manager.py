"""
tests/unit/test_session_manager.py
====================================
Unit tests for jarvis.gateway.session_manager.SessionManager.
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

pytestmark = pytest.mark.unit


@pytest.fixture
def session_manager(fake_gateway):
    """A SessionManager with all dependencies mocked."""
    with patch("jarvis.gateway.session_manager.Orchestrator") as MockOrch, \
         patch("jarvis.gateway.session_manager.EpisodicMemory") as MockEpisodic:

        MockOrch.return_value = MagicMock()
        MockOrch.return_value.boot = MagicMock()
        MockEpisodic.return_value = MagicMock()

        from jarvis.gateway.session_manager import SessionManager
        mgr = SessionManager(
            memory=MagicMock(),
            router=MagicMock(),
            bus=MagicMock(),
            gateway=fake_gateway,
            vloop=None,
        )
        yield mgr


# ── get_or_create ────────────────────────────────────────────

def test_get_or_create_makes_new_session(session_manager):
    session = session_manager.get_or_create("cli", "user1")
    assert session.id == "cli:user1"
    assert session.channel == "cli"
    assert session.user_id == "user1"


def test_get_or_create_returns_same_session(session_manager):
    s1 = session_manager.get_or_create("cli", "user1")
    s2 = session_manager.get_or_create("cli", "user1")
    assert s1 is s2


def test_different_users_get_isolated_sessions(session_manager):
    s1 = session_manager.get_or_create("cli", "alice")
    s2 = session_manager.get_or_create("cli", "bob")
    assert s1 is not s2
    assert s1.id != s2.id


def test_different_channels_get_isolated_sessions(session_manager):
    s1 = session_manager.get_or_create("cli", "user1")
    s2 = session_manager.get_or_create("telegram", "user1")
    assert s1 is not s2
    assert s1.channel == "cli"
    assert s2.channel == "telegram"


def test_session_has_slash_handler(session_manager):
    session = session_manager.get_or_create("cli", "user1")
    assert session.slash_handler is not None
    assert session.slash_handler._session is session  # circular ref is set


# ── list_sessions ────────────────────────────────────────────

def test_list_sessions_empty_initially(session_manager):
    assert session_manager.list_sessions() == []


def test_list_sessions_grows_after_create(session_manager):
    session_manager.get_or_create("cli", "u1")
    session_manager.get_or_create("cli", "u2")
    assert len(session_manager.list_sessions()) == 2


# ── kill ─────────────────────────────────────────────────────

def test_kill_removes_session(session_manager):
    session_manager.get_or_create("cli", "user1")
    killed = session_manager.kill("cli:user1")
    assert killed is True
    assert session_manager.get("cli:user1") is None


def test_kill_nonexistent_returns_false(session_manager):
    assert session_manager.kill("cli:nobody") is False


# ── cleanup_idle ─────────────────────────────────────────────

def test_cleanup_idle_removes_stale_sessions(session_manager):
    s = session_manager.get_or_create("cli", "stale")
    # Force last_active far in the past
    from datetime import timedelta
    s.last_active = datetime.now() - timedelta(hours=2)

    session_manager.cleanup_idle(max_age_minutes=60)
    assert session_manager.get("cli:stale") is None
