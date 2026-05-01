"""Navigator Skill — deep-link navigation via URIs and graph paths."""
import logging
import os
import time
from jarvis.skills.skill_decorator import skill
from jarvis.skills.skill_bus import SkillResult

logger = logging.getLogger(__name__)


@skill(triggers=["navigate location", "navigate to", "go to", "open location"],
       name="navigate_location", category="navigation")
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

    # Fallback: if target looks like a URL or path, try opening directly
    is_url = any(target.endswith(ext) for ext in [".com", ".net", ".org", ".edu", ".gov", ".io"]) or \
             any(target.startswith(pre) for pre in ["http", "www.", "https"]) or \
             ":\\" in target or "/" in target
             
    if target and is_url:
        full_target = target
        if "." in target and not target.startswith("http") and not ":\\" in target:
            full_target = "https://" + target
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
    """Find and click a UI element by its text label using pyautogui."""
    import pyautogui
    try:
        loc = pyautogui.locateCenterOnScreen(label, confidence=0.7)
        if loc:
            pyautogui.click(loc)
    except Exception:
        # No image — try accessibility click via pywinauto
        _click_by_accessibility(label)


def _click_by_accessibility(label: str) -> None:
    try:
        from pywinauto import Desktop
        win = Desktop(backend="uia").window(title_re=".*")
        elem = win.child_window(title=label, control_type="Button")
        elem.click_input()
    except Exception as e:
        logger.debug(f"[navigator_skill] Accessibility click failed for {label!r}: {e}")
