"""App Skill — open, close, switch applications."""
import logging
import os
import subprocess
from jarvis.skills.skill_decorator import skill
from jarvis.skills.skill_bus import SkillResult

logger = logging.getLogger(__name__)

KNOWN_APPS = {
    "notepad": "notepad.exe",
    "calculator": "CalculatorApp.exe",
    "paint": "mspaint.exe",
    "wordpad": "wordpad.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "edge": "msedge.exe",
    "chrome": "chrome.exe",
    "firefox": "firefox.exe",
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
            else:
                os.startfile(exe)
            logger.info(f"[app_skill] Launched: {exe}")
            
            # Ensure focus
            import time
            from pywinauto import Desktop
            time.sleep(1.5) # Wait for window to initialize
            try:
                # 1. Try partial title match
                win = Desktop(backend="uia").window(title_re=f"(?i).*{target}.*")
                if win.exists():
                    win.set_focus()
                    logger.info(f"[app_skill] Focused window by title: {target}")
                else:
                    # 2. Try by process name if known
                    if exe:
                        proc_name = exe.replace(".exe", "")
                        win = Desktop(backend="uia").window(process=proc_name)
                        if win.exists():
                            win.set_focus()
                            logger.info(f"[app_skill] Focused window by process: {proc_name}")
            except Exception as fe:
                logger.debug(f"[app_skill] Focus failed for {target}: {fe}")

            return SkillResult(success=True, action_taken=f"Launched and focused {target}", data={"exe": exe})
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
        elif target.lower() == "all":
            # Use PowerShell to close all windows with a title, excluding dev tools and the runner itself
            exclude = "'code','terminal','powershell','cmd','pycharm','conhost','antigravity'"
            cmd = f'powershell "Get-Process | Where-Object {{$_.MainWindowTitle -ne \'\' -and $_.Name -notin ({exclude})}} | Stop-Process -Force"'
            os.system(cmd)
            return SkillResult(success=True, action_taken="Closed all visible applications (excluding dev tools)")
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
