"""
tests/unit/test_context_harvester.py
=====================================
Unit tests for jarvis.perception.context_harvester.ContextHarvester.

UIInspector is patched at the point ContextHarvester imports it (so no real
pywinauto/UIA hooks are touched), and the private win32-backed static
helpers (_get_foreground_title / _get_foreground_app_id) are patched or
exercised directly against a mocked win32gui/win32process/psutil boundary.
"""
import pytest
from unittest.mock import MagicMock, patch

from jarvis.perception.context_harvester import ContextHarvester
from jarvis.perception.perception_packet import ContextSnapshot
from jarvis.perception.ui_inspector import UISnapshot

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_inspector():
    """Patches the UIInspector class as imported into context_harvester."""
    with patch("jarvis.perception.context_harvester.UIInspector") as MockCls:
        instance = MagicMock()
        MockCls.return_value = instance
        yield instance


@pytest.fixture
def harvester(mock_inspector):
    """A ContextHarvester with UIInspector mocked and foreground lookups
    pinned to deterministic values (no real UI/win32 interaction)."""
    with patch.object(ContextHarvester, "_get_foreground_title", return_value="Untitled - Notepad"), \
         patch.object(ContextHarvester, "_get_foreground_app_id", return_value="notepad"):
        yield ContextHarvester()


# ── capture(): normal shape ──────────────────────────────

def test_capture_returns_context_snapshot_with_expected_shape(harvester, mock_inspector):
    ui_snap = UISnapshot(active_app="notepad", page_title="Untitled - Notepad", state_signature="abc123")
    mock_inspector.inspect.return_value = ui_snap

    snapshot = harvester.capture()

    assert isinstance(snapshot, ContextSnapshot)
    assert snapshot.active_app == "notepad"
    assert snapshot.active_window_title == "Untitled - Notepad"
    assert snapshot.ui_snapshot is ui_snap
    assert snapshot.state_sig == "abc123"
    mock_inspector.inspect.assert_called_once_with(app_title="notepad")


def test_capture_without_state_harvester_leaves_screen_hash_empty(harvester, mock_inspector):
    mock_inspector.inspect.return_value = UISnapshot()
    snapshot = harvester.capture()
    assert snapshot.screen_hash == ""


def test_get_active_app_returns_foreground_app_id(harvester):
    assert harvester.get_active_app() == "notepad"


# ── capture(): state_harvester integration ───────────────

def test_capture_uses_state_harvester_hash_when_available(mock_inspector):
    mock_state_harvester = MagicMock()
    mock_state_harvester.harvest_and_hash.return_value = (None, "deadbeef")

    with patch.object(ContextHarvester, "_get_foreground_title", return_value="Notepad"), \
         patch.object(ContextHarvester, "_get_foreground_app_id", return_value="notepad"):
        h = ContextHarvester(state_harvester=mock_state_harvester)
        mock_inspector.inspect.return_value = UISnapshot()
        snapshot = h.capture()

    assert snapshot.screen_hash == "deadbeef"
    mock_state_harvester.harvest_and_hash.assert_called_once_with(app_title="notepad")


def test_capture_swallows_state_harvester_exception(mock_inspector):
    """The state_harvester call IS guarded by try/except -- a failure there
    must not propagate and must leave screen_hash empty."""
    mock_state_harvester = MagicMock()
    mock_state_harvester.harvest_and_hash.side_effect = RuntimeError("boom")

    with patch.object(ContextHarvester, "_get_foreground_title", return_value="Notepad"), \
         patch.object(ContextHarvester, "_get_foreground_app_id", return_value="notepad"):
        h = ContextHarvester(state_harvester=mock_state_harvester)
        mock_inspector.inspect.return_value = UISnapshot()
        snapshot = h.capture()  # must not raise

    assert snapshot.screen_hash == ""


def test_capture_skips_state_harvester_when_app_id_is_empty(mock_inspector):
    """capture() only calls the state harvester `if self._state_harvester and app_id`;
    an empty foreground app_id must short-circuit the call."""
    mock_state_harvester = MagicMock()

    with patch.object(ContextHarvester, "_get_foreground_title", return_value=""), \
         patch.object(ContextHarvester, "_get_foreground_app_id", return_value=""):
        h = ContextHarvester(state_harvester=mock_state_harvester)
        mock_inspector.inspect.return_value = UISnapshot()
        snapshot = h.capture()

    mock_state_harvester.harvest_and_hash.assert_not_called()
    assert snapshot.screen_hash == ""


# ── capture(): UIInspector failure / stale data (production-code gap) ──

def test_capture_propagates_ui_inspector_exception(harvester, mock_inspector):
    """GAP: unlike the state_harvester call, the `self._inspector.inspect(...)`
    call in capture() is NOT wrapped in a try/except. An exception raised by
    UIInspector therefore propagates straight out of capture() and crashes
    the harvest cycle instead of degrading gracefully. This test documents
    that real (unguarded) behavior rather than forcing a graceful fallback
    that the code doesn't implement."""
    mock_inspector.inspect.side_effect = RuntimeError("uia crashed")

    with pytest.raises(RuntimeError, match="uia crashed"):
        harvester.capture()


def test_capture_with_empty_ui_snapshot_still_populates_state_sig(harvester, mock_inspector):
    """When UIInspector reports stale/empty data (is_empty=True), capture()
    still wires it through as-is -- no special handling for staleness."""
    empty_snap = UISnapshot(is_empty=True, state_signature="")
    mock_inspector.inspect.return_value = empty_snap

    snapshot = harvester.capture()

    assert snapshot.ui_snapshot is empty_snap
    assert snapshot.ui_snapshot.is_empty is True
    assert snapshot.state_sig == ""


# ── capture(): episodic lineage ──────────────────────────

def test_capture_sets_lineage_from_episodic_when_present(mock_inspector):
    mock_episodic = MagicMock()
    lineage = MagicMock(cause="JARVIS", action="opened notepad")
    mock_episodic.get_lineage.return_value = lineage

    with patch.object(ContextHarvester, "_get_foreground_title", return_value="Notepad"), \
         patch.object(ContextHarvester, "_get_foreground_app_id", return_value="notepad"):
        h = ContextHarvester(episodic=mock_episodic)
        mock_inspector.inspect.return_value = UISnapshot()
        snapshot = h.capture()

    assert snapshot.state_origin == "JARVIS"
    assert snapshot.prior_action == "opened notepad"


def test_capture_defaults_lineage_to_user_when_episodic_has_none(mock_inspector):
    mock_episodic = MagicMock()
    mock_episodic.get_lineage.return_value = None

    with patch.object(ContextHarvester, "_get_foreground_title", return_value="Notepad"), \
         patch.object(ContextHarvester, "_get_foreground_app_id", return_value="notepad"):
        h = ContextHarvester(episodic=mock_episodic)
        mock_inspector.inspect.return_value = UISnapshot()
        snapshot = h.capture()

    assert snapshot.state_origin == "USER"
    assert snapshot.prior_action == "manually navigated"


def test_capture_leaves_lineage_unset_without_episodic(harvester, mock_inspector):
    mock_inspector.inspect.return_value = UISnapshot()
    snapshot = harvester.capture()
    assert snapshot.state_origin == ""
    assert snapshot.prior_action == ""


# ── private static helpers: win32 boundary ───────────────

def test_get_foreground_app_id_maps_systemsettings_to_settings():
    with patch("win32gui.GetForegroundWindow", return_value=12345), \
         patch("win32process.GetWindowThreadProcessId", return_value=(0, 999)), \
         patch("psutil.Process") as MockProcess:
        MockProcess.return_value.name.return_value = "SystemSettings.exe"
        app_id = ContextHarvester._get_foreground_app_id()
    assert app_id == "settings"


def test_get_foreground_app_id_strips_lowercase_exe_suffix():
    with patch("win32gui.GetForegroundWindow", return_value=12345), \
         patch("win32process.GetWindowThreadProcessId", return_value=(0, 999)), \
         patch("psutil.Process") as MockProcess:
        MockProcess.return_value.name.return_value = "notepad.exe"
        app_id = ContextHarvester._get_foreground_app_id()
    assert app_id == "notepad"


def test_get_foreground_app_id_does_not_strip_uppercase_exe_suffix():
    """GAP: `proc.name().replace(".exe", "").lower()` replaces the literal
    lowercase substring ".exe" BEFORE lowercasing the name. A process name
    reported with an uppercase extension (e.g. ".EXE", which psutil can
    return on some Windows configurations) therefore is NOT stripped, and
    app_id ends up as "notepad.exe" instead of "notepad". This documents
    the actual (buggy) behavior rather than the presumably-intended one."""
    with patch("win32gui.GetForegroundWindow", return_value=12345), \
         patch("win32process.GetWindowThreadProcessId", return_value=(0, 999)), \
         patch("psutil.Process") as MockProcess:
        MockProcess.return_value.name.return_value = "Notepad.EXE"
        app_id = ContextHarvester._get_foreground_app_id()
    assert app_id == "notepad.exe"


def test_get_foreground_app_id_returns_empty_on_exception():
    with patch("win32gui.GetForegroundWindow", side_effect=RuntimeError("no window")):
        app_id = ContextHarvester._get_foreground_app_id()
    assert app_id == ""


def test_get_foreground_app_id_returns_empty_when_no_hwnd():
    with patch("win32gui.GetForegroundWindow", return_value=0):
        app_id = ContextHarvester._get_foreground_app_id()
    assert app_id == ""


def test_get_foreground_title_returns_window_text():
    with patch("win32gui.GetForegroundWindow", return_value=555), \
         patch("win32gui.GetWindowText", return_value="My Window"):
        title = ContextHarvester._get_foreground_title()
    assert title == "My Window"


def test_get_foreground_title_returns_empty_on_exception():
    with patch("win32gui.GetForegroundWindow", side_effect=RuntimeError("fail")):
        title = ContextHarvester._get_foreground_title()
    assert title == ""
