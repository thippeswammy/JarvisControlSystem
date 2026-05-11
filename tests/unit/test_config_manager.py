"""
tests/unit/test_config_manager.py
=====================================
Unit tests for jarvis.config.config_manager.ConfigManager.
"""
import pytest
import yaml
from pathlib import Path
from jarvis.config.config_manager import ConfigManager

pytestmark = pytest.mark.unit


@pytest.fixture
def cfg_file(tmp_path):
    """Write a minimal YAML config and return its path."""
    data = {
        "jarvis": {"input_mode": "text"},
        "llm": {"primary": "local"},
        "memory": {"db_path": "./memory/test.db"},
        "gateway": {"enabled": True},
        "channels": {
            "cli": {"enabled": True},
            "telegram": {"enabled": False, "token": "secret123"},
        },
    }
    p = tmp_path / "config.yaml"
    p.write_text(yaml.dump(data), encoding="utf-8")
    return str(p)


@pytest.fixture
def cfg(cfg_file):
    return ConfigManager(cfg_file)


# ── load ─────────────────────────────────────────────────────

def test_loads_yaml_correctly(cfg):
    assert cfg.get("jarvis.input_mode") == "text"


def test_missing_file_gives_empty_config(tmp_path):
    mgr = ConfigManager(str(tmp_path / "nonexistent.yaml"))
    assert mgr.get("any.key") is None


# ── get ───────────────────────────────────────────────────────

def test_get_nested_key(cfg):
    assert cfg.get("llm.primary") == "local"

def test_get_missing_key_returns_default(cfg):
    assert cfg.get("llm.nonexistent", "fallback") == "fallback"

def test_get_none_when_no_default(cfg):
    assert cfg.get("does.not.exist") is None


# ── set ───────────────────────────────────────────────────────

def test_set_existing_key(cfg):
    cfg.set("jarvis.input_mode", "voice")
    assert cfg.get("jarvis.input_mode") == "voice"

def test_set_new_nested_key(cfg):
    cfg.set("jarvis.new_section.key", "value")
    assert cfg.get("jarvis.new_section.key") == "value"

def test_set_converts_bool_string(cfg):
    cfg.set("gateway.enabled", "false")
    assert cfg.get("gateway.enabled") is False

def test_set_converts_int_string(cfg):
    cfg.set("jarvis.port", "8080")
    assert cfg.get("jarvis.port") == 8080

def test_set_persists_to_disk(cfg, cfg_file):
    cfg.set("jarvis.input_mode", "api")
    # Reload from disk
    cfg2 = ConfigManager(cfg_file)
    assert cfg2.get("jarvis.input_mode") == "api"


# ── unset ─────────────────────────────────────────────────────

def test_unset_removes_key(cfg):
    cfg.unset("jarvis.input_mode")
    assert cfg.get("jarvis.input_mode") is None

def test_unset_missing_key_returns_false(cfg):
    assert cfg.unset("does.not.exist") is False


# ── validate ─────────────────────────────────────────────────

def test_validate_passes_for_valid_config(cfg):
    issues = cfg.validate()
    assert issues == []

def test_validate_flags_missing_llm_primary(cfg):
    cfg.unset("llm.primary")
    issues = cfg.validate()
    assert any("llm.primary" in i for i in issues)

def test_validate_flags_missing_channels(cfg):
    cfg.unset("channels")
    issues = cfg.validate()
    assert any("channels" in i for i in issues)


# ── show (secret masking) ─────────────────────────────────────

def test_show_masks_telegram_token(cfg):
    shown = cfg.show(mask_secrets=True)
    assert shown["channels"]["telegram"]["token"] == "********"

def test_show_unmasked_reveals_token(cfg):
    shown = cfg.show(mask_secrets=False)
    assert shown["channels"]["telegram"]["token"] == "secret123"


# ── reload ───────────────────────────────────────────────────

def test_reload_picks_up_changes(cfg, cfg_file):
    # Directly edit the file
    with open(cfg_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    data["jarvis"]["input_mode"] = "reloaded"
    with open(cfg_file, "w", encoding="utf-8") as f:
        yaml.dump(data, f)

    cfg.load()  # reload
    assert cfg.get("jarvis.input_mode") == "reloaded"
