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

    @staticmethod
    def diff(before: 'WorldState', after: 'WorldState') -> dict:
        """
        Compute semantic diff between two world state snapshots.
        
        Returns a dict describing what changed:
          - focus_changed: bool + details
          - windows_opened: list of new window titles
          - windows_closed: list of removed window titles
          - resource_delta: CPU/RAM changes
          - browser_changed: bool + details
        """
        result = {}

        # Focus change
        before_title = before.active_window.get("title", "")
        after_title = after.active_window.get("title", "")
        if before_title != after_title:
            result["focus_changed"] = {
                "from": before_title,
                "to": after_title,
            }

        # Window diff
        before_wins = {w.get("title", "") for w in before.open_windows if w.get("title")}
        after_wins = {w.get("title", "") for w in after.open_windows if w.get("title")}
        opened = after_wins - before_wins
        closed = before_wins - after_wins
        if opened:
            result["windows_opened"] = sorted(opened)
        if closed:
            result["windows_closed"] = sorted(closed)

        # Resource delta
        cpu_before = before.system_resources.get("cpu", 0)
        cpu_after = after.system_resources.get("cpu", 0)
        ram_before = before.system_resources.get("ram", 0)
        ram_after = after.system_resources.get("ram", 0)
        if abs(cpu_after - cpu_before) > 5 or abs(ram_after - ram_before) > 3:
            result["resource_delta"] = {
                "cpu": f"{cpu_before}% → {cpu_after}%",
                "ram": f"{ram_before}% → {ram_after}%",
            }

        # Browser state change
        if before.browser_state or after.browser_state:
            b_tab = (before.browser_state or {}).get("tab_title", "")
            a_tab = (after.browser_state or {}).get("tab_title", "")
            b_url = (before.browser_state or {}).get("tab_url", "")
            a_url = (after.browser_state or {}).get("tab_url", "")
            if b_tab != a_tab or b_url != a_url:
                result["browser_changed"] = {
                    "tab_from": b_tab,
                    "tab_to": a_tab,
                    "url_from": b_url,
                    "url_to": a_url,
                }

        if not result:
            result["no_change"] = True

        return result

    @staticmethod
    def diff_to_text(diff: dict) -> str:
        """Convert a diff dict to human-readable text for LLM injection."""
        if diff.get("no_change"):
            return "No observable changes to the desktop environment."
        
        lines = []
        if "focus_changed" in diff:
            fc = diff["focus_changed"]
            lines.append(f"Focus changed: '{fc['from']}' → '{fc['to']}'")
        if "windows_opened" in diff:
            lines.append(f"Windows opened: {', '.join(diff['windows_opened'])}")
        if "windows_closed" in diff:
            lines.append(f"Windows closed: {', '.join(diff['windows_closed'])}")
        if "resource_delta" in diff:
            rd = diff["resource_delta"]
            lines.append(f"Resources: CPU {rd['cpu']}, RAM {rd['ram']}")
        if "browser_changed" in diff:
            bc = diff["browser_changed"]
            lines.append(f"Browser: tab '{bc['tab_from']}' → '{bc['tab_to']}'")
        return "\n".join(lines) if lines else "No significant changes."


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

        # 2. Harvest Open Windows (Optimized with fast Win32 EnumWindows)
        open_windows = []
        try:
            def enum_windows_callback(hwnd, extra):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd) or ""
                    if title:
                        try:
                            _, pid = win32process.GetWindowThreadProcessId(hwnd)
                            proc = psutil.Process(pid)
                            proc_name = proc.name().replace(".exe", "").lower()
                        except Exception:
                            proc_name = "unknown"
                        open_windows.append({"title": title, "process": proc_name, "hwnd": hwnd})
                return True

            win32gui.EnumWindows(enum_windows_callback, None)
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
