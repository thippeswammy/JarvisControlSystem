"""
Unified World-State Modeler
==========================
Constructs a semantic model of the operating system environment (running windows,
active background processes, system resource states, and browser metadata) to
allow rich reasoning within OODA cycles.
"""

import logging
import sys
import psutil
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class WorldState:
    """Represents a rich snapshot of the OS and browser environments."""
    
    def __init__(self, active_window: Dict[str, Any], running_processes: List[str], open_windows: List[Dict[str, Any]], system_resources: Dict[str, Any], browser_state: Optional[Dict[str, Any]] = None):
        self.active_window = active_window
        self.running_processes = running_processes
        self.open_windows = open_windows
        self.system_resources = system_resources
        self.browser_state = browser_state

    def to_llm_context(self) -> str:
        """Serializes the operating system environment state into a clean format for LLM prompts."""
        lines = [
            "=== UNIFIED WORLD STATE ===",
            f"Active Foreground Window: {self.active_window.get('title')} (Process: {self.active_window.get('process')})",
            f"System Resources: CPU {self.system_resources.get('cpu')}% | RAM {self.system_resources.get('ram')}%",
            "Open Applications on Desktop:"
        ]
        
        # Add top 10 open windows
        for win in self.open_windows[:12]:
            lines.append(f"  • '{win.get('title')}' (Process: {win.get('process')})")
            
        if self.browser_state:
            lines.append("Active Web Browser Context:")
            lines.append(f"  • Profile: {self.browser_state.get('profile')}")
            lines.append(f"  • Active Tab Title: '{self.browser_state.get('tab_title')}'")
            lines.append(f"  • Active Tab URL: {self.browser_state.get('tab_url')}")
            
        return "\n".join(lines)


class WorldStateModeler:
    """Harvests and builds a unified WorldState model dynamically on demand."""

    @staticmethod
    def get_current_state(browser_manager: Optional[Any] = None) -> WorldState:
        """Gathers and compiles active state from Windows OS and Brave browser contexts."""
        try:
            import win32gui
            import win32process
            from pywinauto import Desktop
        except ImportError:
            logger.warning("[WorldStateModeler] Windows win32/pywinauto UIA libraries unavailable.")
            return WorldState({}, [], [], {}, None)

        # 1. Harvest Active Foreground Window
        active_win_data = {"title": "None", "process": "none", "hwnd": 0}
        hwnd = win32gui.GetForegroundWindow()
        if hwnd:
            try:
                title = win32gui.GetWindowText(hwnd) or ""
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                proc = psutil.Process(pid)
                proc_name = proc.name().replace(".exe", "").lower()
                active_win_data = {"title": title, "process": proc_name, "hwnd": hwnd}
            except Exception:
                pass

        # 2. Harvest Open Windows
        open_windows = []
        desktop = Desktop(backend="uia")
        try:
            for win in desktop.windows():
                title = win.window_text()
                if not title:
                    continue
                try:
                    _, pid = win32process.GetWindowThreadProcessId(win.handle)
                    proc = psutil.Process(pid)
                    proc_name = proc.name().replace(".exe", "").lower()
                except Exception:
                    proc_name = "unknown"
                open_windows.append({"title": title, "process": proc_name, "hwnd": win.handle})
        except Exception as e:
            logger.debug(f"[WorldStateModeler] Enumerate windows failed: {e}")

        # 3. System resources
        system_resources = {
            "cpu": psutil.cpu_percent(),
            "ram": psutil.virtual_memory().percent
        }

        # 4. Harvest background processes (top names)
        running_procs = list(set([p.info["name"].replace(".exe", "").lower() for p in psutil.process_iter(["name"]) if p.info["name"]]))

        # 5. Harvest Browser State if active connection exists
        browser_state = None
        if browser_manager and browser_manager.context:
            try:
                ctx = browser_manager.context
                if ctx.pages:
                    active_page = ctx.pages[0]
                    browser_state = {
                        "profile": getattr(browser_manager, "active_profile", "Default"),
                        "tab_title": active_page.title(),
                        "tab_url": active_page.url()
                    }
            except Exception as be:
                logger.debug(f"[WorldStateModeler] Browser status harvesting failed: {be}")

        return WorldState(
            active_window=active_win_data,
            running_processes=running_procs,
            open_windows=open_windows,
            system_resources=system_resources,
            browser_state=browser_state
        )
