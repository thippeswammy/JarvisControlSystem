"""Window Skill — minimize, maximize, move, resize windows."""
import logging
from jarvis.skills.skill_decorator import skill
from jarvis.skills.skill_bus import SkillResult

logger = logging.getLogger(__name__)


@skill(triggers=["minimize window", "minimise window", "minimize"], name="minimize_window", category="window")
def minimize_window(params: dict) -> SkillResult:
    try:
        import pyautogui
        pyautogui.hotkey("win", "down")
        return SkillResult(success=True, action_taken="Window minimized")
    except Exception as e:
        return SkillResult(success=False, message=str(e))


@skill(triggers=["maximize window", "maximise window", "fullscreen", "full screen"],
       name="maximize_window", category="window")
def maximize_window(params: dict) -> SkillResult:
    try:
        import pyautogui
        pyautogui.hotkey("win", "up")
        return SkillResult(success=True, action_taken="Window maximized")
    except Exception as e:
        return SkillResult(success=False, message=str(e))


@skill(triggers=["snap left", "snap right", "window left", "window right"],
       name="snap_window", category="window")
def snap_window(params: dict) -> SkillResult:
    direction = params.get("direction", "left").lower()
    key = "left" if "left" in direction else "right"
    try:
        import pyautogui
        pyautogui.hotkey("win", key)
        return SkillResult(success=True, action_taken=f"Snapped {direction}")
    except Exception as e:
        return SkillResult(success=False, message=str(e))


@skill(triggers=["switch window", "alt tab", "next window"], name="switch_window", category="window")
def switch_window(params: dict) -> SkillResult:
    try:
        import pyautogui
        pyautogui.hotkey("alt", "tab")
        return SkillResult(success=True, action_taken="Switched window")
    except Exception as e:
        return SkillResult(success=False, message=str(e))
@skill(triggers=["activate window", "focus window", "bring to front", "switch to"],
       name="activate_window", category="window")
def activate_window(params: dict) -> SkillResult:
    target = params.get("target", "").strip()
    if not target:
        return SkillResult(success=False, message="No window title specified")
    
    try:
        from pywinauto import Desktop
        win = Desktop(backend="uia").window(title_re=f"(?i).*{target}.*")
        if win.exists():
            win.set_focus()
            return SkillResult(success=True, action_taken=f"Focused window: {target}")
        else:
            return SkillResult(success=False, message=f"Window not found: {target}")
    except Exception as e:
        return SkillResult(success=False, message=str(e))
