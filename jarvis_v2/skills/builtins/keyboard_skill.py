"""Keyboard Skill — key presses, hotkeys, text typing."""
import logging
import time
from jarvis_v2.skills.skill_decorator import skill
from jarvis_v2.skills.skill_bus import SkillResult

logger = logging.getLogger(__name__)


@skill(triggers=["press key", "hold key", "press"], name="press_key", category="keyboard")
def press_key(params: dict) -> SkillResult:
    key = params.get("key", "").strip()
    if not key:
        return SkillResult(success=False, message="No key specified")
    try:
        import pyautogui
        # Support combos: "ctrl+s", "win+d", "alt+F4"
        if "+" in key:
            parts = [p.strip() for p in key.split("+")]
            pyautogui.hotkey(*parts)
        else:
            pyautogui.press(key)
        return SkillResult(success=True, action_taken=f"Pressed: {key}")
    except Exception as e:
        return SkillResult(success=False, message=str(e))


@skill(triggers=["type text", "write text", "type", "say text"], name="type_text", category="keyboard")
def type_text(params: dict) -> SkillResult:
    text = params.get("text", "")
    interval = float(params.get("interval", 0.04))
    if not text:
        return SkillResult(success=False, message="No text specified")
    try:
        import pyautogui
        import time
        time.sleep(0.5) # Allow focus to settle
        pyautogui.typewrite(text, interval=interval)
        return SkillResult(success=True, action_taken=f"Typed: {text[:40]!r}")
    except Exception as e:
        return SkillResult(success=False, message=str(e))
