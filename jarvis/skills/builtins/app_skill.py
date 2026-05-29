"""App Skill — open, close, switch applications autonomously."""
import logging
import os
import subprocess
from jarvis.skills.skill_decorator import skill
from jarvis.skills.skill_bus import SkillResult
from jarvis.utils.app_finder import AppFinder

logger = logging.getLogger(__name__)

@skill(triggers=["open app", "launch app", "start app", "run app"], name="open_app", category="app", fast_path_eligible=True)
def open_app(params: dict) -> SkillResult:
    target = params.get("target", "").strip()
    if not target:
        return SkillResult(success=False, message="No target app specified")

    # Retrieve router if available for semantic disambiguation fallback
    router = params.get("_router")

    # Try to focus existing window first to avoid multiple launches
    from jarvis.brain.state_manager import WindowFocusController
    try:
        if WindowFocusController.focus_window(target, router=router):
            return SkillResult(success=True, action_taken=f"Focused existing {target}")
    except Exception as fe:
        logger.debug(f"[app_skill] Focus existing check failed: {fe}")

    # Discover path dynamically without hardcoding
    exe = AppFinder.find_exe_path(target)

    if exe:
        try:
            if exe.startswith("ms-settings:"):
                os.startfile(exe)
            else:
                os.startfile(exe)
            logger.info(f"[app_skill] Discovered and launched: {exe}")
            
            # Settle and ensure focus
            import time
            from pywinauto import Desktop
            time.sleep(1.5) # Wait for window to initialize
            try:
                # Try partial title match
                win = Desktop(backend="uia").window(title_re=f"(?i).*{target}.*")
                if win.exists():
                    win.set_focus()
                    logger.info(f"[app_skill] Focused window by title: {target}")
                else:
                    # Try by process name
                    proc_name = os.path.basename(exe).replace(".exe", "")
                    win = Desktop(backend="uia").window(process=proc_name)
                    if win.exists():
                        win.set_focus()
                        logger.info(f"[app_skill] Focused window by process: {proc_name}")
            except Exception as fe:
                logger.debug(f"[app_skill] Focus failed for {target}: {fe}")

            return SkillResult(success=True, action_taken=f"Discovered and launched: {target}", data={"exe": exe})
        except Exception as e:
            logger.error(f"[app_skill] Launch failed for {exe}: {e}")

    # Smart Fallback: Windows Search (Guarded)
    # Prevent long conversational sentences from triggering Edge web searches
    if len(target.split()) > 3 or len(target) > 25 or "?" in target or "'" in target or '"' in target:
        logger.warning(f"[app_skill] Target {target!r} failed validation for Windows Search fallback.")
        return SkillResult(success=False, message=f"NOT_FOUND: Application {target!r} could not be found locally.")

    import pyautogui, time
    try:
        pyautogui.hotkey("win", "s")
        time.sleep(0.8)
        pyautogui.typewrite(target, interval=0.05)
        time.sleep(1.0) # Settle for search results to appear
        
        # We press enter assuming the short target brings up a local app.
        # If further inspection is needed to strictly prevent web results, UI automation could check the pane here.
        pyautogui.press("enter")
        return SkillResult(success=True, action_taken=f"Searched and launched fallback: {target}")
    except Exception as e:
        return SkillResult(success=False, message=f"Failed to open {target!r}: {e}")


@skill(triggers=["close app", "quit app", "exit app"], name="close_app", category="app", fast_path_eligible=True)
def close_app(params: dict) -> SkillResult:
    target = params.get("target", "active").strip()
    import pyautogui
    try:
        if target == "active":
            pyautogui.hotkey("alt", "F4")
        elif "all" in target.lower():
            # Close all windows excluding development tools and context components
            exclude = "'code','terminal','powershell','cmd','pycharm','conhost','antigravity'"
            cmd = f'powershell "Get-Process | Where-Object {{$_.MainWindowTitle -ne \'\' -and $_.Name -notin ({exclude})}} | Stop-Process -Force"'
            os.system(cmd)
            return SkillResult(success=True, action_taken="Closed all visible applications (excluding dev tools)")
        else:
            # Query path to get correct executable name dynamically
            exe = AppFinder.find_exe_path(target)
            exe_name = os.path.basename(exe) if exe and not exe.startswith("ms-settings:") else f"{target}.exe"
            
            if exe_name.lower() == "explorer.exe":
                try:
                    import win32com.client
                    shell = win32com.client.Dispatch("Shell.Application")
                    for window in shell.Windows():
                        window.Quit()
                except Exception as ex:
                    logger.error(f"[app_skill] Failed to gracefully close Explorer: {ex}")
            else:
                os.system(f'taskkill /IM "{exe_name}" /F')
                # Try raw target too in case it was launched directly
                if exe_name.lower() != f"{target.lower()}.exe":
                    os.system(f'taskkill /IM "{target}.exe" /F')
                    
        return SkillResult(success=True, action_taken=f"Closed application: {target}")
    except Exception as e:
        return SkillResult(success=False, message=str(e))
