"""
Browser Skill
=============
Playwright and CDP based Brave/Chromium browser automation.
Supports dynamic executable path finding, profile management, tab operations,
and advanced DOM Accessibility Tree extraction for index-based clicking/typing.
"""

import logging
import os
import subprocess
import time
from typing import Dict, Any, List, Optional
from jarvis.skills.skill_decorator import skill
from jarvis.skills.skill_bus import SkillResult
from jarvis.utils.app_finder import AppFinder

logger = logging.getLogger(__name__)

class BraveBrowserManager:
    """Manages browser automation using Playwright / CDP."""
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self._cdp_url = "http://localhost:9222"
        self.cached_nodes: List[Any] = []

    def _ensure_playwright(self):
        if self.playwright is not None:
            return
        from playwright.sync_api import sync_playwright
        self.playwright = sync_playwright().start()

    def connect_or_launch(self, profile: str = "Default") -> Any:
        """Connects via CDP to running Brave or launches new instance."""
        self._ensure_playwright()
        
        # Try connecting via CDP first
        try:
            self.browser = self.playwright.chromium.connect_over_cdp(self._cdp_url)
            self.context = self.browser.contexts[0]
            logger.info(f"[BraveBrowserManager] Connected over CDP to running Brave instance.")
            return self.context
        except Exception as e:
            logger.debug(f"[BraveBrowserManager] CDP connection failed: {e}. Launching new instance...")

        # Discovers the executable path dynamically
        exe = AppFinder.find_exe_path("brave") or AppFinder.find_exe_path("chrome")
        if not exe:
            raise FileNotFoundError("Brave or Chrome executable not found on this system.")

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
        logger.info(f"[BraveBrowserManager] Launched new browser instance dynamically: {exe}")
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
        from jarvis.brain.state_manager import WindowFocusController
        WindowFocusController.focus_window("brave")
        
        context = _MANAGER.connect_or_launch(profile=profile)
        if not context.pages:
            page = context.new_page()
        else:
            page = context.pages[0]
            
        page.bring_to_front()
        return SkillResult(success=True, action_taken=f"Opened browser with profile: {profile}")
    except Exception as e:
        logger.warning(f"[browser_skill] Profile open failed: {e}. Falling back to system startfile.")
        
        exe = AppFinder.find_exe_path("brave") or AppFinder.find_exe_path("chrome")
        if exe:
            try:
                subprocess.Popen([exe, f"--profile-directory={profile}"])
                return SkillResult(success=True, action_taken=f"Launched browser profile {profile} via system fallback")
            except Exception as se:
                return SkillResult(success=False, message=f"Failed to open browser profile: {se}")
        return SkillResult(success=False, message=f"Browser not installed or failed to launch: {e}")


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
        
        if selector.startswith(".") or selector.startswith("#") or "[" in selector:
            page.click(selector, timeout=5000)
        else:
            page.click(f"text={selector}", timeout=5000)
            
        return SkillResult(success=True, action_taken=f"Clicked web element: '{selector}'")
    except Exception as e:
        return SkillResult(success=False, message=f"Failed to click web element '{selector}': {e}")


@skill(triggers=["extract browser dom tree", "show web interaction tree"], name="extract_browser_dom_tree", category="browser")
def extract_browser_dom_tree(params: dict) -> SkillResult:
    """Extracts a clean, compact, index-based representation of active web interactive elements."""
    try:
        context = _MANAGER.connect_or_launch()
        if not context.pages:
            return SkillResult(success=False, message="No active page open to extract tree.")
            
        page = context.pages[0]
        page.bring_to_front()
        
        # Enumerate clickable/interactive candidates
        selector = "a, button, input, select, textarea, [role=button], [role=link]"
        elements = page.query_selector_all(selector)
        
        _MANAGER.cached_nodes = []
        lines = []
        idx = 0
        
        for elem in elements:
            if not elem.is_visible():
                continue
                
            tag = elem.evaluate("node => node.tagName.toLowerCase()")
            text = (elem.inner_text() or "").strip().replace("\n", " ")
            placeholder = elem.get_attribute("placeholder") or ""
            role = elem.get_attribute("role") or ""
            elem_id = elem.get_attribute("id") or ""
            name_attr = elem.get_attribute("name") or ""
            
            # Formulate tag name and description
            label = text or placeholder or name_attr or elem_id or "Unnamed element"
            if len(label) > 60:
                label = label[:57] + "..."
                
            type_str = tag
            if role:
                type_str = f"{tag}[{role}]"
                
            idx += 1
            _MANAGER.cached_nodes.append(elem)
            lines.append(f"[{idx}] {type_str.upper()}: '{label}'")
            
        catalog = " | ".join(lines) if lines else "No interactive web elements detected."
        return SkillResult(success=True, action_taken="Extracted DOM Accessibility Tree", data={"dom_tree": catalog})
    except Exception as e:
        return SkillResult(success=False, message=f"DOM extraction failed: {e}")


@skill(triggers=["click browser node", "click web index"], name="click_browser_node", category="browser")
def click_browser_node(params: dict) -> SkillResult:
    try:
        index = int(params.get("index", 0))
    except ValueError:
        return SkillResult(success=False, message="Invalid node index integer")

    if not (1 <= index <= len(_MANAGER.cached_nodes)):
        return SkillResult(success=False, message=f"Node index {index} out of cached bounds (1-{len(_MANAGER.cached_nodes)})")
        
    try:
        elem = _MANAGER.cached_nodes[index - 1]
        elem.click()
        return SkillResult(success=True, action_taken=f"Clicked browser node index: {index}")
    except Exception as e:
        return SkillResult(success=False, message=f"Failed clicking browser node: {e}")


@skill(triggers=["fill browser node", "type web index"], name="fill_browser_node", category="browser")
def fill_browser_node(params: dict) -> SkillResult:
    try:
        index = int(params.get("index", 0))
    except ValueError:
        return SkillResult(success=False, message="Invalid node index integer")
    text = params.get("text", "")

    if not (1 <= index <= len(_MANAGER.cached_nodes)):
        return SkillResult(success=False, message=f"Node index {index} out of cached bounds (1-{len(_MANAGER.cached_nodes)})")
        
    try:
        elem = _MANAGER.cached_nodes[index - 1]
        elem.fill(text)
        return SkillResult(success=True, action_taken=f"Typed '{text}' into browser node index: {index}")
    except Exception as e:
        return SkillResult(success=False, message=f"Failed typing into browser node: {e}")
