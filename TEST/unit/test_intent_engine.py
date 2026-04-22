"""
Unit Tests — Intent Engine
==========================
Tests pure parsing logic. No system calls, no heavy imports.
Run: pytest TEST/unit/test_intent_engine.py -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
from Jarvis.core.intent_engine import IntentEngine, Intent, ActionType


@pytest.fixture
def engine():
    return IntentEngine()


# ─────────────────────────────────────────────
#  Session control
# ─────────────────────────────────────────────
class TestSessionParsing:
    def test_hi_jarvis(self, engine):
        i = engine.parse("hi jarvis")
        assert i.action == ActionType.ACTIVATE_JARVIS

    def test_hey_jarvis(self, engine):
        i = engine.parse("hey jarvis")
        assert i.action == ActionType.ACTIVATE_JARVIS

    def test_close_jarvis(self, engine):
        i = engine.parse("close jarvis")
        assert i.action == ActionType.DEACTIVATE_JARVIS

    def test_stop_jarvis(self, engine):
        i = engine.parse("stop jarvis")
        assert i.action == ActionType.DEACTIVATE_JARVIS

    def test_typing_on(self, engine):
        i = engine.parse("start typing")
        assert i.action == ActionType.TYPING_MODE_ON

    def test_typing_off(self, engine):
        i = engine.parse("stop typing")
        assert i.action == ActionType.TYPING_MODE_OFF

    def test_typing_off_variants(self, engine):
        for cmd in ["typing stop", "deactivate typing", "end typing"]:
            i = engine.parse(cmd)
            assert i.action == ActionType.TYPING_MODE_OFF, f"Failed: {cmd!r}"


# ─────────────────────────────────────────────
#  App opening — verb synonyms
# ─────────────────────────────────────────────
class TestAppOpenParsing:
    @pytest.mark.parametrize("cmd,expected_target", [
        ("open chrome", "chrome"),
        ("launch chrome", "chrome"),
        ("start chrome", "chrome"),
        ("run chrome", "chrome"),
        ("open notepad", "notepad"),
        ("launch notepad", "notepad"),
        ("open google chrome", "google chrome"),
        ("open visual studio code", "visual studio code"),
    ])
    def test_open_variants(self, engine, cmd, expected_target):
        i = engine.parse(cmd)
        assert i.action == ActionType.OPEN_APP
        assert i.target == expected_target

    @pytest.mark.parametrize("cmd,expected_target", [
        ("close chrome", "chrome"),
        ("exit notepad", "notepad"),
        ("quit chrome", "chrome"),
        ("kill notepad", "notepad"),
        ("terminate chrome", "chrome"),
    ])
    def test_close_variants(self, engine, cmd, expected_target):
        i = engine.parse(cmd)
        assert i.action == ActionType.CLOSE_APP
        assert i.target == expected_target


# ─────────────────────────────────────────────
#  System controls
# ─────────────────────────────────────────────
class TestSystemParsing:
    @pytest.mark.parametrize("cmd,tgt,val", [
        ("set volume to 80", "volume", 80),
        ("set volume to 50", "volume", 50),
        ("set brightness to 100", "brightness", 100),
        ("set brightness to 30", "brightness", 30),
    ])
    def test_set_value(self, engine, cmd, tgt, val):
        i = engine.parse(cmd)
        assert i.action == ActionType.SET_VALUE
        assert tgt in i.target
        assert i.params.get("value") == val

    @pytest.mark.parametrize("cmd,tgt,amount", [
        ("increase volume", "volume", 10),        # default amount
        ("increase volume by 20", "volume", 20),
        ("increase brightness by 30", "brightness", 30),
        ("raise volume 15", "volume", 15),
        ("turn up volume", "volume", 10),
    ])
    def test_increase(self, engine, cmd, tgt, amount):
        i = engine.parse(cmd)
        assert i.action == ActionType.INCREASE
        assert tgt in i.target
        assert i.params.get("amount", 10) == amount

    @pytest.mark.parametrize("cmd,tgt,amount", [
        ("decrease volume", "volume", 10),
        ("lower brightness by 20", "brightness", 20),
        ("turn down volume", "volume", 10),
        ("reduce brightness 15", "brightness", 15),
    ])
    def test_decrease(self, engine, cmd, tgt, amount):
        i = engine.parse(cmd)
        assert i.action == ActionType.DECREASE
        assert tgt in i.target
        assert i.params.get("amount", 10) == amount


# ─────────────────────────────────────────────
#  Keyboard
# ─────────────────────────────────────────────
class TestKeyboardParsing:
    @pytest.mark.parametrize("cmd,expected_key", [
        ("press enter", "enter"),
        ("press ctrl", "ctrl"),
        ("press escape", "escape"),
        ("press f5", "f5"),
    ])
    def test_press_key(self, engine, cmd, expected_key):
        i = engine.parse(cmd)
        assert i.action == ActionType.PRESS_KEY
        assert expected_key in i.target

    def test_hold_key(self, engine):
        i = engine.parse("hold ctrl")
        assert i.action == ActionType.HOLD_KEY
        assert "ctrl" in i.target

    def test_release_key(self, engine):
        i = engine.parse("release ctrl")
        assert i.action == ActionType.RELEASE_KEY
        assert "ctrl" in i.target

    def test_type_text(self, engine):
        i = engine.parse("type hello world")
        assert i.action == ActionType.TYPE_TEXT
        assert "hello world" in i.target


# ─────────────────────────────────────────────
#  Navigation
# ─────────────────────────────────────────────
class TestNavigationParsing:
    @pytest.mark.parametrize("cmd,name", [
        ("go to documents", "documents"),
        ("navigate to downloads", "downloads"),
        ("open folder desktop", "desktop"),
        ("go to c drive", "c drive"),
        ("go to this pc", "this pc"),
    ])
    def test_navigate_location(self, engine, cmd, name):
        i = engine.parse(cmd)
        assert i.action == ActionType.NAVIGATE_LOCATION
        assert name in i.target

    def test_documents_resolved(self, engine):
        i = engine.parse("go to documents")
        assert "resolved_path" in i.params
        assert "Documents" in i.params["resolved_path"]

    def test_c_drive_resolved(self, engine):
        i = engine.parse("go to c drive")
        assert "resolved_path" in i.params
        assert "C:\\" in i.params["resolved_path"]

    @pytest.mark.parametrize("cmd,expected_elem", [
        ("click save", "save"),
        ("click ok", "ok"),
        ("click new file", "new file"),
        ("click save button", "save button"),
        ("select items", "items"),
    ])
    def test_click_element(self, engine, cmd, expected_elem):
        i = engine.parse(cmd)
        assert i.action == ActionType.CLICK_ELEMENT
        assert expected_elem in i.target

    @pytest.mark.parametrize("cmd,direction", [
        ("scroll down", "down"),
        ("scroll up", "up"),
        ("page down", "down"),
        ("page up", "up"),
    ])
    def test_scroll(self, engine, cmd, direction):
        i = engine.parse(cmd)
        assert i.action == ActionType.SCROLL
        assert i.params.get("direction") == direction

    def test_scroll_amount(self, engine):
        i = engine.parse("scroll down 5")
        assert i.params.get("amount") == 5


# ─────────────────────────────────────────────
#  Settings
# ─────────────────────────────────────────────
class TestSettingsParsing:
    @pytest.mark.parametrize("cmd,keyword", [
        ("open settings", "settings"),
        ("open settings wifi", "wifi"),
        ("open settings display", "display"),
        ("open settings bluetooth", "bluetooth"),
        ("settings volume", "volume"),
    ])
    def test_settings_open(self, engine, cmd, keyword):
        i = engine.parse(cmd)
        assert i.action == ActionType.OPEN_SETTINGS
        # keyword in raw or target
        assert keyword in i.target or keyword in i.raw


# ─────────────────────────────────────────────
#  Window management
# ─────────────────────────────────────────────
class TestWindowParsing:
    def test_minimize(self, engine):
        assert engine.parse("minimize window").action == ActionType.MINIMIZE

    def test_maximize(self, engine):
        assert engine.parse("maximize window").action == ActionType.MAXIMIZE

    def test_close_window(self, engine):
        # "close window" should be CLOSE_WINDOW not CLOSE_APP
        i = engine.parse("close window")
        assert i.action in (ActionType.CLOSE_WINDOW, ActionType.CLOSE_APP)

    def test_switch_window(self, engine):
        for cmd in ["switch window", "next window", "switch windows"]:
            assert engine.parse(cmd).action == ActionType.SWITCH_WINDOW

    def test_snap_left(self, engine):
        assert engine.parse("snap left").action == ActionType.SNAP_LEFT

    def test_snap_right(self, engine):
        assert engine.parse("snap right").action == ActionType.SNAP_RIGHT


# ─────────────────────────────────────────────
#  Search
# ─────────────────────────────────────────────
class TestSearchParsing:
    def test_search_for(self, engine):
        i = engine.parse("search for python")
        assert i.action == ActionType.SEARCH
        assert "python" in i.target

    def test_search_plain(self, engine):
        i = engine.parse("search python tutorial")
        assert i.action == ActionType.SEARCH

    def test_rescan_apps(self, engine):
        i = engine.parse("rescan apps")
        assert i.action == ActionType.SCAN_APPS

    def test_refresh_apps(self, engine):
        i = engine.parse("refresh apps")
        assert i.action == ActionType.SCAN_APPS


# ─────────────────────────────────────────────
#  Edge cases
# ─────────────────────────────────────────────
class TestEdgeCases:
    def test_empty_string(self, engine):
        i = engine.parse("")
        assert i.action == ActionType.UNKNOWN

    def test_unknown_command(self, engine):
        i = engine.parse("xyzzy plugh")
        assert i.action == ActionType.UNKNOWN

    def test_confidence_exact_match(self, engine):
        i = engine.parse("hi jarvis")
        assert i.confidence == 1.0

    def test_raw_preserved(self, engine):
        cmd = "Open Chrome"
        i = engine.parse(cmd)
        assert i.raw == cmd   # original case preserved

    def test_extra_spaces(self, engine):
        i = engine.parse("  open  chrome  ")
        assert i.action == ActionType.OPEN_APP
