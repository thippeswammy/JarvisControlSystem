"""
tests/unit/test_channel_manager.py
=====================================
Unit tests for jarvis.gateway.channel_manager.ChannelManager.
"""
import pytest
from unittest.mock import MagicMock, patch

pytestmark = pytest.mark.unit


def _make_adapter(name: str, available: bool = True):
    """Helper to build a mock ChannelAdapter."""
    adapter = MagicMock()
    adapter.name = name
    adapter.is_available.return_value = available
    adapter.on_ready = MagicMock()
    adapter.on_stop = MagicMock()
    adapter.stop = MagicMock()
    adapter.send = MagicMock()
    return adapter


@pytest.fixture
def channel_manager():
    """A ChannelManager with a mocked SessionManager."""
    from jarvis.gateway.channel_manager import ChannelManager
    mgr = ChannelManager(session_mgr=MagicMock())
    return mgr


# ── add_channel ───────────────────────────────────────────────

def test_add_channel_registers_adapter(channel_manager):
    adapter = _make_adapter("cli")
    channel_manager.add_channel(adapter)
    assert "cli" in channel_manager._channels
    assert channel_manager._channels["cli"] is adapter


def test_add_channel_overwrites_same_name(channel_manager):
    a1 = _make_adapter("cli")
    a2 = _make_adapter("cli")
    channel_manager.add_channel(a1)
    channel_manager.add_channel(a2)
    assert channel_manager._channels["cli"] is a2


def test_add_multiple_channels(channel_manager):
    channel_manager.add_channel(_make_adapter("cli"))
    channel_manager.add_channel(_make_adapter("telegram"))
    assert len(channel_manager._channels) == 2


# ── list_channels ─────────────────────────────────────────────

def test_list_channels_empty(channel_manager):
    assert channel_manager.list_channels() == []


def test_list_channels_shows_status(channel_manager):
    channel_manager.add_channel(_make_adapter("cli"))
    result = channel_manager.list_channels()
    assert len(result) == 1
    assert result[0]["name"] == "cli"
    assert "status" in result[0]
    assert "available" in result[0]


# ── stop_all ──────────────────────────────────────────────────

def test_stop_all_calls_stop_on_adapters(channel_manager):
    a1 = _make_adapter("cli")
    a2 = _make_adapter("telegram")
    channel_manager.add_channel(a1)
    channel_manager.add_channel(a2)

    channel_manager.stop_all()

    a1.stop.assert_called_once()
    a2.stop.assert_called_once()
    a1.on_stop.assert_called_once()
    a2.on_stop.assert_called_once()


def test_stop_all_sets_running_false(channel_manager):
    channel_manager._running = True
    channel_manager.stop_all()
    assert channel_manager._running is False


# ── start_all — skips unavailable ────────────────────────────

def test_start_all_skips_unavailable_adapter(channel_manager):
    unavailable = _make_adapter("telegram", available=False)
    channel_manager.add_channel(unavailable)
    channel_manager.start_all()
    # Thread should not be spawned for unavailable adapter
    assert "telegram" not in channel_manager._threads
