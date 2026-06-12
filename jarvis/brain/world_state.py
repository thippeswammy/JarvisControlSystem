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

from dataclasses import dataclass, field

@dataclass
class EnvironmentState:
    running_processes: List[str] = field(default_factory=list)
    system_resources: Dict[str, Any] = field(default_factory=dict)
    directory_trees: Dict[str, Any] = field(default_factory=dict)
    network_sockets: List[Dict[str, Any]] = field(default_factory=list)

    def to_llm_context(self) -> str:
        lines = [
            f"System Resources: CPU {self.system_resources.get('cpu', 0)}% | RAM {self.system_resources.get('ram', 0)}%"
        ]
        return "\n".join(lines)

    def diff(self, other: 'EnvironmentState') -> dict:
        result = {}
        cpu_before = self.system_resources.get("cpu", 0)
        cpu_after = other.system_resources.get("cpu", 0)
        ram_before = self.system_resources.get("ram", 0)
        ram_after = other.system_resources.get("ram", 0)
        if abs(cpu_after - cpu_before) > 5 or abs(ram_after - ram_before) > 3:
            result["resource_delta"] = {
                "cpu": f"{cpu_before}% → {cpu_after}%",
                "ram": f"{ram_before}% → {ram_after}%",
            }
        return result


@dataclass
class UIState:
    active_window: Dict[str, Any] = field(default_factory=dict)
    open_windows: List[Dict[str, Any]] = field(default_factory=list)
    browser_state: Optional[Dict[str, Any]] = None
    uia_tree_dump: Optional[str] = None
    dom_subtree: Optional[str] = None

    def to_llm_context(self) -> str:
        lines = [
            f"Active Foreground Window: {self.active_window.get('title', 'None')} (Process: {self.active_window.get('process', 'none')})",
            "Open Applications on Desktop:"
        ]
        for win in self.open_windows[:12]:
            lines.append(f"  • '{win.get('title')}' (Process: {win.get('process')})")
            
        if self.browser_state:
            lines.append("Active Web Browser Context:")
            lines.append(f"  • Profile: {self.browser_state.get('profile')}")
            lines.append(f"  • Active Tab Title: '{self.browser_state.get('tab_title')}'")
            lines.append(f"  • Active Tab URL: {self.browser_state.get('tab_url')}")
        return "\n".join(lines)

    def diff(self, other: 'UIState') -> dict:
        result = {}
        before_title = self.active_window.get("title", "")
        after_title = other.active_window.get("title", "")
        if before_title != after_title:
            result["focus_changed"] = {
                "from": before_title,
                "to": after_title,
            }

        before_wins = {w.get("title", "") for w in self.open_windows if w.get("title")}
        after_wins = {w.get("title", "") for w in other.open_windows if w.get("title")}
        opened = after_wins - before_wins
        closed = before_wins - after_wins
        if opened:
            result["windows_opened"] = sorted(opened)
        if closed:
            result["windows_closed"] = sorted(closed)

        if self.browser_state or other.browser_state:
            b_tab = (self.browser_state or {}).get("tab_title", "")
            a_tab = (other.browser_state or {}).get("tab_title", "")
            b_url = (self.browser_state or {}).get("tab_url", "")
            a_url = (other.browser_state or {}).get("tab_url", "")
            if b_tab != a_tab or b_url != a_url:
                result["browser_changed"] = {
                    "tab_from": b_tab,
                    "tab_to": a_tab,
                    "url_from": b_url,
                    "url_to": a_url,
                }
        return result


@dataclass
class KnowledgeState:
    semantic_retrievals: List[Dict[str, Any]] = field(default_factory=list)
    cached_search_results: List[Dict[str, Any]] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)

    def to_llm_context(self) -> str:
        if not self.variables:
            return ""
        return f"Knowledge Variables: {self.variables}"

    def diff(self, other: 'KnowledgeState') -> dict:
        result = {}
        added = {k: v for k, v in other.variables.items() if k not in self.variables}
        modified = {k: (self.variables[k], other.variables[k]) for k, v in other.variables.items() if k in self.variables and self.variables[k] != v}
        removed = {k: v for k, v in self.variables.items() if k not in other.variables}
        if added: result["variables_added"] = added
        if modified: result["variables_modified"] = modified
        if removed: result["variables_removed"] = removed
        return result


@dataclass
class TaskState:
    active_task_graph: Optional[Any] = None
    checkpoints: Dict[str, Any] = field(default_factory=dict)
    progress_logs: List[str] = field(default_factory=list)

    def to_llm_context(self) -> str:
        if not self.progress_logs:
            return ""
        return f"Task Progress: {self.progress_logs[-3:]}"

    def diff(self, other: 'TaskState') -> dict:
        result = {}
        if len(other.progress_logs) > len(self.progress_logs):
            result["new_logs"] = other.progress_logs[len(self.progress_logs):]
        return result


@dataclass
class AgentState:
    active_sub_agents: List[Dict[str, Any]] = field(default_factory=list)
    local_memory_stack: List[Any] = field(default_factory=list)
    provider_health: Dict[str, float] = field(default_factory=dict)

    def to_llm_context(self) -> str:
        if not self.active_sub_agents:
            return ""
        return f"Active Sub-agents: {self.active_sub_agents}"

    def diff(self, other: 'AgentState') -> dict:
        return {}


class FiveTierWorldState:
    """Represents a rich, modular 5-tier snapshot of the desktop/agent state."""
    
    def __init__(
        self,
        env_state: Optional[EnvironmentState] = None,
        ui_state: Optional[UIState] = None,
        knowledge_state: Optional[KnowledgeState] = None,
        task_state: Optional[TaskState] = None,
        agent_state: Optional[AgentState] = None
    ):
        self.env_state = env_state or EnvironmentState()
        self.ui_state = ui_state or UIState()
        self.knowledge_state = knowledge_state or KnowledgeState()
        self.task_state = task_state or TaskState()
        self.agent_state = agent_state or AgentState()

    # Backwards compatibility properties mapping to the new decoupled structures
    @property
    def active_window(self) -> Dict[str, Any]:
        return self.ui_state.active_window

    @active_window.setter
    def active_window(self, val: Dict[str, Any]) -> None:
        self.ui_state.active_window = val

    @property
    def running_processes(self) -> List[str]:
        return self.env_state.running_processes

    @running_processes.setter
    def running_processes(self, val: List[str]) -> None:
        self.env_state.running_processes = val

    @property
    def open_windows(self) -> List[Dict[str, Any]]:
        return self.ui_state.open_windows

    @open_windows.setter
    def open_windows(self, val: List[Dict[str, Any]]) -> None:
        self.ui_state.open_windows = val

    @property
    def system_resources(self) -> Dict[str, Any]:
        return self.env_state.system_resources

    @system_resources.setter
    def system_resources(self, val: Dict[str, Any]) -> None:
        self.env_state.system_resources = val

    @property
    def browser_state(self) -> Optional[Dict[str, Any]]:
        return self.ui_state.browser_state

    @browser_state.setter
    def browser_state(self, val: Optional[Dict[str, Any]]) -> None:
        self.ui_state.browser_state = val

    def to_llm_context(self) -> str:
        """Serializes the five-tier state layers into a clean format for LLM prompts."""
        parts = ["=== FIVE-TIER WORLD STATE ==="]
        parts.append(self.ui_state.to_llm_context())
        parts.append(self.env_state.to_llm_context())
        
        k_ctx = self.knowledge_state.to_llm_context()
        if k_ctx: parts.append(k_ctx)
        
        t_ctx = self.task_state.to_llm_context()
        if t_ctx: parts.append(t_ctx)
        
        a_ctx = self.agent_state.to_llm_context()
        if a_ctx: parts.append(a_ctx)
        
        return "\n".join(filter(None, parts))

    @staticmethod
    def diff(before: 'FiveTierWorldState', after: 'FiveTierWorldState') -> dict:
        """Computes semantic diff across all five state tiers."""
        result = {}
        
        ui_diff = before.ui_state.diff(after.ui_state)
        env_diff = before.env_state.diff(after.env_state)
        k_diff = before.knowledge_state.diff(after.knowledge_state)
        t_diff = before.task_state.diff(after.task_state)
        a_diff = before.agent_state.diff(after.agent_state)

        result.update(ui_diff)
        result.update(env_diff)
        if k_diff: result["knowledge"] = k_diff
        if t_diff: result["task"] = t_diff
        if a_diff: result["agent"] = a_diff

        if not result:
            result["no_change"] = True
        return result

    @staticmethod
    def diff_to_text(diff: dict) -> str:
        """Convert a 5-tier diff dict to human-readable text for LLM injection."""
        if diff.get("no_change"):
            return "No observable changes to the environment."
        
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
            
        if "knowledge" in diff:
            k = diff["knowledge"]
            lines.append(f"Knowledge changed: {k}")
        if "task" in diff:
            t = diff["task"]
            lines.append(f"Task progressed: {t}")
            
        return "\n".join(lines) if lines else "No significant changes."


class WorldState(FiveTierWorldState):
    """Represents a backwards-compatible snapshot of the OS and browser environments."""
    
    def __init__(
        self,
        active_window: Dict[str, Any],
        running_processes: List[str],
        open_windows: List[Dict[str, Any]],
        system_resources: Dict[str, Any],
        browser_state: Optional[Dict[str, Any]] = None
    ):
        env_state = EnvironmentState(running_processes=running_processes, system_resources=system_resources)
        ui_state = UIState(active_window=active_window, open_windows=open_windows, browser_state=browser_state)
        super().__init__(env_state=env_state, ui_state=ui_state)


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
