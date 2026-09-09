"""
tests/unit/test_gateway_daemon.py
====================================
Unit tests for jarvis.gateway.gateway.GatewayDaemon.

GatewayDaemon.bootstrap() wires together Memory, LLMRouter, SkillBus,
AgentBus/MCPBus, SessionManager and ChannelManager from a YAML config file.
These tests exercise that wiring, its failure modes on bad/missing config,
status() reporting, and stop()/shutdown behavior -- all without starting
real channel threads (CLIAdapter.stream() blocks on stdin) or letting
config failures reach out to real Ollama / write into the real project
directory.

Fixtures reused from tests/conftest.py:
- mock_gateway: a *real*, already-bootstrapped GatewayDaemon (SemanticEncoder
  and LLMRouter's health check are patched out; router is swapped for
  mock_router post-bootstrap). Used for the "successful bootstrap",
  status(), and stop() tests.
- mock_router / mock_memory / tmp_db_path: available for direct use if a
  test needs to build components itself instead of going through mock_gateway.

New, narrowly-scoped mocks added here (not covered by any existing fixture):
- jarvis.utils.ollama_utils.is_ollama_running / prewarm_models: bootstrap()
  talks to a real local Ollama server and even spawns a helper subprocess
  when it isn't reachable. The bad-config tests below intentionally exercise
  code paths *before* LLMRouter construction, so they still run through this
  Ollama bootstrap step -- these are patched to keep those tests hermetic
  (no real network calls, no ~30s wait for a server that isn't running).
- jarvis.gateway.gateway.MemoryManager: for the "missing config file" test,
  bootstrap() reaches real Memory construction using a default relative
  db path resolved against the *actual* project root before it fails --
  patched here purely to avoid writing a stray sqlite file into the repo.
"""
import yaml
import pytest
from unittest.mock import MagicMock, patch

from jarvis.gateway.gateway import GatewayDaemon

pytestmark = pytest.mark.unit


# ── bootstrap: success ──────────────────────────────────────────────

def test_bootstrap_populates_core_components(mock_gateway):
    """After bootstrap(), all shared managers/components must be wired up."""
    assert mock_gateway.memory is not None
    assert mock_gateway.router is not None  # swapped for mock_router by the fixture
    assert mock_gateway.bus is not None
    assert mock_gateway.agent_bus is not None
    assert mock_gateway.mcp_bus is not None
    assert mock_gateway.session_mgr is not None
    assert mock_gateway.channel_mgr is not None
    # bootstrap() alone must not flip the daemon into the "running" state
    assert mock_gateway._running is False


def test_bootstrap_registers_default_cli_channel(mock_gateway):
    """Default config (no explicit channels section) enables the CLI channel."""
    names = [c["name"] for c in mock_gateway.channel_mgr.list_channels()]
    assert "cli" in names


def test_bootstrap_is_idempotent(mock_gateway):
    """A second bootstrap() call is a documented no-op once memory is set."""
    session_mgr_before = mock_gateway.session_mgr
    channel_mgr_before = mock_gateway.channel_mgr
    memory_before = mock_gateway.memory

    mock_gateway.bootstrap()

    assert mock_gateway.session_mgr is session_mgr_before
    assert mock_gateway.channel_mgr is channel_mgr_before
    assert mock_gateway.memory is memory_before


# ── bootstrap: bad / missing config ──────────────────────────────────

def test_bootstrap_with_malformed_yaml_raises(tmp_path):
    """
    Invalid YAML syntax fails inside ConfigManager.load() -- the very first
    thing bootstrap() does -- before Ollama or any component is touched.
    """
    bad_yaml = tmp_path / "bad_config.yaml"
    bad_yaml.write_text("llm: [unclosed\n  primary: local", encoding="utf-8")

    daemon = GatewayDaemon(config_path=str(bad_yaml))

    with pytest.raises(yaml.YAMLError):
        daemon.bootstrap()

    # Failure happened before any component was constructed.
    assert daemon.memory is None
    assert daemon.router is None
    assert daemon.session_mgr is None


def test_bootstrap_with_malformed_config_structure_raises(tmp_path):
    """
    A config that parses fine as YAML but has the wrong shape (a string
    where the 'llm' mapping is expected) blows up with a bare AttributeError
    while resolving the prewarm model list -- before Memory/Router exist.
    Nothing in bootstrap() validates config shape (ConfigManager.validate()
    exists but bootstrap() never calls it), so this is a raw, unhelpful
    exception rather than a clear configuration error.
    """
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text("llm: not_a_mapping\nchannels: {}\n", encoding="utf-8")

    daemon = GatewayDaemon(config_path=str(cfg_path))

    with patch("jarvis.utils.ollama_utils.is_ollama_running", return_value=True):
        with pytest.raises(AttributeError):
            daemon.bootstrap()

    assert daemon.memory is None
    assert daemon.router is None


def test_bootstrap_with_missing_config_file_leaves_partial_state(tmp_path):
    """
    ConfigManager.load() silently treats a missing config file as an empty
    config ({}) instead of raising -- see the comment in ConfigManager.load().
    bootstrap() therefore sails past config loading with an empty config and
    only fails much later, in LLMRouter.from_config(), which does its own
    `open(config_path)` and raises FileNotFoundError.

    This test documents the resulting gap: the daemon is left half-wired
    (memory constructed, router not) with no rollback, and the underlying
    cause (a missing config file) is reported via a low-level
    FileNotFoundError far from where the bad path was actually supplied.
    """
    missing_path = tmp_path / "does_not_exist.yaml"
    daemon = GatewayDaemon(config_path=str(missing_path))

    with patch("jarvis.utils.ollama_utils.is_ollama_running", return_value=True), \
         patch("jarvis.utils.ollama_utils.prewarm_models"), \
         patch("jarvis.gateway.gateway.MemoryManager") as MockMemoryManager:
        MockMemoryManager.return_value = MagicMock()

        with pytest.raises(FileNotFoundError):
            daemon.bootstrap()

    # Config silently defaulted to {} -- no exception at the ConfigManager stage.
    assert daemon._cfg == {}
    # Partial init: memory got constructed, router never did.
    assert daemon.memory is not None
    assert daemon.router is None


# ── status() ─────────────────────────────────────────────────────────

def test_status_shape_before_bootstrap():
    """status() must be safe pre-bootstrap and report sane defaults."""
    daemon = GatewayDaemon()

    result = daemon.status()

    assert result == {
        "running": False,
        "channels": [],
        "sessions": 0,
        "memory": "unknown",
    }


def test_status_shape_after_bootstrap(mock_gateway):
    result = mock_gateway.status()

    assert set(result.keys()) == {"running", "channels", "sessions", "memory"}
    assert result["running"] is False
    assert isinstance(result["channels"], list)
    assert any(c["name"] == "cli" for c in result["channels"])
    assert result["sessions"] == 0
    assert result["memory"] == mock_gateway.memory.get_db_path()


def test_status_reflects_running_flag(mock_gateway):
    mock_gateway._running = True
    assert mock_gateway.status()["running"] is True


# ── stop() / shutdown ──────────────────────────────────────────────

def test_stop_sets_running_false(mock_gateway):
    mock_gateway._running = True

    mock_gateway.stop()

    assert mock_gateway._running is False
    assert mock_gateway.status()["running"] is False


def test_stop_is_safe_without_start(mock_gateway):
    """stop() must not raise even though start() (and its threads) never ran."""
    mock_gateway.stop()  # should not raise
    assert mock_gateway._running is False


def test_stop_stops_registered_channels(mock_gateway):
    """stop() must delegate to channel_mgr so adapters get their stop hook."""
    adapter = MagicMock()
    adapter.name = "probe"
    adapter.is_available.return_value = True
    mock_gateway.channel_mgr.add_channel(adapter)

    mock_gateway.stop()

    adapter.stop.assert_called_once()
    adapter.on_stop.assert_called_once()


def test_stop_safe_on_never_bootstrapped_daemon():
    """stop() on a daemon that never bootstrapped (channel_mgr is None) must not raise."""
    daemon = GatewayDaemon()

    daemon.stop()  # should not raise

    assert daemon._running is False
