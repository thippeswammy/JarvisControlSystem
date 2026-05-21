"""
Unit Tests — NVIDIA Cloud LLM Backend
======================================
Verifies the initialization, health checks, planning, and decision parsing
of the NvidiaLLM backend using unittest mocks.
"""

import os
from unittest.mock import MagicMock, patch
import pytest

from jarvis.llm.backends.nvidia_llm import NvidiaLLM
from jarvis.llm.llm_interface import SkillCallSpec, LLMDecision


@pytest.fixture
def mock_openai():
    """Mock the openai.OpenAI client and its chat completions endpoint."""
    with patch("openai.OpenAI") as mock_class:
        mock_client = MagicMock()
        mock_class.return_value = mock_client
        yield mock_client


def test_nvidia_llm_init_defaults(monkeypatch):
    """Verify that NvidiaLLM initializes with correct defaults."""
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test-key-123")
    llm = NvidiaLLM()
    assert llm._model == "qwen/qwen3-coder-480b-a35b-instruct"
    assert llm._base_url == "https://integrate.api.nvidia.com/v1"
    assert llm._api_key == "nvapi-test-key-123"
    assert llm.name == "nvidia/qwen/qwen3-coder-480b-a35b-instruct"


def test_nvidia_llm_init_custom(monkeypatch):
    """Verify custom parameters are respected."""
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    llm = NvidiaLLM(
        model="custom-nim-model",
        api_key="custom-key",
        base_url="https://custom.nvidia.nim/v1",
        max_tokens=1000,
        temperature=0.5,
        top_p=0.9,
        timeout=15.0,
    )
    assert llm._model == "custom-nim-model"
    assert llm._base_url == "https://custom.nvidia.nim/v1"
    assert llm._api_key == "custom-key"
    assert llm._max_tokens == 1000
    assert llm._temperature == 0.5
    assert llm._top_p == 0.9
    assert llm._timeout == 15.0


def test_nvidia_llm_health_check_fail_no_key(monkeypatch):
    """Health check should return False if no API key is configured."""
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    llm = NvidiaLLM(api_key="")
    assert llm.health_check() is False


def test_nvidia_llm_health_check_success(mock_openai):
    """Health check should return True if the API call succeeds."""
    llm = NvidiaLLM(api_key="test-key")
    mock_openai.chat.completions.create.return_value = MagicMock()
    assert llm.health_check() is True
    mock_openai.chat.completions.create.assert_called_once()


def test_nvidia_llm_health_check_exception(mock_openai):
    """Health check should return False if the API call raises an exception."""
    llm = NvidiaLLM(api_key="test-key")
    mock_openai.chat.completions.create.side_effect = Exception("API error")
    assert llm.health_check() is False


def test_nvidia_llm_plan_success(mock_openai):
    """Verify that a valid plan response is parsed correctly."""
    llm = NvidiaLLM(api_key="test-key")
    
    # Mock a response containing JSON array of skill calls
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content='[{"skill": "open_app", "params": {"target": "notepad"}}]'))
    ]
    mock_openai.chat.completions.create.return_value = mock_response

    plan = llm.plan("open notepad")
    assert plan is not None
    assert len(plan) == 1
    assert isinstance(plan[0], SkillCallSpec)
    assert plan[0].skill == "open_app"
    assert plan[0].params == {"target": "notepad"}


def test_nvidia_llm_plan_invalid_json(mock_openai):
    """Verify that an invalid plan response returns None."""
    llm = NvidiaLLM(api_key="test-key")
    
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content='invalid json here'))
    ]
    mock_openai.chat.completions.create.return_value = mock_response

    plan = llm.plan("open notepad")
    assert plan is None


def test_nvidia_llm_decide_chat(mock_openai):
    """Verify that decide() parses chat decisions correctly."""
    llm = NvidiaLLM(api_key="test-key")
    
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content='{"type": "chat", "message": "Hello, human!"}'))
    ]
    mock_openai.chat.completions.create.return_value = mock_response

    decision = llm.decide("hi jarvis")
    assert decision is not None
    assert isinstance(decision, LLMDecision)
    assert decision.type == "chat"
    assert decision.message == "Hello, human!"
    assert decision.steps is None


def test_nvidia_llm_decide_plan(mock_openai):
    """Verify that decide() parses plan decisions correctly."""
    llm = NvidiaLLM(api_key="test-key")
    
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content='{"type": "plan", "steps": [{"skill": "click_element", "params": {"x": 100, "y": 200}}]}'))
    ]
    mock_openai.chat.completions.create.return_value = mock_response

    decision = llm.decide("click screen")
    assert decision is not None
    assert isinstance(decision, LLMDecision)
    assert decision.type == "plan"
    assert len(decision.steps) == 1
    assert decision.steps[0].skill == "click_element"
    assert decision.steps[0].params == {"x": 100, "y": 200}
