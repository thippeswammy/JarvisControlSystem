"""
Browser Skill
=============
Playwright and CDP based Brave browser automation.
Supports opening profiles, switching tabs, page actions, and DOM selector querying.
"""

import logging
import os
import subprocess
import time
from typing import Dict, Any, List, Optional
from jarvis.skills.skill_decorator import skill
from jarvis.skills.skill_bus import SkillResult

logger = logging.getLogger(__name__)

BRAVE_PATHS = [
    os.path.expandvars(r"%PROGRAMFILES%\BraveSoftware\Brave-Browser\Application\brave.exe"),
    os.path.expandvars(r"%PROGRAMFILES(X86)%\BraveSoftware\Brave-Browser\Application\brave.exe"),
    os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
]

def get_brave_path() -> Optional[str]:
    for p in BRAVE_PATHS:
        if os.path.exists(p):
            return p
    return None

class BraveBrowserManager:
    """Manages browser automation using Playwright / CDP."""
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self._cdp_url = "http://localhost:9222"

    def _ensure_playwright(self):
        if self.playwright is not None:
            return
        
        # Lazy import of playwright
        from playwright.sync_api import sync_playwright
        self.playwright = sync_playwright().start()

    def connect_or_launch(self, profile: str = "Default") -> Any:
        """Connects via CDP to running Brave or launches new instance."""
        self._ensure_playwright()
        
        # Try connecting via CDP first (if Brave is already running with remote-debugging-port=9222)
        try:
            self.browser = self.playwright.chromium.connect_over_cdp(self._cdp_url)
            self.context = self.browser.contexts[0]
            logger.info(f"[BraveBrowserManager] Connected over CDP to running Brave instance.")
            return self.context
        except Exception as e:
            logger.debug(f"[BraveBrowserManager] CDP connection failed: {e}. Launching new instance...")

        # Fallback: Launch a new Brave instance
        exe = get_brave_path()
        if not exe:
            raise FileNotFoundError("Brave browser executable not found on this system.")

        user_data_dir = os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data")
        
        # Launch persistent context
        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            executable_path=exe,
            headless=False,
            args=[
                f"--profile-directory={profile}",
                "--remote-debugging-port=9222"
            ]
        )
        logger.info(f"[BraveBrowserManager] Launched new Brave instance with profile '{profile}'.")
        return self.context

    def close(self):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
            self.playwright = None


_MANAGER = BraveBrowserManager()

@skill(triggers=["open brave profile", "open profile in brave"], name="open_brave_profile", category="browser")
def open_brave_profile(params: dict) -> SkillResult:
    profile = params.get("profile", "Default").strip()
    if not profile:
        profile = "Default"
        
    try:
        # Try launching/focusing Brave via State/UIA first to make it active
        from jarvis.brain.state_manager import WindowFocusController
        WindowFocusController.focus_window("brave")
        
        context = _MANAGER.connect_or_launch(profile=profile)
        # Ensure we have at least one active page
        if not context.pages:
            page = context.new_page()
        else:
            page = context.pages[0]
            
        page.bring_to_front()
        return SkillResult(success=True, action_taken=f"Opened Brave browser with profile: {profile}")
    except Exception as e:
        logger.warning(f"[browser_skill] Playwright profile open failed: {e}. Falling back to system startfile.")
        
        # System fallback launcher
        exe = get_brave_path()
        if exe:
            try:
                subprocess.Popen([exe, f"--profile-directory={profile}"])
                return SkillResult(success=True, action_taken=f"Launched Brave profile {profile} via system fallback")
            except Exception as se:
                return SkillResult(success=False, message=f"Failed to open Brave profile: {se}")
        return SkillResult(success=False, message=f"Brave browser not installed or failed to launch: {e}")


@skill(triggers=["switch browser tab", "switch tab in brave"], name="switch_browser_tab", category="browser")
def switch_browser_tab(params: dict) -> SkillResult:
    target = params.get("target", "").strip().lower()
    if not target:
        return SkillResult(success=False, message="No target tab name specified")

    try:
        context = _MANAGER.connect_or_launch()
        for page in context.pages:
            title = page.title().lower()
            url = page.url().lower()
            if target in title or target in url:
                page.bring_to_front()
                return SkillResult(success=True, action_taken=f"Switched browser tab to: '{page.title()}'")
        return SkillResult(success=False, message=f"No active browser tab found matching: '{target}'")
    except Exception as e:
        return SkillResult(success=False, message=f"Failed to switch browser tab: {e}")


@skill(triggers=["click web element", "click selector in brave"], name="click_web_element", category="browser")
def click_web_element(params: dict) -> SkillResult:
    selector = params.get("selector", "").strip()
    if not selector:
        return SkillResult(success=False, message="No selector or button text specified")

    try:
        context = _MANAGER.connect_or_launch()
        if not context.pages:
            return SkillResult(success=False, message="No active browser page open")
            
        page = context.pages[0]
        page.bring_to_front()
        
        # Try both text and css matching
        if selector.startswith(".") or selector.startswith("#") or "[" in selector:
            page.click(selector, timeout=5000)
        else:
            # Match by text content
            page.click(f"text={selector}", timeout=5000)
            
        return SkillResult(success=True, action_taken=f"Clicked web element: '{selector}'")
    except Exception as e:
        return SkillResult(success=False, message=f"Failed to click web element '{selector}': {e}")
