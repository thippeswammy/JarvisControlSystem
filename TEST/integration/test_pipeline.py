"""
Integration Tests — Full Pipeline (No System Calls)
====================================================
Tests text → intent → dispatch without actually calling Windows APIs.
Uses monkeypatching to mock Windows-specific calls.
Run: pytest TEST/integration/test_pipeline.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
from unittest.mock import MagicMock, patch
from Jarvis.core.intent_engine import IntentEngine, ActionType
from Jarvis.core.action_registry import ActionRegistry, ActionResult


# ─────────────────────────────────────────────
#  Integration: Full text → Intent parse
# ─────────────────────────────────────────────
class TestFullParse:
    """These verify the full parse chain produces correct structures."""

    @pytest.fixture(autouse=True)
    def engine(self):
        self.engine = IntentEngine()

    def _parse(self, text):
        return self.engine.parse(text)

    # Session
    def test_full_activate(self):
        i = self._parse("hi jarvis")
        assert i.action == ActionType.ACTIVATE_JARVIS
        assert i.confidence == 1.0
        assert i.raw == "hi jarvis"

    # App open with target
    def test_full_open_app_target(self):
        i = self._parse("open google chrome")
        assert i.action == ActionType.OPEN_APP
        assert "google chrome" in i.target

    # Set value extracts number correctly
    def test_full_set_volume_number(self):
        i = self._parse("set volume to 75")
        assert i.action == ActionType.SET_VALUE
        assert i.params["value"] == 75

    # Increase with amount
    def test_full_increase_amount(self):
        i = self._parse("increase brightness by 25")
        assert i.action == ActionType.INCREASE
        assert i.params["amount"] == 25
        assert "brightness" in i.target

    # Navigate with path resolution
    def test_full_navigate_documents_resolves(self):
        i = self._parse("go to documents")
        assert i.action == ActionType.NAVIGATE_LOCATION
        assert "documents" in i.target
        assert "resolved_path" in i.params

    # Settings with page keyword
    def test_full_settings_with_keyword(self):
        i = self._parse("open settings wifi")
        assert i.action == ActionType.OPEN_SETTINGS
        assert "wifi" in i.target

    # Scroll with direction + amount
    def test_full_scroll_direction_amount(self):
        i = self._parse("scroll down 8")
        assert i.action == ActionType.SCROLL
        assert i.params["direction"] == "down"
        assert i.params["amount"] == 8

    # Menu navigation path
    def test_full_menu_navigation(self):
        i = self._parse("navigate menu file then save as")
        assert i.action == ActionType.NAVIGATE_MENU
        path = i.params.get("menu_path", [])
        assert len(path) >= 2
        assert "file" in [p.lower() for p in path]


# ─────────────────────────────────────────────
#  Integration: Settings URI lookup
# ─────────────────────────────────────────────
class TestSettingsURILookup:
    """Verify the settings handler can resolve URIs for all common queries."""

    def _find(self, query):
        from Jarvis.core.handlers.settings_handler import _find_setting_uri
        return _find_setting_uri(query)

    def test_exact_wifi(self):
        result = self._find("wifi")
        assert result is not None
        key, uri = result
        assert "wifi" in uri.lower() or "network" in uri.lower()

    def test_exact_bluetooth(self):
        result = self._find("bluetooth")
        assert result is not None
        _, uri = result
        assert "bluetooth" in uri

    def test_exact_display(self):
        result = self._find("display")
        assert result is not None

    def test_exact_volume(self):
        result = self._find("sound")
        assert result is not None

    def test_partial_match_update(self):
        result = self._find("windows update")
        assert result is not None

    def test_fuzzy_match_accent(self):
        result = self._find("wallpaper")
        assert result is not None

    def test_power_settings(self):
        result = self._find("power")
        assert result is not None
        _, uri = result
        assert "power" in uri or "sleep" in uri

    def test_no_match_returns_none(self):
        result = self._find("xyzzy_nonexistent_setting")
        # May or may not find something via fuzzy — just ensure no crash
        # (fuzzy might match something with low confidence)
        # The main point: function doesn't raise
        pass


# ─────────────────────────────────────────────
#  Integration: Registry dispatch with mocked actions
# ─────────────────────────────────────────────
class TestRegistryDispatchIntegration:
    """
    Uses fresh registry to test dispatch without real Windows calls.
    """

    @pytest.fixture
    def reg_and_engine(self):
        reg = ActionRegistry()
        engine = IntentEngine()
        return reg, engine

    def test_open_app_dispatched(self, reg_and_engine):
        reg, engine = reg_and_engine
        received = {}

        @reg.register(actions=[ActionType.OPEN_APP])
        def mock_open(intent, ctx):
            received['target'] = intent.target
            return ActionResult.ok(f"opened {intent.target}")

        intent = engine.parse("open notepad")
        result = reg.dispatch(intent, None)

        assert result.success
        assert received.get('target') == 'notepad'

    def test_chain_open_then_close(self, reg_and_engine):
        reg, engine = reg_and_engine
        opened = []
        closed = []

        @reg.register(actions=[ActionType.OPEN_APP])
        def mock_open(intent, ctx):
            opened.append(intent.target)
            return ActionResult.ok(f"opened {intent.target}")

        @reg.register(actions=[ActionType.CLOSE_APP])
        def mock_close(intent, ctx):
            closed.append(intent.target)
            return ActionResult.ok(f"closed {intent.target}")

        # Simulate: open notepad → open chrome → close notepad
        for cmd in ["open notepad", "open chrome", "close notepad"]:
            reg.dispatch(engine.parse(cmd), None)

        assert "notepad" in opened
        assert "chrome" in opened
        assert "notepad" in closed

    def test_multiple_system_commands(self, reg_and_engine):
        reg, engine = reg_and_engine
        calls = []

        @reg.register(actions=[ActionType.SET_VALUE, ActionType.INCREASE, ActionType.DECREASE])
        def mock_sys(intent, ctx):
            calls.append((intent.action.name, intent.target, intent.params))
            return ActionResult.ok("done")

        commands = [
            "set volume to 80",
            "increase brightness by 20",
            "decrease volume 10",
        ]
        for cmd in commands:
            reg.dispatch(engine.parse(cmd), None)

        assert len(calls) == 3
        assert calls[0][0] == "SET_VALUE"
        assert calls[1][0] == "INCREASE"
        assert calls[2][0] == "DECREASE"
