"""Crawler Skill — UI tree crawling for unknown element discovery."""
import logging
import time
from jarvis.skills.skill_decorator import skill
from jarvis.skills.skill_bus import SkillResult

logger = logging.getLogger(__name__)


@skill(triggers=["click element", "click button", "click on", "find and click"],
       name="click_element", category="navigation")
def click_element(params: dict) -> SkillResult:
    """
    Click a UI element by label. Uses pywinauto UIA backend.
    Falls back to pyautogui image search if accessibility fails.
    """
    label = params.get("label", "").strip()
    control_type = params.get("control_type", "")
    if not label:
        return SkillResult(success=False, message="No element label specified")

    import time
    from pywinauto import Desktop
    import win32gui
    import re

    # Try for up to 5 seconds
    start_time = time.time()
    last_err = None
    
    while time.time() - start_time < 5.0:
        hwnd = win32gui.GetForegroundWindow()
        win = Desktop(backend="uia").window(handle=hwnd)
        
        try:
            kwargs = {"title_re": re.compile(f".*{re.escape(label)}.*", re.IGNORECASE)}
            if control_type:
                kwargs["control_type"] = control_type
            
            elem = win.child_window(**kwargs)
            # wait up to 0.5s for it to be ready
            try:
                elem.wait('ready', timeout=0.5)
                elem.click_input()
                logger.info(f"[crawler_skill] Clicked via UIA: {label!r}")
                return SkillResult(success=True, action_taken=f"Clicked: {label!r}")
            except Exception as e:
                last_err = e
        except Exception as e:
            last_err = e

        # Fallback
        try:
            for ctrl in win.descendants():
                name = (ctrl.element_info.name or "").strip()
                if label.lower() in name.lower():
                    ctrl.click_input()
                    return SkillResult(success=True, action_taken=f"Clicked (partial match): {name!r}")
        except Exception as e:
            last_err = e

        time.sleep(0.5)

    return SkillResult(success=False, message=f"Could not find element: {label!r} (Last error: {last_err})")


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
