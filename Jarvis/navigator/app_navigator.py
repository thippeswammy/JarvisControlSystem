"""
App Navigator — Generic Windows UI Automation
=============================================
Works for ANY Windows application using pywinauto (UIA backend):
  - Win32 apps (Notepad, Paint, Calculator)
  - WinForms / WPF apps
  - UWP / Store apps (Settings, Photos, etc.)
  - Electron apps (VS Code, Discord)
  - File Explorer / This PC

Core capabilities:
  - click_element(target)        → find + click any UI element
  - type_in_field(field, text)   → focus field + type
  - navigate_menu(menu_path)     → multi-level menu navigation
  - scroll(direction, amount)    → scroll active window
"""

import logging
import time
from typing import Optional

import pyautogui

from Jarvis.navigator.ui_finder import UIFinder, _CLICKABLE_TYPES, _INPUT_TYPES

logger = logging.getLogger(__name__)

try:
    from pywinauto import Desktop, mouse
    _HAS_PYWINAUTO = True
except ImportError:
    _HAS_PYWINAUTO = False
    logger.warning("pywinauto not available — UI navigation will use fallbacks only.")


class AppNavigator:
    """
    Generic Windows UI navigator. Works on any Windows application.
    Uses UIFinder for element lookup + pywinauto for interaction.
    Falls back to pyautogui keyboard shortcuts when pywinauto is unavailable.
    """

    # Common keyboard shortcuts as fallback for navigation
    _KEYBOARD_FALLBACKS: dict[str, tuple] = {
        "save":          ("ctrl", "s"),
        "save as":       ("ctrl", "shift", "s"),
        "new":           ("ctrl", "n"),
        "new file":      ("ctrl", "n"),
        "open":          ("ctrl", "o"),
        "open file":     ("ctrl", "o"),
        "close":         ("ctrl", "w"),
        "undo":          ("ctrl", "z"),
        "redo":          ("ctrl", "y"),
        "copy":          ("ctrl", "c"),
        "paste":         ("ctrl", "v"),
        "cut":           ("ctrl", "x"),
        "select all":    ("ctrl", "a"),
        "find":          ("ctrl", "f"),
        "replace":       ("ctrl", "h"),
        "print":         ("ctrl", "p"),
        "refresh":       ("f5",),
        "address bar":   ("alt", "d"),
        "back":          ("alt", "left"),
        "forward":       ("alt", "right"),
        "go back":       ("alt", "left"),
        "go forward":    ("alt", "right"),
        "new tab":       ("ctrl", "t"),
        "close tab":     ("ctrl", "w"),
        "next tab":      ("ctrl", "tab"),
        "prev tab":      ("ctrl", "shift", "tab"),
        "zoom in":       ("ctrl", "+"),
        "zoom out":      ("ctrl", "-"),
        "fullscreen":    ("f11",),
        "help":          ("f1",),
        "settings":      ("ctrl", ","),
        "developer tools": ("f12",),
        "search":        ("ctrl", "f"),
    }

    def __init__(self):
        self._finder = UIFinder(min_score=0.4)
        self._ocr_clicker = None

    # ─────────────────────────────────────────
    #  Click Element (any app)
    # ─────────────────────────────────────────
    def click_element(self, target: str, window=None) -> bool:
        """
        Find and click a UI element by name.
        Falls back to keyboard shortcut if UI search fails.
        """
        target_lower = target.lower().strip()

        # Step 1: Try UI Automation (pywinauto)
        if _HAS_PYWINAUTO:
            win = window or self._finder.get_active_window()
            if win:
                elem = self._finder.find_element(
                    target_lower, window=win,
                    preferred_types=list(_CLICKABLE_TYPES),
                )
                if elem:
                    try:
                        self._click_control(elem.element)
                        logger.info(f"Clicked '{elem.name}' ({elem.control_type}) via UI Automation")
                        return True
                    except Exception as e:
                        logger.warning(f"UI click failed for {target!r}: {e}")

        # Step 2: Keyboard shortcut fallback
        keys = self._KEYBOARD_FALLBACKS.get(target_lower)
        if keys:
            pyautogui.hotkey(*keys)
            logger.info(f"Used keyboard shortcut {keys} for '{target}'")
            return True

        # Step 3: OCR Visual Scan Fallback (Ultimate Fallback)
        logger.info(f"UI and Keyboard shortcuts failed. Attempting visual OCR scan for '{target}'...")
        if self._ocr_clicker is None:
            from Jarvis.navigator.ocr_clicker import VisualClicker
            self._ocr_clicker = VisualClicker()
            
        if self._ocr_clicker.click_text(target):
            logger.info(f"Clicked '{target}' visually using OCR.")
            return True

        logger.warning(f"Could not find element visually or via shortcut: {target!r}")
        return False

    # ─────────────────────────────────────────
    #  Type in Field
    # ─────────────────────────────────────────
    def type_in_field(self, field_name: str, text: str, window=None) -> bool:
        """
        Find a text input field by name, focus it, and type text.
        """
        if not _HAS_PYWINAUTO:
            # Fallback: just type (hope cursor is in the right place)
            pyautogui.typewrite(text, interval=0.03)
            return True

        win = window or self._finder.get_active_window()
        if not win:
            return False

        # Find text field
        field = self._finder.find_element(
            field_name, window=win,
            preferred_types=list(_INPUT_TYPES),
        )

        if not field:
            # Try clicking field by name then typing
            logger.debug(f"Field {field_name!r} not found via UI Automation, trying click + type")
            clicked = self.click_element(field_name, window=win)
            if clicked:
                time.sleep(0.2)
                pyautogui.typewrite(text, interval=0.03)
                return True
            return False

        try:
            field.element.set_focus()
            time.sleep(0.1)
            # Try set_text first (fast, direct)
            try:
                field.element.set_edit_text(text)
            except Exception:
                # Fallback: click then typewrite
                self._click_control(field.element)
                time.sleep(0.1)
                pyautogui.hotkey("ctrl", "a")   # Select all existing text
                pyautogui.typewrite(text, interval=0.03)

            logger.info(f"Typed '{text}' in field '{field.name}'")
            return True
        except Exception as e:
            logger.error(f"type_in_field failed for {field_name!r}: {e}")
            return False

    # ─────────────────────────────────────────
    #  Navigate Menu
    # ─────────────────────────────────────────
    def navigate_menu(self, menu_path: list[str], window=None) -> bool:
        """
        Navigate a menu path step by step.
        e.g. ["File", "Save As"] clicks File then Save As.
        """
        if not menu_path:
            return False

        if _HAS_PYWINAUTO:
            win = window or self._finder.get_active_window()
            if win:
                success = self._finder.find_and_navigate_menu(win, menu_path)
                if success:
                    return True

        # Keyboard fallback: try each step as a click
        for step in menu_path:
            self.click_element(step)
            time.sleep(0.3)

        return True   # Optimistic — can't verify easily

    # ─────────────────────────────────────────
    #  Scroll
    # ─────────────────────────────────────────
    def scroll(self, direction: str = "down", amount: int = 3, window=None) -> bool:
        """Scroll the active window by ensuring the mouse is over it first."""
        try:
            # Ensure mouse is over the active window so scroll events actually target it
            if _HAS_PYWINAUTO:
                win = window or self._finder.get_active_window()
                if win:
                    try:
                        rect = win.rectangle()
                        # Move to dead center of the window
                        x = (rect.left + rect.right) // 2
                        y = (rect.top + rect.bottom) // 2
                        pyautogui.moveTo(x, y)
                        time.sleep(0.1)  # tiny sleep to let cursor register
                    except Exception as e:
                        logger.debug(f"Could not center mouse for scroll: {e}")

            direction_lower = direction.lower()
            if direction_lower in ("down", "up"):
                # On Windows: negative value scrolls DOWN, positive scrolls UP.
                # So if direction="down", we negate the amount.
                clicks = -amount if direction_lower == "down" else amount
                # Multiply by 100 because PyAutoGUI amount on Windows is very small per tick
                pyautogui.scroll(clicks * 100)
            elif direction_lower == "left":
                pyautogui.hscroll(-amount * 100)
            elif direction_lower == "right":
                pyautogui.hscroll(amount)
            logger.info(f"Scrolled {direction} by {amount}")
            return True
        except Exception as e:
            logger.error(f"Scroll failed: {e}")
            return False

    # ─────────────────────────────────────────
    #  Get Active Window Info (debug)
    # ─────────────────────────────────────────
    def get_active_window_info(self) -> dict:
        """Returns info about the currently active window."""
        if not _HAS_PYWINAUTO:
            return {}
        try:
            win = self._finder.get_active_window()
            if win:
                return {
                    "title": win.window_text(),
                    "control_type": win.element_info.control_type,
                }
        except Exception:
            pass
        return {}

    def list_elements(self, window=None) -> list[dict]:
        """List all interactable elements in the active window (for debugging)."""
        if not _HAS_PYWINAUTO:
            return []
        win = window or self._finder.get_active_window()
        if not win:
            return []
        elements = self._finder.get_all_interactable(win)
        return [{"name": e.name, "type": e.control_type} for e in elements]

    # ─────────────────────────────────────────
    #  Internal: click a pywinauto control
    # ─────────────────────────────────────────
    @staticmethod
    def _click_control(control) -> None:
        """
        Click a pywinauto control — tries invoke() first (accessibility),
        falls back to click_input() (mouse simulation).
        """
        try:
            control.invoke()
        except Exception:
            try:
                control.click_input()
            except Exception as e2:
                # Last resort: move mouse and click
                rect = control.rectangle()
                x = (rect.left + rect.right) // 2
                y = (rect.top + rect.bottom) // 2
                pyautogui.click(x, y)


# ─────────────────────────────────────────────
#  Smoke test
# ─────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    nav = AppNavigator()

    print("Active window:", nav.get_active_window_info())
    print("\nInteractable elements:")
    for elem in nav.list_elements()[:15]:
        print(f"  {elem['type']:15s} | {elem['name']}")

    print("\nTest: click 'File' menu")
    nav.click_element("file")

    print("\nTest: scroll down")
    nav.scroll("down", 3)
