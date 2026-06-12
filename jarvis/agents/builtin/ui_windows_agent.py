"""
UI Windows Agent
================
Built-in agent that delegates Windows UI automation tasks to the ui_windows
MCP server, executing action loops with per-step DOM verification.
"""

import json
import time
import logging
from typing import Any, Dict, List, Optional

from jarvis.agents.agent_interface import AgentInterface
from jarvis.agents.agent_result import AgentResult
from jarvis.agents.memory.agent_local_memory import AgentLocalMemory
from jarvis.agents.memory.shared_context import SharedAgentContext

logger = logging.getLogger(__name__)


class UIWindowsAgent(AgentInterface):
    """
    Built-in agent that controls and automates Windows desktop applications.
    """

    @property
    def name(self) -> str:
        return "ui_windows_agent"

    @property
    def description(self) -> str:
        return "Automates Windows desktop applications via UIA DOM capture and action execution loops."

    @property
    def parallel_safe(self) -> bool:
        # Interacts with physical desktop/GUI, so NOT safe to run concurrently with other UI actions.
        return False

    def run(
        self,
        task: str,
        context: dict,
        local_memory: AgentLocalMemory,
        shared: SharedAgentContext,
    ) -> AgentResult:
        local_memory.log_step(f"Starting UI Windows Automation for task: {task!r}")

        # 1. Retrieve or instantiate MCPBus
        mcp_bus = context.get("mcp_bus")
        if not mcp_bus:
            try:
                from jarvis.mcp.mcp_bus import MCPBus
                mcp_bus = MCPBus()
                mcp_bus.discover()
            except Exception as e:
                logger.error(f"[UIWindowsAgent] Failed to load MCPBus: {e}")
                return AgentResult(
                    success=False,
                    output=f"Failed to load MCPBus: {e}",
                    agent_name=self.name,
                    steps_taken=local_memory.exec_log.copy()
                )

        # 2. Retrieve LLM router
        router = context.get("llm_router") or context.get("router")
        if not router:
            try:
                from jarvis.llm.llm_router import LLMRouter
                router = LLMRouter.from_config()
            except Exception as e:
                logger.warning(f"[UIWindowsAgent] LLMRouter not in context, trying fallback: {e}")
                try:
                    from jarvis.llm.llm_router import LLMRouter
                    router = LLMRouter.from_config()
                except Exception:
                    pass

        if not router:
            return AgentResult(
                success=False,
                output="LLM router is not available.",
                agent_name=self.name,
                steps_taken=local_memory.exec_log.copy()
            )

        # 3. Get open windows list to determine target app
        try:
            windows_result = mcp_bus.call("ui_windows", "list_windows", {})
            windows = windows_result.get("windows", [])
        except Exception as e:
            logger.warning(f"[UIWindowsAgent] Failed to list windows: {e}")
            windows = []

        # 4. Target Application Selection
        app_title = None
        target_prompt = (
            "You are JARVIS, a Windows UI Automation Agent.\n"
            "Analyze the task and determine the target application window to automate.\n"
            f"User task: {task}\n"
            f"Currently open windows:\n{json.dumps(windows, indent=2)}\n\n"
            "If the application is already running, return its window title.\n"
            "If it is not running, specify the executable name or path to launch it.\n"
            "Output ONLY a JSON in LLMDecision format:\n"
            "{\n"
            "  \"type\": \"plan\",\n"
            "  \"steps\": [\n"
            "    {\"skill\": \"target_window\", \"params\": {\"app_title\": \"Window Title\"}}\n"
            "    // OR:\n"
            "    // {\"skill\": \"launch_app\", \"params\": {\"app_path\": \"calc.exe\", \"app_title\": \"Calculator\"}}\n"
            "  ]\n"
            "}"
        )

        try:
            decision = router.decide(task, target_prompt)
            if decision and decision.steps:
                step = decision.steps[0]
                if step.skill == "launch_app":
                    app_path = step.params.get("app_path", "calc.exe")
                    app_title = step.params.get("app_title")
                    local_memory.log_step(f"Launching application: {app_path}")
                    mcp_bus.call("ui_windows", "launch_app", {"app_path": app_path})
                    time.sleep(2.0)
                elif step.skill == "target_window":
                    app_title = step.params.get("app_title")
        except Exception as e:
            logger.warning(f"[UIWindowsAgent] LLM failed targeting decision: {e}. Applying fallbacks.")

        # Robust fallbacks for targeting
        if not app_title:
            task_lower = task.lower()
            if "calculator" in task_lower or "calc" in task_lower:
                app_title = "Calculator"
                calc_running = any("calculator" in w.get("title", "").lower() for w in windows)
                if not calc_running:
                    local_memory.log_step("Calculator window not found. Starting calc.exe...")
                    mcp_bus.call("ui_windows", "launch_app", {"app_path": "calc.exe"})
                    time.sleep(2.5)

        local_memory.log_step(f"Targeting window matching title: {app_title!r}")

        # 5. Closed Loop UI Control Loop
        step_count = 0
        max_steps = 10
        action_history = []
        warning_msg = ""

        while step_count < max_steps:
            step_count += 1
            local_memory.log_step(f"Loop step {step_count}/{max_steps}")

            # 5a. Capture current DOM
            try:
                dom_result = mcp_bus.call("ui_windows", "get_dom", {
                    "app_title": app_title,
                    "mode": "FULL"
                })
                dom_text = dom_result.get("dom_text", "")
            except Exception as e:
                logger.error(f"[UIWindowsAgent] Failed to retrieve DOM: {e}")
                return AgentResult(
                    success=False,
                    output=f"Error retrieving DOM: {e}",
                    agent_name=self.name,
                    steps_taken=local_memory.exec_log.copy()
                )

            if not dom_text:
                logger.warning("[UIWindowsAgent] Received empty DOM text from server.")

            # 5b. Formulate prompt for next action
            system_prompt = (
                "You are JARVIS, an autonomous Windows UI Automation Agent.\n"
                f"Your goal is to accomplish this task: {task}\n"
                f"Target application window: {app_title}\n"
                f"Actions executed so far: {action_history}\n"
            )
            if warning_msg:
                system_prompt += f"ATTENTION: {warning_msg}\n"
                warning_msg = ""

            system_prompt += (
                "\nHere is the active application's UI DOM:\n"
                f"{dom_text}\n\n"
                "Determine the next single action to take. Select from these allowed tools:\n"
                "- click (params: {\"element_id\": \"...\"})\n"
                "- type_text (params: {\"element_id\": \"...\", \"text\": \"...\"})\n"
                "- set_value (params: {\"element_id\": \"...\", \"value\": \"...\"})\n"
                "- invoke (params: {\"element_id\": \"...\"})\n"
                "- read_value (params: {\"element_id\": \"...\"})\n\n"
                "If the goal has been fully met, return type 'chat' with a clear summary message.\n"
                "Otherwise, return type 'plan' with the next step in the 'steps' array."
            )

            prompt = "Determine the next action."
            try:
                decision = router.decide(prompt, system_prompt)
            except Exception as e:
                logger.error(f"[UIWindowsAgent] LLM decide loop failed: {e}")
                return AgentResult(
                    success=False,
                    output=f"LLM decision failure: {e}",
                    agent_name=self.name,
                    steps_taken=local_memory.exec_log.copy()
                )

            if not decision:
                return AgentResult(
                    success=False,
                    output="LLM returned no decision.",
                    agent_name=self.name,
                    steps_taken=local_memory.exec_log.copy()
                )

            if decision.type == "chat":
                # Success!
                local_memory.log_step(f"Goal met! {decision.message}")
                return AgentResult(
                    success=True,
                    output=decision.message or "UI Automation task completed.",
                    agent_name=self.name,
                    steps_taken=local_memory.exec_log.copy()
                )

            if decision.type == "plan" and decision.steps:
                step = decision.steps[0]
                action_name = step.skill
                params = step.params
                element_id = params.get("element_id")

                local_memory.log_step(f"Executing step: {action_name} on {element_id}")

                # Guarantee app_title parameter is included
                if "app_title" not in params and app_title:
                    params["app_title"] = app_title

                try:
                    # Run action
                    action_res = mcp_bus.call("ui_windows", action_name, params)
                    success = action_res.get("success", False)
                    dom_delta = action_res.get("dom_delta", {})

                    action_history.append(f"{action_name}({element_id}) -> success={success}, changed={dom_delta.get('changed')}")

                    # Verify per-action DOM changes
                    if not success or not dom_delta.get("changed", False):
                        warning_msg = (
                            f"Action '{action_name}' on '{element_id}' did not cause any UI changes. "
                            "Verify the element exists, is enabled, and supports the operation."
                        )
                        local_memory.log_step(f"Verification issue: {warning_msg}")

                    # Notify WorldStateModeler
                    shared.observe(
                        f"UI Windows Action: {action_name} on {element_id} | "
                        f"success={success}, changed={dom_delta.get('changed')}, "
                        f"modified={list(dom_delta.get('modified', {}).keys())}"
                    )

                except Exception as e:
                    logger.error(f"[UIWindowsAgent] Error running action {action_name}: {e}")
                    warning_msg = f"Action execution error: {e}"
            else:
                return AgentResult(
                    success=False,
                    output=f"Agent blocked or returned unhandled decision type: {decision.type}",
                    agent_name=self.name,
                    steps_taken=local_memory.exec_log.copy()
                )

        return AgentResult(
            success=False,
            output="Reached maximum steps before completing task.",
            agent_name=self.name,
            steps_taken=local_memory.exec_log.copy()
        )
