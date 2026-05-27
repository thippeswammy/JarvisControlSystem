"""Navigator Skill — deep-link navigation via URIs and graph paths."""
import logging
import os
import time
from jarvis.skills.skill_decorator import skill
from jarvis.skills.skill_bus import SkillResult

logger = logging.getLogger(__name__)


@skill(triggers=["navigate location", "navigate to", "go to", "open location"],
       name="navigate_location", category="navigation", settle_ms=1500)
def navigate_location(params: dict) -> SkillResult:
    """
    Navigate to a location. Tries URI deep-link first, then step sequence.
    Params:
        target: str — location label (e.g. "wifi", "display settings")
        uri: str    — optional direct ms-settings: or other URI
        steps: list — optional ordered action steps
    """
    uri = params.get("uri", "")
    target = params.get("target", "")
    steps = params.get("steps", [])

    # Fast path: direct URI
    if uri:
        try:
            os.startfile(uri)
            logger.info(f"[navigator_skill] URI navigation: {uri}")
            return SkillResult(success=True, action_taken=f"Opened URI: {uri}")
        except Exception as e:
            logger.warning(f"[navigator_skill] URI failed: {e}")

    # Step sequence fallback
    if steps:
        import pyautogui
        for step in steps:
            try:
                _execute_step(step)
                time.sleep(0.4)
            except Exception as e:
                logger.error(f"[navigator_skill] Step failed: {step!r} — {e}")
                return SkillResult(success=False, message=f"Step failed: {step!r}")
        return SkillResult(success=True, action_taken=f"Navigated via steps to: {target}")

    is_url = any(target.endswith(ext) for ext in [".com", ".net", ".org", ".edu", ".gov", ".io"]) or \
             any(target.startswith(pre) for pre in ["http", "www.", "https"]) or \
             ":\\" in target or "/" in target

    shell_map = {
        "my documents": "shell:Personal",
        "documents": "shell:Personal",
        "downloads": "shell:Downloads",
        "desktop": "shell:Desktop",
        "this pc": "shell:MyComputerFolder",
    }
             
    if target.lower() in shell_map:
        try:
            os.startfile(shell_map[target.lower()])
            return SkillResult(success=True, action_taken=f"Opened shell target: {target}")
        except Exception as e:
            logger.warning(f"[navigator_skill] direct open failed for {target}: {e}")

    if target and is_url:
        full_target = target
        if "." in target and not target.startswith("http") and not ":\\" in target:
            full_target = "https://" + target
        
        # In-Place Browser Navigation Check
        try:
            import pyautogui
            active_title = (pyautogui.getActiveWindowTitle() or "").lower()
            is_browser_active = any(b in active_title for b in ["edge", "chrome", "brave", "firefox", "browser", "chromium"])
            if is_browser_active:
                logger.info(f"[navigator_skill] Active browser window detected: '{active_title}'. Navigating in-place.")
                pyautogui.hotkey("ctrl", "l")
                time.sleep(0.3)
                pyautogui.typewrite(full_target, interval=0.02)
                time.sleep(0.2)
                pyautogui.press("enter")
                return SkillResult(success=True, action_taken=f"Navigated active browser to: {full_target}")
        except Exception as e:
            logger.warning(f"[navigator_skill] In-place browser navigation failed: {e}. Falling back to system handler.")

        try:
            os.startfile(full_target)
            return SkillResult(success=True, action_taken=f"Opened target directly: {full_target}")
        except Exception as e:
            logger.warning(f"[navigator_skill] direct open failed for {full_target}: {e}")
            pass

    return SkillResult(success=False, message=f"No URI or steps for: {target!r}")


def _execute_step(step: str) -> None:
    """Execute a single navigation step string."""
    import pyautogui
    step_l = step.lower().strip()

    if step_l.startswith("uri:"):
        os.startfile(step[4:].strip())
    elif step_l.startswith("click:"):
        label = step[6:].strip()
        _click_by_label(label)
    elif step_l.startswith("key:"):
        keys = step[4:].strip().split("+")
        pyautogui.hotkey(*keys)
    elif step_l.startswith("type:"):
        pyautogui.typewrite(step[5:].strip(), interval=0.04)
    elif step_l.startswith("wait:"):
        secs = float(step[5:].strip())
        time.sleep(secs)
    else:
        # Default: treat as a click label
        _click_by_label(step)


def _click_by_label(label: str) -> None:
    """Find and click a UI element by text or fallback to pyautogui."""
    # 1. Try accessibility click via pywinauto FIRST (highly robust, resolution-independent)
    try:
        _click_by_accessibility(label)
        return
    except Exception as ae:
        logger.debug(f"[navigator_skill] Accessibility click fallback triggered: {ae}")

    # 2. Try pyautogui image lookup as a fallback
    import pyautogui
    try:
        loc = pyautogui.locateCenterOnScreen(label, confidence=0.7)
        if loc:
            pyautogui.click(loc)
            logger.info(f"[navigator_skill] Clicked image element: {label}")
            return
    except Exception as e:
        logger.debug(f"[navigator_skill] PyAutoGUI image click failed: {e}")

    # 3. Simple text/search click helper fallback
    logger.warning(f"[navigator_skill] Failed to click: {label!r}")


def _click_by_accessibility(label: str) -> None:
    try:
        from pywinauto import Desktop
        import re
        import win32gui

        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            raise RuntimeError("No active foreground window found")

        win = Desktop(backend="uia").window(handle=hwnd)
        
        # Search the active window's descendants for clickable matching controls
        descendants = win.descendants()
        target_elem = None
        label_pattern = re.compile(rf".*{re.escape(label)}.*", re.IGNORECASE)
        
        # Prioritized list of control types to click
        for ctrl in descendants:
            try:
                name = (ctrl.element_info.name or "").strip()
                if label_pattern.match(name):
                    ctrl_type = ctrl.element_info.control_type
                    if ctrl_type in ["Button", "MenuItem", "ListItem", "Hyperlink", "Text", "TabItem"]:
                        target_elem = ctrl
                        break
            except Exception:
                continue

        if target_elem is None:
            # Fallback direct child search
            target_elem = win.child_window(title_re=label_pattern)

        if target_elem:
            target_elem.wait('ready', timeout=2)
            target_elem.click_input()
            logger.info(f"[navigator_skill] Clicked accessibility element: {target_elem.element_info.name} ({target_elem.element_info.control_type})")
            return
            
        raise ValueError(f"No clickable element found matching {label!r}")
    except Exception as e:
        logger.debug(f"[navigator_skill] Accessibility click failed for {label!r}: {e}")
        raise e
