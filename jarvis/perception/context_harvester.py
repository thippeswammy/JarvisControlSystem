"""
Context Harvester
=================
Extracts current system context: active app, window title, active graph node.
Used to populate ContextSnapshot in each pipeline cycle.
Zero hardcoded mappings. App identity is fetched dynamically from the foreground window PID.
"""

import logging
import re
from typing import Optional

from jarvis.perception.perception_packet import ContextSnapshot
from jarvis.perception.ui_inspector import UIInspector

logger = logging.getLogger(__name__)

class ContextHarvester:
    """
    Captures the current Windows foreground window state.
    Returns a ContextSnapshot with app_id, title, and (optionally) state hash.
    """

    def __init__(self, state_harvester=None, episodic=None):
        self._state_harvester = state_harvester  # Optional StateHarvester for hash
        self._inspector = UIInspector()
        self._episodic = episodic                # For lineage query

    def capture(self) -> ContextSnapshot:
        """Capture current foreground window context."""
        title = self._get_foreground_title()
        app_id = self._get_foreground_app_id()

        state_hash = ""
        if self._state_harvester and app_id:
            try:
                _, state_hash = self._state_harvester.harvest_and_hash(app_title=app_id)
            except Exception as e:
                logger.debug(f"[ContextHarvester] State hash failed: {e}")

        snapshot = ContextSnapshot(
            active_app=app_id,
            active_window_title=title,
            screen_hash=state_hash,
        )

        # Delta Navigation Upgrades
        ui_snap = self._inspector.inspect(app_title=app_id)
        snapshot.ui_snapshot = ui_snap
        snapshot.state_sig = ui_snap.state_signature
        
        if self._episodic:
            lineage = self._episodic.get_lineage()
            if lineage:
                snapshot.state_origin = lineage.cause
                snapshot.prior_action = lineage.action
            else:
                snapshot.state_origin = "USER"
                snapshot.prior_action = "manually navigated"

        logger.debug(f"[ContextHarvester] Context: app={app_id!r}, title={title!r}, sig={snapshot.state_sig}")
        return snapshot

    def get_active_app(self) -> str:
        """Quick lookup: just the app_id of the current foreground window."""
        return self._get_foreground_app_id()

    # ── Private ──────────────────────────────────────

    @staticmethod
    def _get_foreground_title() -> str:
        try:
            import win32gui
            hwnd = win32gui.GetForegroundWindow()
            return win32gui.GetWindowText(hwnd) or ""
        except Exception:
            return ""

    @staticmethod
    def _get_foreground_app_id() -> str:
        try:
            import win32gui
            import win32process
            import psutil
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return ""
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc = psutil.Process(pid)
            name = proc.name().replace(".exe", "").lower()
            if "systemsettings" in name:
                return "settings"
            return name
        except Exception:
            return ""
