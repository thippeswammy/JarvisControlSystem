"""App Skill — open, close, switch applications."""
import logging
import os
import subprocess
from jarvis_v2.skills.skill_decorator import skill
from jarvis_v2.skills.skill_bus import SkillResult

logger = logging.getLogger(__name__)

KNOWN_APPS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "paint": "mspaint.exe",
    "wordpad": "wordpad.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "settings": "SystemSettings.exe",
    "control panel": "control.exe",
    "task manager": "taskmgr.exe",
    "registry editor": "regedit.exe",
    "device manager": "devmgmt.msc",
    "snipping tool": "SnippingTool.exe",
    "magnifier": "magnify.exe",
}

@skill(triggers=["open app", "launch app", "start app", "run app"], name="open_app", category="app")
def open_app(params: dict) -> SkillResult:
    target = params.get("target", "").strip()
    if not target:
        return SkillResult(success=False, message="No target app specified")

    exe = KNOWN_APPS.get(target.lower())

    if exe:
        try:
            if target.lower() == "settings":
                os.startfile("ms-settings:")
            elif exe.endswith(".msc"):
                os.startfile(exe)
            else:
                subprocess.Popen(exe, shell=True)
            logger.info(f"[app_skill] Launched: {exe}")
            return SkillResult(success=True, action_taken=f"Launched {target}", data={"exe": exe})
        except Exception as e:
            logger.error(f"[app_skill] Launch failed for {exe}: {e}")

    # Fallback: Windows Search
    import pyautogui, time
    try:
        pyautogui.hotkey("win", "s")
        time.sleep(0.6)
        pyautogui.typewrite(target, interval=0.05)
        time.sleep(0.5)
        pyautogui.press("enter")
        return SkillResult(success=True, action_taken=f"Searched and launched: {target}")
    except Exception as e:
        return SkillResult(success=False, message=f"Failed to open {target!r}: {e}")


@skill(triggers=["close app", "quit app", "exit app"], name="close_app", category="app")
def close_app(params: dict) -> SkillResult:
    target = params.get("target", "active").strip()
    import pyautogui
    try:
        if target == "active":
            pyautogui.hotkey("alt", "F4")
        else:
            exe = KNOWN_APPS.get(target.lower(), f"{target}.exe")
            
            if exe.lower() == "explorer.exe":
                try:
                    import win32com.client
                    shell = win32com.client.Dispatch("Shell.Application")
                    for window in shell.Windows():
                        window.Quit()
                except Exception as ex:
                    logger.error(f"[app_skill] Failed to gracefully close Explorer: {ex}")
            else:
                os.system(f'taskkill /IM "{exe}" /F')
        return SkillResult(success=True, action_taken=f"Closed: {target}")
    except Exception as e:
        return SkillResult(success=False, message=str(e))
