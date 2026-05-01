"""Crawler Skill — UI tree crawling for unknown element discovery."""
import logging
import time
from jarvis_v2.skills.skill_decorator import skill
from jarvis_v2.skills.skill_bus import SkillResult

logger = logging.getLogger(__name__)


@skill(triggers=["click element", "click button", "click on", "find and click"],
       name="click_element", category="navigation")
def click_element(params: dict) -> SkillResult:
    """
    Click a UI element by label. Uses pywinauto UIA backend.
    Falls back to pyautogui image search if accessibility fails.
    """
    label = params.get("label", "").strip()
    control_type = params.get("control_type", "")  # Button, CheckBox, etc.
    if not label:
        return SkillResult(success=False, message="No element label specified")

    # Try UIA accessibility tree first (fast, reliable)
    try:
        from pywinauto import Desktop
        import win32gui
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd)
        win = Desktop(backend="uia").window(handle=hwnd)
        kwargs = {"title": label}
        if control_type:
            kwargs["control_type"] = control_type
        elem = win.child_window(**kwargs)
        elem.click_input()
        logger.info(f"[crawler_skill] Clicked via UIA: {label!r}")
        return SkillResult(success=True, action_taken=f"Clicked: {label!r}")
    except Exception as e:
        logger.debug(f"[crawler_skill] UIA click failed for {label!r}: {e}")

    # Fallback: partial match on any clickable element
    try:
        from pywinauto import Desktop
        import win32gui
        hwnd = win32gui.GetForegroundWindow()
        win = Desktop(backend="uia").window(handle=hwnd)
        for ctrl in win.descendants():
            name = (ctrl.element_info.name or "").strip()
            if label.lower() in name.lower():
                ctrl.click_input()
                return SkillResult(success=True, action_taken=f"Clicked (partial match): {name!r}")
    except Exception as e:
        logger.debug(f"[crawler_skill] Partial match failed: {e}")

    return SkillResult(success=False, message=f"Could not find element: {label!r}")


@skill(triggers=["scroll down", "scroll up", "scroll page"],
       name="scroll_page", category="navigation")
def scroll_page(params: dict) -> SkillResult:
    direction = params.get("direction", "down")
    clicks = int(params.get("clicks", 3))
    try:
        import pyautogui
        delta = -clicks if direction == "down" else clicks
        pyautogui.scroll(delta)
        return SkillResult(success=True, action_taken=f"Scrolled {direction} {clicks} clicks")
    except Exception as e:
        return SkillResult(success=False, message=str(e))
