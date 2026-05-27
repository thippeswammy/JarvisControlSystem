"""
Planner Agent
=============
Builtin agent that uses the LLM (or robust rule-based fallbacks) to decompose
a complex request into a structured dependency TaskGraph.
"""

import json
import logging
import re
from typing import Any, Optional

from jarvis.agents.agent_interface import AgentInterface
from jarvis.agents.agent_result import AgentResult
from jarvis.agents.memory.agent_local_memory import AgentLocalMemory
from jarvis.agents.memory.shared_context import SharedAgentContext
from jarvis.agents.task_graph import AgentTask, TaskGraph

logger = logging.getLogger(__name__)


class PlannerAgent(AgentInterface):
    """Builtin Planner Agent that decomposes complex tasks into a TaskGraph."""

    @property
    def name(self) -> str:
        return "planner_agent"

    @property
    def description(self) -> str:
        return "Decomposes a complex request into a TaskGraph of sub-agent tasks."

    @property
    def parallel_safe(self) -> bool:
        return True

    def run(
        self,
        task: str,
        context: dict,
        local_memory: AgentLocalMemory,
        shared: SharedAgentContext,
    ) -> AgentResult:
        local_memory.log_step(f"Planning decomposition for task: {task!r}")

        # 1. Get available agents catalog
        agent_catalog = context.get("agent_catalog", "")
        if not agent_catalog and "agent_bus" in context:
            agent_catalog = context["agent_bus"].get_agent_catalog()

        # 2. Formulate system prompt
        fallback_agents = "- search_agent: search web\n- code_agent: run python code"
        agents_str = agent_catalog or fallback_agents
        system_prompt = (
            "You are the Jarvis Task Decomposer (Planner Agent).\n"
            "Given a complex task and a list of available agents, decompose it into a TaskGraph of sub-tasks.\n"
            "Respond ONLY with a valid JSON object matching the following schema:\n"
            "{\n"
            "  \"tasks\": [\n"
            "    {\n"
            "      \"id\": \"t1\",\n"
            "      \"agent\": \"agent_name_from_catalog\",\n"
            "      \"task\": \"specific task description for this agent\",\n"
            "      \"depends_on\": []\n"
            "    }\n"
            "  ]\n"
            "}\n\n"
            f"Available Agents:\n{agents_str}\n\n"
            "Example Decomposition:\n"
            "For \"Search for Python guides and write code in code_agent\":\n"
            "{\n"
            "  \"tasks\": [\n"
            "    {\"id\": \"t1\", \"agent\": \"search_agent\", \"task\": \"find Python guides\", \"depends_on\": []},\n"
            "    {\"id\": \"t2\", \"agent\": \"code_agent\", \"task\": \"write Python code using guides\", \"depends_on\": [\"t1\"]}\n"
            "  ]\n"
            "}\n"
        )

        # 3. Retrieve LLM router
        router = context.get("llm_router") or context.get("router")
        if not router:
            try:
                from jarvis.llm.llm_router import LLMRouter
                router = LLMRouter.from_config()
            except Exception:
                pass

        if router:
            try:
                local_memory.log_step("Querying LLM for task decomposition...")
                decision = router.decide(task, system_prompt)

                response_text = decision.message or ""
                # Attempt to extract JSON block
                json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group(0))
                    tasks_data = data.get("tasks", [])
                    task_graph = TaskGraph()
                    for t in tasks_data:
                        task_graph.add_task(
                            AgentTask(
                                id=t["id"],
                                agent=t["agent"],
                                task=t["task"],
                                depends_on=t.get("depends_on", []),
                            )
                        )

                    local_memory.log_step(
                        f"LLM successfully decomposed task into {len(task_graph.tasks)} sub-tasks."
                    )
                    return AgentResult(
                        success=True,
                        output=f"Successfully decomposed task into {len(task_graph.tasks)} sub-tasks.",
                        agent_name=self.name,
                        steps_taken=local_memory.exec_log.copy(),
                        data=task_graph,
                    )
            except Exception as exc:
                logger.warning(
                    f"[PlannerAgent] LLM planning failed: {exc}. Using rule-based fallback."
                )
                local_memory.log_step(
                    f"LLM planning failed ({exc}). Using rule-based decomposition."
                )

        # Heuristic/rule-based fallback
        task_graph = TaskGraph()
        task_lower = task.lower()
        if "search" in task_lower and "code" in task_lower:
            task_graph.add_task(
                AgentTask(id="t1", agent="search_agent", task=f"Search related to: {task}")
            )
            task_graph.add_task(
                AgentTask(
                    id="t2",
                    agent="code_agent",
                    task=f"Write code based on search results for: {task}",
                    depends_on=["t1"],
                )
            )
        elif "search" in task_lower:
            task_graph.add_task(AgentTask(id="t1", agent="search_agent", task=task))
        else:
            task_graph.add_task(AgentTask(id="t1", agent="code_agent", task=task))

        local_memory.log_step(
            f"Fallback generated task graph with {len(task_graph.tasks)} tasks."
        )
        return AgentResult(
            success=True,
            output=f"Decomposed task via fallback into {len(task_graph.tasks)} tasks.",
            agent_name=self.name,
            steps_taken=local_memory.exec_log.copy(),
            data=task_graph,
        )
