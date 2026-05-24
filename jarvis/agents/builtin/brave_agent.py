"""
Brave Agent
===========
Specialized autonomous agent for web browsing, profile management, tab operations,
and DOM-based interactions inside the Brave Browser using browser automation skills.
"""

import logging
from typing import Any
from jarvis.agents.agent_interface import AgentInterface
from jarvis.agents.agent_result import AgentResult
from jarvis.agents.memory.agent_local_memory import AgentLocalMemory
from jarvis.agents.memory.shared_context import SharedAgentContext

logger = logging.getLogger(__name__)

class BraveAgent(AgentInterface):
    """Specialized agent to automate the Brave Browser using dedicated Playwright/CDP APIs."""

    @property
    def name(self) -> str:
        return "brave_agent"

    @property
    def description(self) -> str:
        return "Automates the Brave browser, manages profiles, switches tabs, and clicks web elements."

    @property
    def parallel_safe(self) -> bool:
        return False  # browser control requires serialization

    def run(
        self,
        task: str,
        context: dict,
        local_memory: AgentLocalMemory,
        shared: SharedAgentContext,
    ) -> AgentResult:
        local_memory.log_step(f"Analyzing browser task: {task!r}")
        task_lower = task.lower().strip()

        # Retrieve router and skill bus
        bus = context.get("_bus")
        if not bus:
            from jarvis.skills.skill_bus import SkillBus
            bus = SkillBus()

        # Handle Profile Switching
        if "profile" in task_lower:
            profile_name = "Default"
            for word in task.split():
                if "person" in word.lower() or "profile" in word.lower() or word.isdigit():
                    profile_name = word.strip()
                    break
            
            local_memory.log_step(f"Dispatching profile switch to: {profile_name}")
            from jarvis.skills.skill_bus import SkillCall
            res = bus.dispatch(SkillCall(skill="open_brave_profile", params={"profile": profile_name}))
            return AgentResult(
                success=res.success,
                output=res.action_taken if res.success else f"Failed to switch profile: {res.message}",
                agent_name=self.name,
                steps_taken=local_memory.exec_log.copy()
            )

        # Handle Tab Switching
        if "tab" in task_lower:
            target_tab = ""
            if "switch" in task_lower or "open" in task_lower:
                parts = task_lower.split("tab")
                if len(parts) > 1:
                    target_tab = parts[1].replace("to", "").replace("in", "").strip()
            if not target_tab:
                target_tab = task_lower
                
            local_memory.log_step(f"Dispatching tab switch to: '{target_tab}'")
            from jarvis.skills.skill_bus import SkillCall
            res = bus.dispatch(SkillCall(skill="switch_browser_tab", params={"target": target_tab}))
            return AgentResult(
                success=res.success,
                output=res.action_taken if res.success else f"Failed to switch tab: {res.message}",
                agent_name=self.name,
                steps_taken=local_memory.exec_log.copy()
            )

        # Handle Selector Clicking
        if "click" in task_lower:
            selector = ""
            if "on" in task_lower:
                parts = task_lower.split("on")
                if len(parts) > 1:
                    selector = parts[1].strip()
            else:
                parts = task_lower.split("click")
                if len(parts) > 1:
                    selector = parts[1].strip()

            local_memory.log_step(f"Dispatching click selector to: '{selector}'")
            from jarvis.skills.skill_bus import SkillCall
            res = bus.dispatch(SkillCall(skill="click_web_element", params={"selector": selector}))
            return AgentResult(
                success=res.success,
                output=res.action_taken if res.success else f"Failed to click web element: {res.message}",
                agent_name=self.name,
                steps_taken=local_memory.exec_log.copy()
            )

        # General opening fallback
        local_memory.log_step("Opening Brave browser default profile...")
        from jarvis.skills.skill_bus import SkillCall
        res = bus.dispatch(SkillCall(skill="open_brave_profile", params={"profile": "Default"}))
        return AgentResult(
            success=res.success,
            output=res.action_taken if res.success else f"Failed to launch browser: {res.message}",
            agent_name=self.name,
            steps_taken=local_memory.exec_log.copy()
        )
