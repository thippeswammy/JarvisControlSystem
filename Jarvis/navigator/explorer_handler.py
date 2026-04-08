"""
Explorer Handler — File Explorer / This PC Navigation
=====================================================
Handles navigation within Windows File Explorer:
  - Open named locations (Documents, Downloads, This PC, C Drive, etc.)
  - Navigate to any folder path
  - Go back / forward
  - Open new Explorer window
  - Get current path from address bar

Uses pywinauto + pyautogui for interaction.
"""

import logging
import os
import subprocess
import time
from typing import Optional

import pyautogui

from Jarvis.navigator.ui_finder import UIFinder

logger = logging.getLogger(__name__)

try:
    from pywinauto import Desktop, Application
    _HAS_PYWINAUTO = True
except ImportError:
    _HAS_PYWINAUTO = False

# Expand home dir once at import
_HOME = os.path.expanduser("~")


# ─────────────────────────────────────────────
#  Named location map
# ─────────────────────────────────────────────
NAMED_LOCATIONS: dict[str, str] = {
    # User folders
    "documents":      os.path.join(_HOME, "Documents"),
    "document":       os.path.join(_HOME, "Documents"),
    "downloads":      os.path.join(_HOME, "Downloads"),
    "download":       os.path.join(_HOME, "Downloads"),
    "desktop":        os.path.join(_HOME, "Desktop"),
    "pictures":       os.path.join(_HOME, "Pictures"),
    "picture":        os.path.join(_HOME, "Pictures"),
    "photos":         os.path.join(_HOME, "Pictures"),
    "videos":         os.path.join(_HOME, "Videos"),
    "video":          os.path.join(_HOME, "Videos"),
    "music":          os.path.join(_HOME, "Music"),
    "appdata":        os.path.join(_HOME, "AppData"),
    # Special shell folders
    "this pc":        "shell:MyComputerFolder",
    "my pc":          "shell:MyComputerFolder",
    "my computer":    "shell:MyComputerFolder",
    "recycle bin":    "shell:RecycleBinFolder",
    "network":        "shell:NetworkPlacesFolder",
    "libraries":      "shell:Libraries",
    # Drives
    "c drive":        "C:\\",
    "c:":             "C:\\",
    "c disk":         "C:\\",
    "d drive":        "D:\\",
    "d:":             "D:\\",
    "d disk":         "D:\\",
    "e drive":        "E:\\",
    "e:":             "E:\\",
    "f drive":        "F:\\",
    "f:":             "F:\\",
    # Windows folders
    "program files":  "C:\\Program Files",
    "programs":       "C:\\Program Files",
    "windows":        "C:\\Windows",
    "system32":       "C:\\Windows\\System32",
    "temp":           os.environ.get("TEMP", "C:\\Temp"),
    "user":           _HOME,
    "home":           _HOME,
}


class ExplorerHandler:
    """
    Manages File Explorer navigation.
    Opens Explorer windows, navigates to paths/named locations.
    """

    def __init__(self):
        self._finder = UIFinder(min_score=0.4)

    # ─────────────────────────────────────────
    #  Navigate to Named Location
    # ─────────────────────────────────────────
    def navigate_to_named_location(self, name: str) -> bool:
        """
        Open or navigate to a named location like "documents" or "c drive".
        Works with existing Explorer windows or opens a new one.
        """
        name_lower = name.lower().strip()

        # Exact match
        path = NAMED_LOCATIONS.get(name_lower)
        if not path:
            # Partial match
            for key, val in NAMED_LOCATIONS.items():
                if key in name_lower or name_lower in key:
                    path = val
                    break

        if not path:
            logger.debug(f"No named location found for: {name!r}")
            return False

        return self.navigate_to_path(path)

    # ─────────────────────────────────────────
    #  Navigate to Any Path
    # ─────────────────────────────────────────
    def navigate_to_path(self, path: str) -> bool:
        """
        Navigate to any file system path or shell: URI.
        Tries to use existing Explorer window first, opens new if needed.
        """
        # shell: URIs — open directly
        if path.lower().startswith("shell:"):
            subprocess.Popen(f"explorer {path}")
            logger.info(f"Opened Explorer to: {path}")
            return True

        # Expand path
        expanded = os.path.expandvars(os.path.expanduser(path))

        # Try to navigate existing Explorer window using address bar
        if _HAS_PYWINAUTO:
            explorer_win = self._find_explorer_window()
            if explorer_win:
                success = self._navigate_address_bar(explorer_win, expanded)
                if success:
                    return True

        # Open new Explorer window at path
        try:
            subprocess.Popen(f'explorer "{expanded}"')
            logger.info(f"Opened new Explorer window at: {expanded}")
            return True
        except Exception as e:
            logger.error(f"Explorer navigation failed for {expanded!r}: {e}")
            return False

    # ─────────────────────────────────────────
    #  Open new Explorer Window
    # ─────────────────────────────────────────
    def open_new_explorer_window(self, path: str = None) -> bool:
        """Open a new File Explorer window, optionally at a path."""
        try:
            if path:
                expanded = os.path.expandvars(os.path.expanduser(path))
                subprocess.Popen(f'explorer "{expanded}"')
            else:
                subprocess.Popen("explorer")
            logger.info(f"Opened Explorer at: {path or 'default'}")
            return True
        except Exception as e:
            logger.error(f"open_new_explorer_window failed: {e}")
            return False

    # ─────────────────────────────────────────
    #  Go Back / Forward
    # ─────────────────────────────────────────
    def go_back(self) -> bool:
        """Navigate back in Explorer history."""
        pyautogui.hotkey("alt", "left")
        return True

    def go_forward(self) -> bool:
        """Navigate forward in Explorer history."""
        pyautogui.hotkey("alt", "right")
        return True

    # ─────────────────────────────────────────
    #  Get Current Path
    # ─────────────────────────────────────────
    def get_current_path(self) -> Optional[str]:
        """
        Read the current path from the active Explorer window address bar.
        Returns None if not in Explorer or path can't be read.
        """
        if not _HAS_PYWINAUTO:
            return None
        try:
            win = self._find_explorer_window()
            if not win:
                return None
            # The address bar in Explorer is an Edit or ComboBox
            address_bar = self._finder.find_element(
                "address bar", window=win,
                preferred_types=["Edit", "ComboBox"],
            )
            if address_bar:
                return address_bar.element.window_text()
        except Exception as e:
            logger.debug(f"get_current_path failed: {e}")
        return None

    # ─────────────────────────────────────────
    #  Internal Helpers
    # ─────────────────────────────────────────
    def _find_explorer_window(self) -> Optional[object]:
        """Find an open File Explorer window."""
        if not _HAS_PYWINAUTO:
            return None
        try:
            desktop = Desktop(backend="uia")
            # Look for windows with "Explorer" or "File Explorer" in title
            wins = desktop.windows()
            for win in wins:
                try:
                    title = win.window_text().lower()
                    if any(k in title for k in ["file explorer", "this pc", "explorer",
                                                "documents", "downloads", "desktop",
                                                "pictures", "videos", "music",
                                                "c:\\", "d:\\"]):
                        return win
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"_find_explorer_window failed: {e}")
        return None

    def _navigate_address_bar(self, window, path: str) -> bool:
        """Navigate to a path by typing in the Explorer address bar."""
        try:
            # Open address bar (Alt+D)
            window.set_focus()
            time.sleep(0.2)
            pyautogui.hotkey("alt", "d")
            time.sleep(0.3)
            # Clear and type path
            pyautogui.hotkey("ctrl", "a")
            pyautogui.typewrite(path, interval=0.03)
            pyautogui.press("enter")
            time.sleep(0.5)
            logger.info(f"Navigated address bar to: {path}")
            return True
        except Exception as e:
            logger.error(f"Address bar navigation failed: {e}")
            return False


# ─────────────────────────────────────────────
#  Smoke test
# ─────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    handler = ExplorerHandler()

    print("Testing: navigate to Documents folder")
    handler.navigate_to_named_location("documents")
    time.sleep(2)

    print("Testing: get current path")
    path = handler.get_current_path()
    print(f"Current path: {path}")
