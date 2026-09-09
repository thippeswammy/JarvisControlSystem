"""
tests/unit/test_ui_windows_agent.py
=====================================
Unit tests for jarvis.agents.builtin.ui_windows_agent.UIWindowsAgent.

The two external boundaries — mcp_bus.call(...) (dispatch to the ui_windows
MCP server) and router.decide(...) (LLM decisions) — are both mocked via the
context dict, which UIWindowsAgent checks before constructing real instances.
"""
import itertools
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from jarvis.agents.builtin.ui_windows_agent import UIWindowsAgent
from jarvis.agents.memory.agent_local_memory import AgentLocalMemory

pytestmark = pytest.mark.unit


def make_memory():
    return AgentLocalMemory(agent_name="ui_windows_agent")


def test_no_router_available_returns_immediate_failure_without_calling_mcp():
    """If no router is supplied and LLMRouter.from_config() also fails, the
    agent must fail fast with a clear message and never touch the MCP bus."""
    agent = UIWindowsAgent()
    mock_mcp_bus = MagicMock()

    with patch(
        "jarvis.llm.llm_router.LLMRouter.from_config",
        side_effect=RuntimeError("no config in test env"),
    ):
        result = agent.run("open calculator", {"mcp_bus": mock_mcp_bus}, make_memory(), MagicMock())

    assert result.success is False
    assert result.output == "LLM router is not available."
    mock_mcp_bus.call.assert_not_called()


def test_successful_dispatch_completes_when_llm_reports_chat_done():
    """Happy path: MCP lists windows, the LLM targets the window, one DOM
    capture happens, and the LLM immediately reports the goal is complete."""
    agent = UIWindowsAgent()

    mock_mcp_bus = MagicMock()

    def mcp_call(server, tool, params):
        assert server == "ui_windows"
        if tool == "list_windows":
            return {"windows": [{"title": "Notepad"}]}
        if tool == "get_dom":
            assert params.get("app_title") == "Notepad"
            return {"dom_text": "<dom>...</dom>"}
        raise AssertionError(f"unexpected tool call: {tool}")

    mock_mcp_bus.call.side_effect = mcp_call

    mock_router = MagicMock()
    mock_router.decide.side_effect = [
        SimpleNamespace(steps=[SimpleNamespace(skill="target_window", params={"app_title": "Notepad"})]),
        SimpleNamespace(type="chat", message="Task complete!", steps=None),
    ]

    context = {"mcp_bus": mock_mcp_bus, "llm_router": mock_router}
    result = agent.run("type hello in notepad", context, make_memory(), MagicMock())

    assert result.success is True
    assert result.output == "Task complete!"
    assert mock_router.decide.call_count == 2


def test_get_dom_timeout_is_caught_and_returned_as_failed_result():
    """An exception raised by mcp_bus.call for get_dom (simulating an MCP
    timeout/transport error) must be caught and converted into a controlled
    failed AgentResult rather than propagating out of run()."""
    agent = UIWindowsAgent()

    mock_mcp_bus = MagicMock()

    def mcp_call(server, tool, params):
        if tool == "list_windows":
            return {"windows": [{"title": "Calculator"}]}
        if tool == "get_dom":
            raise TimeoutError("Timed out waiting for DOM snapshot")
        raise AssertionError(f"unexpected tool call: {tool}")

    mock_mcp_bus.call.side_effect = mcp_call

    # Target-selection LLM call fails too; the agent must fall back to the
    # keyword-based targeting heuristic ("calculator" -> "Calculator"),
    # which finds the window already running and skips launching it.
    mock_router = MagicMock()
    mock_router.decide.side_effect = RuntimeError("LLM backend overloaded")

    context = {"mcp_bus": mock_mcp_bus, "llm_router": mock_router}
    result = agent.run("open calculator and press 5", context, make_memory(), MagicMock())

    assert result.success is False
    assert result.output == "Error retrieving DOM: Timed out waiting for DOM snapshot"
    # launch_app must never be called since Calculator was already running.
    launch_calls = [c for c in mock_mcp_bus.call.call_args_list if c.args[1] == "launch_app"]
    assert launch_calls == []


def test_llm_decide_failure_inside_action_loop_is_caught_and_returned():
    """Once DOM capture succeeds, a second failure point is the per-step
    router.decide() call; an exception there must also be converted into a
    controlled failed AgentResult (a distinct code path from the DOM-capture
    failure above)."""
    agent = UIWindowsAgent()

    mock_mcp_bus = MagicMock()

    def mcp_call(server, tool, params):
        if tool == "list_windows":
            return {"windows": [{"title": "Calculator"}]}
        if tool == "get_dom":
            return {"dom_text": "<dom>...</dom>"}
        raise AssertionError(f"unexpected tool call: {tool}")

    mock_mcp_bus.call.side_effect = mcp_call

    mock_router = MagicMock()
    mock_router.decide.side_effect = [
        SimpleNamespace(steps=[SimpleNamespace(skill="target_window", params={"app_title": "Calculator"})]),
        RuntimeError("model overloaded"),
    ]

    context = {"mcp_bus": mock_mcp_bus, "llm_router": mock_router}
    result = agent.run("open calculator and compute 2+2", context, make_memory(), MagicMock())

    assert result.success is False
    assert result.output == "LLM decision failure: model overloaded"


def test_loop_terminates_with_failure_after_reaching_max_steps():
    """If the LLM keeps returning actionable plan steps and never signals
    'chat' (done), the closed loop must not run forever — it stops at
    max_steps (10) and reports failure."""
    agent = UIWindowsAgent()

    mock_mcp_bus = MagicMock()

    def mcp_call(server, tool, params):
        if tool == "list_windows":
            return {"windows": [{"title": "App"}]}
        if tool == "get_dom":
            return {"dom_text": "<dom/>"}
        if tool == "click":
            return {"success": True, "dom_delta": {"changed": True, "modified": {}}}
        raise AssertionError(f"unexpected tool call: {tool}")

    mock_mcp_bus.call.side_effect = mcp_call

    target_decision = SimpleNamespace(steps=[SimpleNamespace(skill="target_window", params={"app_title": "App"})])
    loop_decision = SimpleNamespace(type="plan", steps=[SimpleNamespace(skill="click", params={"element_id": "btn"})])
    mock_router = MagicMock()
    mock_router.decide.side_effect = itertools.chain([target_decision], itertools.repeat(loop_decision))

    shared = MagicMock()
    context = {"mcp_bus": mock_mcp_bus, "llm_router": mock_router}
    result = agent.run("click the button repeatedly", context, make_memory(), shared)

    assert result.success is False
    assert result.output == "Reached maximum steps before completing task."
    # 1 target-selection call + 10 loop-iteration calls.
    assert mock_router.decide.call_count == 11
    click_calls = [c for c in mock_mcp_bus.call.call_args_list if c.args[1] == "click"]
    assert len(click_calls) == 10
    assert shared.observe.called
