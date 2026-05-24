"""
Conversation State Manager & Window Focus Controller
===================================================
Tracks active desktop applications, handles window handles (hwnd), minimized status,
and provides robust window reuse/focus methods using pywinauto and win32gui.
"""

import logging
import sys
import time
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Canonical synonym mapping
CANONICAL_APPS = {
    "notepad": "notepad",
    "notebook": "notepad",
    "calculator": "calculator",
    "paint": "paint",
    "wordpad": "wordpad",
    "cmd": "cmd",
    "command prompt": "cmd",
    "powershell": "powershell",
    "explorer": "explorer",
    "file explorer": "explorer",
    "this pc": "explorer",
    "edge": "edge",
    "chrome": "chrome",
    "firefox": "firefox",
    "settings": "settings",
    "windows settings": "settings",
    "control panel": "controlpanel",
    "task manager": "taskmanager",
    "word": "word",
    "excel": "excel",
    "powerpoint": "powerpoint",
    "brave": "brave",
}

class WindowStateTracker:
    """Tracks running and active windows for conversational context."""
    def __init__(self):
        self.active_apps: Dict[str, Dict[str, Any]] = {}
        self.focused_app: Optional[str] = None

    def register_app(self, app_id: str, title: str, hwnd: int, minimized: bool = False):
        canonical = CANONICAL_APPS.get(app_id.lower(), app_id.lower())
        self.active_apps[canonical] = {
            "title": title,
            "hwnd": hwnd,
            "minimized": minimized,
            "last_seen": time.time()
        }
        logger.info(f"[WindowStateTracker] Registered active app: {canonical} (title={title!r}, hwnd={hwnd})")

    def get_app(self, app_id: str) -> Optional[Dict[str, Any]]:
        canonical = CANONICAL_APPS.get(app_id.lower(), app_id.lower())
        return self.active_apps.get(canonical)

    def remove_app(self, app_id: str):
        canonical = CANONICAL_APPS.get(app_id.lower(), app_id.lower())
        if canonical in self.active_apps:
            del self.active_apps[canonical]
            logger.info(f"[WindowStateTracker] Deregistered app: {canonical}")

    def update_focused(self, app_id: str):
        canonical = CANONICAL_APPS.get(app_id.lower(), app_id.lower())
        self.focused_app = canonical


class WindowFocusController:
    """Restores and focuses existing windows using pywinauto and win32gui."""
    @staticmethod
    def focus_window(app_id: str) -> bool:
        """
        Attempts to find an existing window for the canonical app_id,
        restore it if minimized, and set foreground focus.
        Returns True if successful, False if no window exists.
        """
        canonical = CANONICAL_APPS.get(app_id.lower(), app_id.lower())
        logger.info(f"[WindowFocusController] Attempting to focus existing window for: {canonical}")

        try:
            import win32gui
            import win32con
            from pywinauto import Desktop
        except ImportError:
            logger.warning("[WindowFocusController] win32gui / pywinauto not available.")
            return False

        # 1. Search open desktop windows via pywinauto
        desktop = Desktop(backend="uia")
        windows = desktop.windows()
        
        target_win = None
        for win in windows:
            title = win.window_text()
            if not title:
                continue
            
            # Simple matching logic matching canonical titles
            matched = False
            title_lower = title.lower()
            if canonical == "settings" and ("settings" in title_lower or "systemsettings" in title_lower):
                matched = True
            elif canonical == "notepad" and "notepad" in title_lower:
                matched = True
            elif canonical == "explorer" and ("explorer" in title_lower or "this pc" in title_lower or "quick access" in title_lower or "downloads" in title_lower or "documents" in title_lower):
                matched = True
            elif canonical in title_lower:
                matched = True

            if matched:
                target_win = win
                break

        if target_win is not None:
            hwnd = target_win.handle
            logger.info(f"[WindowFocusController] Found window: {target_win.window_text()} (hwnd={hwnd})")
            
            try:
                # 2. Check if minimized and restore
                if win32gui.IsIconic(hwnd):
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    time.sleep(0.2)
                
                # 3. Bring to front and set focus
                win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                win32gui.SetForegroundWindow(hwnd)
                target_win.set_focus()
                
                logger.info(f"[WindowFocusController] Successfully focused {canonical}")
                return True
            except Exception as e:
                logger.warning(f"[WindowFocusController] Failed focusing hwnd {hwnd}: {e}")
                
                # Fallback: force set_focus using pywinauto directly
                try:
                    target_win.set_focus()
                    return True
                except Exception as ex:
                    logger.debug(f"[WindowFocusController] direct set_focus fallback failed: {ex}")

        return False
