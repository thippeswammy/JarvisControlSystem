"""
tests/unit/test_planner_agent.py
=================================
Unit tests for jarvis.agents.builtin.planner_agent.PlannerAgent.

The LLM router boundary is mocked via context["llm_router"] (checked by the
agent before it lazy-imports/constructs a real LLMRouter), so no network or
config-file access is ever exercised.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from jarvis.agents.builtin.planner_agent import PlannerAgent
from jarvis.agents.memory.agent_local_memory import AgentLocalMemory

pytestmark = pytest.mark.unit


def make_memory():
    return AgentLocalMemory(agent_name="planner_agent")


def test_valid_llm_response_produces_correct_task_graph():
    """A well-formed JSON plan from the LLM is parsed into a matching TaskGraph."""
    agent = PlannerAgent()
    mock_router = MagicMock()
    mock_router.decide.return_value = SimpleNamespace(
        message=(
            '{"tasks": ['
            '{"id": "t1", "agent": "search_agent", "task": "find guides", "depends_on": []},'
            '{"id": "t2", "agent": "code_agent", "task": "write code", "depends_on": ["t1"]}'
            ']}'
        )
    )

    result = agent.run(
        "Search for Python guides and write code",
        {"llm_router": mock_router},
        make_memory(),
        MagicMock(),
    )

    assert result.success is True
    assert result.agent_name == "planner_agent"
    graph = result.data
    assert graph is not None
    assert len(graph.tasks) == 2
    assert graph.get_task("t1").agent == "search_agent"
    assert graph.get_task("t1").depends_on == []
    assert graph.get_task("t2").agent == "code_agent"
    assert graph.get_task("t2").depends_on == ["t1"]
    assert "2 sub-tasks" in result.output
    mock_router.decide.assert_called_once()


def test_valid_llm_response_uses_agent_catalog_from_context():
    """The agent catalog supplied via context is forwarded into the system prompt."""
    agent = PlannerAgent()
    mock_router = MagicMock()
    mock_router.decide.return_value = SimpleNamespace(
        message='{"tasks": [{"id": "t1", "agent": "custom_agent", "task": "do it", "depends_on": []}]}'
    )
    context = {
        "llm_router": mock_router,
        "agent_catalog": "- custom_agent: does custom things",
    }

    result = agent.run("do something custom", context, make_memory(), MagicMock())

    assert result.success is True
    assert result.data.get_task("t1").agent == "custom_agent"
    # The system prompt (2nd positional arg to decide) should mention the injected catalog.
    call_args = mock_router.decide.call_args
    system_prompt = call_args[0][1]
    assert "custom_agent: does custom things" in system_prompt


def test_non_json_llm_output_falls_back_to_heuristic_decomposition():
    """LLM output with no JSON object at all is not an exception path; the code
    falls through silently to the rule-based fallback decomposition."""
    agent = PlannerAgent()
    mock_router = MagicMock()
    mock_router.decide.return_value = SimpleNamespace(message="Sorry, I can't help with that.")

    result = agent.run(
        "please search for cats and write code to show them",
        {"llm_router": mock_router},
        make_memory(),
        MagicMock(),
    )

    assert result.success is True
    graph = result.data
    # Heuristic branch: task contains both "search" and "code" -> two dependent tasks.
    assert len(graph.tasks) == 2
    assert graph.get_task("t1").agent == "search_agent"
    assert graph.get_task("t2").agent == "code_agent"
    assert graph.get_task("t2").depends_on == ["t1"]
    assert "fallback" in result.output.lower()


def test_malformed_json_llm_output_is_caught_and_falls_back():
    """LLM output that contains braces but is not valid JSON triggers json.loads
    to raise; the exception is caught and the rule-based fallback is used."""
    agent = PlannerAgent()
    mock_router = MagicMock()
    mock_router.decide.return_value = SimpleNamespace(message="{this is not valid json}")

    memory = make_memory()
    result = agent.run("search for news", {"llm_router": mock_router}, memory, MagicMock())

    assert result.success is True
    graph = result.data
    # Heuristic branch: only "search" present -> single search_agent task.
    assert len(graph.tasks) == 1
    assert graph.get_task("t1").agent == "search_agent"
    # The exception path logs a specific failure step before falling back.
    assert any("LLM planning failed" in step for step in memory.exec_log)


def test_llm_json_missing_required_fields_is_caught_and_falls_back():
    """Valid JSON that is missing a required key (e.g. 'agent') raises a KeyError
    while building AgentTask objects; this must also be caught, not propagated."""
    agent = PlannerAgent()
    mock_router = MagicMock()
    mock_router.decide.return_value = SimpleNamespace(
        message='{"tasks": [{"id": "t1", "task": "missing the agent field"}]}'
    )

    result = agent.run("write some code please", {"llm_router": mock_router}, make_memory(), MagicMock())

    assert result.success is True
    # Heuristic branch: only "code" present -> single code_agent task.
    assert len(result.data.tasks) == 1
    assert result.data.get_task("t1").agent == "code_agent"


def test_empty_task_with_no_router_available_uses_pure_heuristic_fallback():
    """With no router in context and LLMRouter.from_config() unavailable, the
    agent must not crash on an empty task string and should produce the
    'else' heuristic branch: a single code_agent task."""
    agent = PlannerAgent()

    with patch(
        "jarvis.llm.llm_router.LLMRouter.from_config",
        side_effect=RuntimeError("no config available in test env"),
    ):
        result = agent.run("", {}, make_memory(), MagicMock())

    assert result.success is True
    assert len(result.data.tasks) == 1
    task = result.data.get_task("t1")
    assert task.agent == "code_agent"
    assert task.task == ""


def test_llm_decide_raising_exception_falls_back_to_heuristic():
    """If router.decide() itself raises (e.g. backend/network failure), the
    exception is caught and the heuristic fallback still produces a result."""
    agent = PlannerAgent()
    mock_router = MagicMock()
    mock_router.decide.side_effect = ConnectionError("LLM backend unreachable")

    memory = make_memory()
    result = agent.run("search the web", {"llm_router": mock_router}, memory, MagicMock())

    assert result.success is True
    assert len(result.data.tasks) == 1
    assert result.data.get_task("t1").agent == "search_agent"
    assert any("LLM planning failed" in step for step in memory.exec_log)
