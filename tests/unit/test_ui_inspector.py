"""
tests/unit/test_ui_inspector.py
=====================================
Unit tests for jarvis.perception.ui_inspector.UISnapshot and UIInspector.

pywinauto/win32gui/win32process/psutil are real, importable packages in this
environment, so `UIInspector._check_uia()` would normally succeed. To keep
these tests hermetic (no real desktop/UIA interaction) every test that
exercises `_harvest_ui` patches `pywinauto.Desktop`, `win32gui.*`,
`win32process.*` and `psutil.Process` at their boundary, and/or forces
`_uia_available` directly rather than depending on the host's real UI state.
"""
import hashlib

import pytest
from unittest.mock import MagicMock, patch

from jarvis.perception.ui_inspector import UISnapshot, UIInspector

pytestmark = pytest.mark.unit


def _make_ctrl(control_type, name):
    ctrl = MagicMock()
    ctrl.element_info.control_type = control_type
    ctrl.element_info.name = name
    return ctrl


# ── UISnapshot: defaults & equality ──────────────────────

def test_uisnapshot_defaults():
    snap = UISnapshot()
    assert snap.active_app == ""
    assert snap.page_title == ""
    assert snap.nav_items == []
    assert snap.visible_buttons == []
    assert snap.active_section == ""
    assert snap.state_signature == ""
    assert snap.is_empty is False


def test_uisnapshot_equality_is_field_based():
    a = UISnapshot(active_app="notepad", page_title="Untitled", state_signature="abc")
    b = UISnapshot(active_app="notepad", page_title="Untitled", state_signature="abc")
    c = UISnapshot(active_app="chrome", page_title="Untitled", state_signature="abc")
    assert a == b
    assert a != c


def test_uisnapshot_independent_nav_item_lists():
    """default_factory=list must give each instance its own list, not a
    shared mutable default."""
    a = UISnapshot()
    b = UISnapshot()
    a.nav_items.append("File")
    assert b.nav_items == []


# ── UISnapshot.to_llm_context() ──────────────────────────

def test_to_llm_context_when_empty():
    snap = UISnapshot(is_empty=True)
    assert snap.to_llm_context() == "UI State: Unknown (No data harvested)"


def test_to_llm_context_basic_fields():
    snap = UISnapshot(active_app="notepad", page_title="Untitled - Notepad")
    assert snap.to_llm_context() == "Active App: notepad | Current Page: Untitled - Notepad"


def test_to_llm_context_includes_section_nav_and_buttons():
    snap = UISnapshot(
        active_app="settings",
        page_title="Settings",
        active_section="Display",
        nav_items=["Display", "Sound", "Network"],
        visible_buttons=["Apply", "Cancel"],
    )
    ctx = snap.to_llm_context()
    assert "Active Section: Display" in ctx
    assert "Navigation Menu: [Display, Sound, Network]" in ctx
    assert "Visible Buttons: [Apply, Cancel]" in ctx


def test_to_llm_context_truncates_nav_items_to_twelve():
    nav = [f"Item{i}" for i in range(20)]
    snap = UISnapshot(active_app="a", page_title="p", nav_items=nav)
    ctx = snap.to_llm_context()
    assert f"[{', '.join(nav[:12])}]" in ctx
    assert "Item12" not in ctx  # 13th item (0-indexed) must be excluded


def test_to_llm_context_truncates_visible_buttons_to_ten():
    buttons = [f"Btn{i}" for i in range(15)]
    snap = UISnapshot(active_app="a", page_title="p", visible_buttons=buttons)
    ctx = snap.to_llm_context()
    assert f"[{', '.join(buttons[:10])}]" in ctx
    assert "Btn10" not in ctx


# ── UIInspector._check_uia ────────────────────────────────

def test_check_uia_true_when_imports_succeed():
    inspector = UIInspector()
    assert inspector._uia_available is True


def test_check_uia_false_when_pywinauto_import_fails():
    import sys
    with patch.dict(sys.modules, {"pywinauto": None}):
        inspector = UIInspector()
    assert inspector._uia_available is False


# ── UIInspector.inspect(): unavailable / failure paths ───

def test_inspect_returns_empty_snapshot_when_uia_unavailable():
    inspector = UIInspector()
    inspector._uia_available = False
    snap = inspector.inspect()
    assert snap.is_empty is True


def test_inspect_returns_empty_snapshot_on_harvest_exception():
    """GAP-adjacent: _harvest_ui failures ARE caught here (unlike
    ContextHarvester.capture(), which does not guard its UIInspector call)."""
    inspector = UIInspector()
    inspector._uia_available = True
    with patch.object(inspector, "_harvest_ui", side_effect=RuntimeError("boom")):
        snap = inspector.inspect(app_title="notepad")
    assert snap.is_empty is True


# ── UIInspector._harvest_ui via inspect(): foreground window ─

def test_harvest_ui_foreground_window_builds_expected_snapshot():
    fake_win = MagicMock()
    fake_win.window_text.return_value = "Untitled - Notepad"
    fake_win.handle = 4242
    fake_win.descendants.return_value = [
        _make_ctrl("MenuItem", "File"),
        _make_ctrl("MenuItem", "File"),   # duplicate -> must be deduped
        _make_ctrl("Button", "Save"),
        _make_ctrl("Text", "Ready"),
        _make_ctrl("ListItem", "Clock"),  # noise -> filtered out entirely
        _make_ctrl("Text", "x"),          # too short (<2 chars) -> filtered
    ]
    fake_desktop = MagicMock()
    fake_desktop.window.return_value = fake_win

    with patch("pywinauto.Desktop", return_value=fake_desktop), \
         patch("win32gui.GetForegroundWindow", return_value=4242), \
         patch("win32gui.GetWindowText", return_value="Untitled - Notepad"), \
         patch("win32process.GetWindowThreadProcessId", return_value=(0, 111)), \
         patch("psutil.Process") as MockProcess:
        MockProcess.return_value.name.return_value = "notepad.exe"

        inspector = UIInspector()
        inspector._uia_available = True
        snap = inspector.inspect()

    assert snap.is_empty is False
    assert snap.active_app == "notepad"
    assert snap.page_title == "Untitled - Notepad"
    assert snap.nav_items == ["File"]
    assert snap.visible_buttons == ["Save"]
    assert snap.active_section == "Ready"

    expected_sig = hashlib.sha256(b"notepad|Untitled - Notepad|File").hexdigest()[:12]
    assert snap.state_signature == expected_sig


def test_harvest_ui_no_foreground_title_returns_empty():
    fake_desktop = MagicMock()
    with patch("pywinauto.Desktop", return_value=fake_desktop), \
         patch("win32gui.GetForegroundWindow", return_value=0), \
         patch("win32gui.GetWindowText", return_value=""):
        inspector = UIInspector()
        inspector._uia_available = True
        snap = inspector.inspect()
    assert snap.is_empty is True


def test_harvest_ui_falls_back_to_title_based_app_id_on_process_lookup_failure():
    fake_win = MagicMock()
    fake_win.window_text.return_value = "Untitled - Notepad"
    fake_win.handle = 111
    fake_win.descendants.return_value = []
    fake_desktop = MagicMock()
    fake_desktop.window.return_value = fake_win

    with patch("pywinauto.Desktop", return_value=fake_desktop), \
         patch("win32gui.GetForegroundWindow", return_value=111), \
         patch("win32gui.GetWindowText", return_value="Untitled - Notepad"), \
         patch("win32process.GetWindowThreadProcessId", side_effect=RuntimeError("no proc")):
        inspector = UIInspector()
        inspector._uia_available = True
        snap = inspector.inspect()

    assert snap.is_empty is False
    assert snap.active_app == "notepad"  # via _infer_app_id_fallback


def test_harvest_ui_continues_when_descendant_walk_raises():
    """The descendant walk is wrapped in its own try/except inside
    _harvest_ui; a failure there must not make the whole snapshot empty --
    it should just yield no nav_items/buttons."""
    fake_win = MagicMock()
    fake_win.window_text.return_value = "Page"
    fake_win.handle = 1
    fake_win.descendants.side_effect = RuntimeError("walk failed")
    fake_desktop = MagicMock()
    fake_desktop.window.return_value = fake_win

    with patch("pywinauto.Desktop", return_value=fake_desktop), \
         patch("win32gui.GetForegroundWindow", return_value=1), \
         patch("win32gui.GetWindowText", return_value="Page"), \
         patch("win32process.GetWindowThreadProcessId", return_value=(0, 1)), \
         patch("psutil.Process") as MockProcess:
        MockProcess.return_value.name.return_value = "app.exe"
        inspector = UIInspector()
        inspector._uia_available = True
        snap = inspector.inspect()

    assert snap.is_empty is False
    assert snap.active_app == "app"
    assert snap.nav_items == []
    assert snap.visible_buttons == []


def test_state_signature_is_order_independent_for_nav_items():
    """state_signature sorts nav_items before hashing, so harvesting the
    same set of items in a different order must produce the same
    signature -- this is the 'stable state ID' the module promises."""
    fake_desktop = MagicMock()

    def run(order):
        fake_win = MagicMock()
        fake_win.window_text.return_value = "Page"
        fake_win.handle = 1
        fake_win.descendants.return_value = [_make_ctrl("MenuItem", n) for n in order]
        fake_desktop.window.return_value = fake_win
        with patch("pywinauto.Desktop", return_value=fake_desktop), \
             patch("win32gui.GetForegroundWindow", return_value=1), \
             patch("win32gui.GetWindowText", return_value="Page"), \
             patch("win32process.GetWindowThreadProcessId", return_value=(0, 1)), \
             patch("psutil.Process") as MockProcess:
            MockProcess.return_value.name.return_value = "app.exe"
            inspector = UIInspector()
            inspector._uia_available = True
            return inspector.inspect()

    snap1 = run(["Beta", "Alpha", "Gamma"])
    snap2 = run(["Gamma", "Alpha", "Beta"])
    assert snap1.state_signature == snap2.state_signature
    assert snap1.state_signature != ""


def test_state_signature_changes_with_different_page():
    fake_desktop = MagicMock()

    def run(page_title):
        fake_win = MagicMock()
        fake_win.window_text.return_value = page_title
        fake_win.handle = 1
        fake_win.descendants.return_value = []
        fake_desktop.window.return_value = fake_win
        with patch("pywinauto.Desktop", return_value=fake_desktop), \
             patch("win32gui.GetForegroundWindow", return_value=1), \
             patch("win32gui.GetWindowText", return_value=page_title), \
             patch("win32process.GetWindowThreadProcessId", return_value=(0, 1)), \
             patch("psutil.Process") as MockProcess:
            MockProcess.return_value.name.return_value = "app.exe"
            inspector = UIInspector()
            inspector._uia_available = True
            return inspector.inspect()

    snap1 = run("Page One")
    snap2 = run("Page Two")
    assert snap1.state_signature != snap2.state_signature


# ── UIInspector.inspect(app_title=...): explicit target window ─

def test_harvest_ui_app_title_not_found_returns_empty():
    fake_win = MagicMock()
    fake_win.exists.return_value = False
    fake_desktop = MagicMock()
    fake_desktop.window.return_value = fake_win

    with patch("pywinauto.Desktop", return_value=fake_desktop):
        inspector = UIInspector()
        inspector._uia_available = True
        snap = inspector.inspect(app_title="chrome")

    assert snap.is_empty is True


def test_harvest_ui_app_title_lookup_raises_returns_empty():
    fake_desktop = MagicMock()
    fake_desktop.window.side_effect = RuntimeError("not found")

    with patch("pywinauto.Desktop", return_value=fake_desktop):
        inspector = UIInspector()
        inspector._uia_available = True
        snap = inspector.inspect(app_title="chrome")

    assert snap.is_empty is True


# ── UIInspector._infer_app_id_fallback ───────────────────

def test_infer_app_id_fallback_matches_known_apps():
    assert UIInspector._infer_app_id_fallback("Settings") == "settings"
    assert UIInspector._infer_app_id_fallback("Untitled - Notepad") == "notepad"
    assert UIInspector._infer_app_id_fallback("New Tab - Google Chrome") == "chrome"
    assert UIInspector._infer_app_id_fallback("Documents - File Explorer") == "explorer"


def test_infer_app_id_fallback_splits_on_dash_when_unknown():
    assert UIInspector._infer_app_id_fallback("MyApp - Custom Window") == "custom window"


def test_infer_app_id_fallback_uses_first_word_when_no_dash():
    assert UIInspector._infer_app_id_fallback("SomeStandaloneApp") == "somestandaloneapp"
