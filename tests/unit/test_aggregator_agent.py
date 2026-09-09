"""
tests/unit/test_aggregator_agent.py
====================================
Unit tests for jarvis.agents.builtin.aggregator_agent.AggregatorAgent.

The LLM router boundary is mocked via context["llm_router"] (checked by the
agent before it lazy-imports/constructs a real LLMRouter).
"""
from unittest.mock import MagicMock

import pytest

from jarvis.agents.agent_result import AgentResult
from jarvis.agents.builtin.aggregator_agent import AggregatorAgent
from jarvis.agents.memory.agent_local_memory import AgentLocalMemory

pytestmark = pytest.mark.unit


def make_memory():
    return AgentLocalMemory(agent_name="aggregator_agent")


def make_pipeline_results():
    return {
        "t1": AgentResult(success=True, output="Found 3 articles about Python.", agent_name="search_agent"),
        "t2": AgentResult(success=False, output="Timed out generating code.", agent_name="code_agent"),
    }


def test_normal_aggregation_of_multiple_results_uses_llm_synthesis():
    """With multiple sub-agent results and a working LLM, the synthesized
    LLM message is returned verbatim as the final output."""
    agent = AggregatorAgent()
    mock_router = MagicMock()
    mock_router.decide.return_value = MagicMock(message="Here is your summary: 3 articles found, code generation failed.")

    context = {"llm_router": mock_router, "__pipeline_results__": make_pipeline_results()}
    result = agent.run("Summarize my research task", context, make_memory(), MagicMock())

    assert result.success is True
    assert result.output == "Here is your summary: 3 articles found, code generation failed."
    assert result.agent_name == "aggregator_agent"

    mock_router.decide.assert_called_once()
    _, kwargs = mock_router.decide.call_args
    assert "Summarize my research task" in kwargs["prompt"]
    assert "Task ID: t1" in kwargs["context"]
    assert "Task ID: t2" in kwargs["context"]
    assert "SUCCESS" in kwargs["context"]
    assert "FAILED" in kwargs["context"]


def test_empty_results_list_short_circuits_without_calling_llm():
    """When there are no sub-agent results to aggregate, the agent returns a
    fixed message immediately and never invokes the LLM router."""
    agent = AggregatorAgent()
    mock_router = MagicMock()

    context = {"llm_router": mock_router, "__pipeline_results__": {}}
    result = agent.run("Aggregate nothing", context, make_memory(), MagicMock())

    assert result.success is True
    assert result.output == "No task results were provided for aggregation."
    mock_router.decide.assert_not_called()


def test_missing_pipeline_results_key_short_circuits_without_calling_llm():
    """When context has no '__pipeline_results__' key at all, behavior matches
    the empty-results case (defaults to an empty dict)."""
    agent = AggregatorAgent()
    mock_router = MagicMock()

    context = {"llm_router": mock_router}
    result = agent.run("Aggregate nothing", context, make_memory(), MagicMock())

    assert result.success is True
    assert result.output == "No task results were provided for aggregation."
    mock_router.decide.assert_not_called()


def test_llm_call_exception_falls_back_to_textual_merge():
    """If router.decide() raises, the exception is caught and a deterministic
    textual merge of the sub-agent results is returned instead."""
    agent = AggregatorAgent()
    mock_router = MagicMock()
    mock_router.decide.side_effect = RuntimeError("LLM backend down")

    memory = make_memory()
    context = {"llm_router": mock_router, "__pipeline_results__": make_pipeline_results()}
    result = agent.run("Summarize results", context, memory, MagicMock())

    assert result.success is True
    assert "Summarize results" in result.output
    assert "[search_agent] Task t1: Found 3 articles about Python." in result.output
    assert "[code_agent] Task t2: Timed out generating code." in result.output
    assert "✓" in result.output  # success checkmark for t1
    assert "✗" in result.output  # failure cross for t2
    assert any("LLM synthesis failed" in step for step in memory.exec_log)


def test_llm_returns_empty_message_falls_back_to_textual_merge():
    """If the LLM call succeeds but returns no usable message, the agent also
    falls back to the textual merge rather than returning an empty output."""
    agent = AggregatorAgent()
    mock_router = MagicMock()
    mock_router.decide.return_value = MagicMock(message="")

    context = {"llm_router": mock_router, "__pipeline_results__": make_pipeline_results()}
    result = agent.run("Summarize results", context, make_memory(), MagicMock())

    assert result.success is True
    assert "[search_agent] Task t1: Found 3 articles about Python." in result.output
    assert "[code_agent] Task t2: Timed out generating code." in result.output
