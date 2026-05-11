"""
tests/unit/conftest.py — Unit-test fixtures
============================================
Lightweight, no-I/O fixtures for fast unit tests.
"""
import pytest
from unittest.mock import MagicMock
from datetime import datetime


@pytest.fixture
def fake_session():
    """
    A minimal fake Session object (not a real Session dataclass).
    Used by SlashHandler, SessionManager, and ChannelManager unit tests.
    """
    session = MagicMock()
    session.id = "cli:test_user"
    session.channel = "cli"
    session.user_id = "test_user"
    session.created_at = datetime.now()
    session.last_active = datetime.now()
    session.episodic = MagicMock()
    session.episodic.clear = MagicMock()
    return session


@pytest.fixture
def fake_gateway_status():
    """Dict matching GatewayDaemon.status() output — no live system needed."""
    return {
        "running": True,
        "channels": [
            {"name": "cli", "status": "running"},
            {"name": "telegram", "status": "stopped"},
        ],
        "sessions": 1,
        "memory": "/tmp/jarvis_test.db",
    }


@pytest.fixture
def fake_gateway(fake_gateway_status):
    """A MagicMock gateway for unit tests."""
    gw = MagicMock()
    gw.status.return_value = fake_gateway_status
    gw.session_mgr = MagicMock()
    gw.session_mgr.memory = MagicMock()
    gw.session_mgr.memory.get_stats.return_value = {
        "nodes": 10, "edges": 5, "success_rate": 88.0,
        "db_size_kb": 32, "db_path": "/tmp/test.db"
    }
    gw.session_mgr.memory.search_edges.return_value = []
    return gw
