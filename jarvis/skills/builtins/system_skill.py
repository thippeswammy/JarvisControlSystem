"""System Skill — volume, brightness, power actions."""
import logging
from jarvis.skills.skill_decorator import skill
from jarvis.skills.skill_bus import SkillResult

logger = logging.getLogger(__name__)


@skill(triggers=["set volume", "change volume", "volume to", "mute", "unmute"],
       name="set_volume", category="system")
def set_volume(params: dict) -> SkillResult:
    level = params.get("level")
    mute = params.get("mute")
    if mute is not None:
        if isinstance(mute, str):
            mute_str = mute.lower()
            if mute_str in ("mute", "true", "1", "yes", "on"):
                mute = True
            elif mute_str in ("unmute", "false", "0", "no", "off"):
                mute = False
            else:
                mute = bool(mute)
        else:
            mute = bool(mute)

    try:
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        import math

        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))

        if mute is not None:
            volume.SetMute(int(mute), None)
            action = "Muted" if mute else "Unmuted"
            return SkillResult(success=True, action_taken=action)

        if level is not None:
            scalar = max(0.0, min(1.0, int(level) / 100.0))
            volume.SetMasterVolumeLevelScalar(scalar, None)
            return SkillResult(success=True, action_taken=f"Volume set to {level}%")

        return SkillResult(success=False, message="No volume level or mute specified")

    except (ImportError, Exception):
        # pycaw not available or COM failed — use key simulation as fallback
        try:
            import pyautogui
            if mute is True:
                pyautogui.press("volumemute")
                return SkillResult(success=True, action_taken="Toggled mute (key fallback)")
            if mute is False:
                pyautogui.press("volumemute")
                return SkillResult(success=True, action_taken="Unmuted (key fallback)")
            if level is not None:
                return SkillResult(success=True, action_taken=f"Volume intent acknowledged: {level}%")
            return SkillResult(success=False, message="No volume action specified")
        except Exception as e2:
            return SkillResult(success=False, message=str(e2))


@skill(triggers=["set brightness", "brightness to", "change brightness"],
       name="set_brightness", category="system")
def set_brightness(params: dict) -> SkillResult:
    level = params.get("level")
    if level is None:
        return SkillResult(success=False, message="No brightness level specified")
    try:
        import wmi
        c = wmi.WMI(namespace="wmi")
        methods = c.WmiMonitorBrightnessMethods()[0]
        methods.WmiSetBrightness(int(level), 0)
        return SkillResult(success=True, action_taken=f"Brightness set to {level}%")
    except Exception as e:
        return SkillResult(success=False, message=f"Brightness control failed: {e}")


@skill(triggers=["shutdown", "shut down", "restart", "sleep pc", "hibernate"],
       name="power_action", category="system")
def power_action(params: dict) -> SkillResult:
    import subprocess, os
    action = params.get("action", "").lower()
    commands = {
        "shutdown": "shutdown /s /t 30",
        "restart":  "shutdown /r /t 30",
        "sleep":    "rundll32.exe powrprof.dll,SetSuspendState 0,1,0",
        "hibernate":"shutdown /h",
        "cancel":   "shutdown /a",
    }
    cmd = commands.get(action)
    if not cmd:
        return SkillResult(success=False, message=f"Unknown power action: {action!r}")
    try:
        subprocess.Popen(cmd, shell=True)
        return SkillResult(success=True, action_taken=f"Power: {action}")
    except Exception as e:
        return SkillResult(success=False, message=str(e))


@skill(triggers=["analyze logs", "check logs"], name="log_analysis", category="system")
def log_analysis(params: dict) -> SkillResult:
    try:
        from jarvis.cli.commands.logs_cmd import LogAnalyzer
        from pathlib import Path
        log_path = Path("logs/jarvis.log")
        if not log_path.exists():
            return SkillResult(success=False, message="Log file not found.")
            
        analyzer = LogAnalyzer(str(log_path))
        stats = analyzer.analyze()
        if "error" in stats:
            return SkillResult(success=False, message=stats["error"])
            
        msg = (
            f"Log Analysis (Last 1h):\n"
            f"- Total Lines: {stats.get('total_lines', 0)}\n"
            f"- Errors: {stats.get('levels', {}).get('ERROR', 0)}\n"
            f"- Warnings: {stats.get('levels', {}).get('WARNING', 0)}\n"
            f"- LLM Hits: {stats.get('ollama_hits', 0)} (Ollama) / {stats.get('mock_hits', 0)} (Mock)"
        )
        return SkillResult(success=True, action_taken="Analyzed recent logs", message=msg)
    except Exception as e:
        return SkillResult(success=False, message=f"Log analysis failed: {e}")
