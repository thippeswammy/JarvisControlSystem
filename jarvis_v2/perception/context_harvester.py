"""
Context Harvester
=================
Extracts current system context: active app, window title, active graph node.
Used to populate ContextSnapshot in each pipeline cycle.

Generic implementation — no hardcoded app dict.
App identity is inferred from window title using fuzzy matching.
"""

import logging
import re
from typing import Optional

from jarvis_v2.perception.perception_packet import ContextSnapshot

logger = logging.getLogger(__name__)

# Title fragments → canonical app_id mapping (extendable)
_TITLE_TO_APP: list[tuple[re.Pattern, str]] = [
    (re.compile(r"settings", re.I),    "settings"),
    (re.compile(r"notepad", re.I),     "notepad"),
    (re.compile(r"chrome", re.I),      "chrome"),
    (re.compile(r"firefox", re.I),     "firefox"),
    (re.compile(r"edge", re.I),        "edge"),
    (re.compile(r"explorer", re.I),    "explorer"),
    (re.compile(r"word", re.I),        "word"),
    (re.compile(r"excel", re.I),       "excel"),
    (re.compile(r"powerpoint", re.I),  "powerpoint"),
    (re.compile(r"vs\s*code|visual studio code", re.I), "vscode"),
    (re.compile(r"task manager", re.I),"taskmanager"),
    (re.compile(r"control panel", re.I),"controlpanel"),
    (re.compile(r"cmd|command prompt", re.I), "cmd"),
    (re.compile(r"powershell", re.I),  "powershell"),
]


class ContextHarvester:
    """
    Captures the current Windows foreground window state.
    Returns a ContextSnapshot with app_id, title, and (optionally) state hash.

    Usage:
        harvester = ContextHarvester()
        snapshot = harvester.capture()
        # snapshot.active_app == "settings"
        # snapshot.active_window_title == "Display - Settings"
    """

    def __init__(self, state_harvester=None):
        self._state_harvester = state_harvester  # Optional StateHarvester for hash

    def capture(self) -> ContextSnapshot:
        """Capture current foreground window context."""
        title = self._get_foreground_title()
        app_id = self._infer_app_id(title)

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
        logger.debug(f"[ContextHarvester] Context: app={app_id!r}, title={title!r}")
        return snapshot

    def get_active_app(self) -> str:
        """Quick lookup: just the app_id of the current foreground window."""
        return self._infer_app_id(self._get_foreground_title())

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
    def _infer_app_id(title: str) -> str:
        if not title:
            return ""
        for pattern, app_id in _TITLE_TO_APP:
            if pattern.search(title):
                return app_id
        # Fallback: use first word of title, lowercased
        first_word = re.split(r"[\s\-–|]", title)[0].strip().lower()
        return first_word or "unknown"
