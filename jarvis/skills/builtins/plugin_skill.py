"""
Plugin Skill — Agent, Multiagent, and MCP Dispatcher
===================================================
Builtin skill that bridges the SkillBus with the AgentBus and MCPBus.
Allows the Planner to execute Agents and MCP tool calls through uniform SkillCalls.
"""

import asyncio
import logging
from typing import Any
from concurrent.futures import ThreadPoolExecutor
from jarvis.skills.skill_decorator import skill
from jarvis.skills.skill_bus import SkillResult

logger = logging.getLogger(__name__)


def _run_async_in_thread(coro) -> Any:
    """Run an async coroutine synchronously in an isolated thread to avoid event loop conflicts."""
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(asyncio.run, coro)
        return future.result()


@skill(
    triggers=["run agent", "execute agent", "spawn agent"],
    name="run_agent",
    category="agent",
    is_cognitive=True,
)
def run_agent(params: dict) -> SkillResult:
    """
    Spawns and executes a single named agent with a task.
    Required params: 'agent', 'task'.
    """
    agent_name = params.get("agent")
    task = params.get("task")
    agent_bus = params.get("_agent_bus")

    if not agent_name or not task:
        return SkillResult(
            success=False,
            message="Missing 'agent' or 'task' parameter for run_agent skill.",
        )

    if not agent_bus:
        return SkillResult(
            success=False,
            message="AgentBus not provided to run_agent skill.",
        )

    # Prepare context for the agent
    context = {
        "router": params.get("_router"),
        "llm_router": params.get("_router"),
        "agent_bus": agent_bus,
    }

    logger.info(f"[plugin_skill] Running agent '{agent_name}' for task: {task!r}")
    res = agent_bus.run_single(agent_name, task, context)

    return SkillResult(
        success=res.success,
        message=res.output,
        data=res.data,
        action_taken=f"Executed agent '{agent_name}'",
    )


@skill(
    triggers=["run agent pipeline", "execute task graph", "run multiagent"],
    name="run_agent_pipeline",
    category="agent",
    is_cognitive=True,
)
def run_agent_pipeline(params: dict) -> SkillResult:
    """
    Executes a multi-agent TaskGraph pipeline concurrently.
    Required params: 'tasks' (list of task dicts).
    """
    tasks_data = params.get("tasks")
    agent_bus = params.get("_agent_bus")

    if not tasks_data:
        return SkillResult(
            success=False,
            message="Missing 'tasks' parameter for run_agent_pipeline skill.",
        )

    if not agent_bus:
        return SkillResult(
            success=False,
            message="AgentBus not provided to run_agent_pipeline skill.",
        )

    from jarvis.agents.task_graph import AgentTask, TaskGraph

    try:
        # Reconstruct TaskGraph
        graph = TaskGraph()
        for t in tasks_data:
            graph.add_task(
                AgentTask(
                    id=t["id"],
                    agent=t["agent"],
                    task=t["task"],
                    depends_on=t.get("depends_on", []),
                )
            )

        # Prepare context
        context = {
            "router": params.get("_router"),
            "llm_router": params.get("_router"),
            "agent_bus": agent_bus,
        }

        # Run pipeline in a separate thread/loop to avoid collision
        logger.info(f"[plugin_skill] Executing agent pipeline with {len(tasks_data)} tasks.")
        coro = agent_bus.run_pipeline(graph, context)
        results = _run_async_in_thread(coro)

        # Aggregate the final outputs or check if aggregator was part of the graph
        aggregator_results = [r for r in results if r.agent_name == "aggregator_agent"]
        if aggregator_results:
            final_output = aggregator_results[-1].output
        else:
            # Fallback output
            final_output = "\n".join(
                [f"[{r.agent_name}] {r.output}" for r in results]
            )

        # If any agent task failed, treat the skill as failed
        success = all(r.success for r in results)

        return SkillResult(
            success=success,
            message=final_output,
            data=results,
            action_taken=f"Executed agent pipeline with {len(tasks_data)} tasks",
        )
    except Exception as exc:
        logger.exception(f"Error executing agent pipeline: {exc}")
        return SkillResult(
            success=False,
            message=f"Error executing agent pipeline: {exc}",
        )


@skill(
    triggers=["call mcp tool", "mcp tool call", "run mcp tool"],
    name="call_mcp_tool",
    category="mcp",
    is_cognitive=True,
)
def call_mcp_tool(params: dict) -> SkillResult:
    """
    Dispatches a tool call to a registered MCP server.
    Required params: 'server', 'tool', 'params'.
    """
    server = params.get("server")
    tool = params.get("tool")
    tool_params = params.get("params", {})
    mcp_bus = params.get("_mcp_bus")

    if not server or not tool:
        return SkillResult(
            success=False,
            message="Missing 'server' or 'tool' parameter for call_mcp_tool skill.",
        )

    if not mcp_bus:
        return SkillResult(
            success=False,
            message="MCPBus not provided to call_mcp_tool skill.",
        )

    logger.info(f"[plugin_skill] Calling MCP tool '{server}/{tool}' with params {tool_params}")
    res = mcp_bus.call(server, tool, tool_params)

    if "error" in res:
        return SkillResult(
            success=False,
            message=str(res["error"]),
            data=res,
            skill_name=f"{server}/{tool}",
        )

    output = str(res.get("result", res))
    return SkillResult(
        success=True,
        message=output,
        data=res,
        action_taken=f"Called MCP tool '{server}/{tool}'",
    )
