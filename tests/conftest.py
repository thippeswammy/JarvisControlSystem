"""
tests/conftest.py — Root shared fixtures
========================================
Shared across unit, integration, and regression test layers.
"""
import sys
import os
import pytest
from unittest.mock import MagicMock, patch

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Enable Mock fallback during tests
os.environ["JARVIS_ALLOW_MOCK"] = "true"



# ── Database fixture ─────────────────────────────────────────

@pytest.fixture
def tmp_db_path(tmp_path):
    """A temporary file path for a fresh SQLite database."""
    return str(tmp_path / "jarvis_test.db")


# ── Memory fixture ───────────────────────────────────────────

@pytest.fixture
def mock_memory(tmp_db_path):
    """
    A real MemoryManager backed by a fresh temp SQLite DB.
    SemanticEncoder.embed is patched to return None immediately.
    """
    with patch("jarvis.memory.semantic_encoder.SemanticEncoder.embed", return_value=None):
        from jarvis.memory.memory_manager import MemoryManager
        mem = MemoryManager(tmp_db_path)
        yield mem


# ── LLM Router fixture ───────────────────────────────────────

@pytest.fixture
def mock_router():
    """
    A MagicMock that mimics LLMRouter.decide().
    Returns a minimal LLMDecision: chat_reply with empty skills list.
    """
    from jarvis.llm.llm_interface import LLMDecision
    router = MagicMock()
    router.decide.return_value = LLMDecision(
        intent="chat_reply",
        reply="Hello from mock.",
        skills=[],
        confidence=1.0,
        raw={}
    )
    router.status.return_value = {"local": True}
    return router


# ── SkillBus fixture ─────────────────────────────────────────

@pytest.fixture
def mock_bus():
    """A MagicMock SkillBus that returns an empty result list."""
    bus = MagicMock()
    bus.execute.return_value = []
    return bus


# ── Gateway fixture ──────────────────────────────────────────

@pytest.fixture
def mock_gateway(tmp_db_path, mock_router, mock_bus):
    """
    A bootstrapped GatewayDaemon with:
    - SemanticEncoder.embed mocked (no Ollama needed)
    - LLMRouter.decide mocked (predictable output)
    Returns the daemon after bootstrap().
    """
    with patch("jarvis.memory.semantic_encoder.SemanticEncoder.embed", return_value=None), \
         patch("jarvis.llm.llm_router.LLMRouter._check_backend", return_value=True):
        from jarvis.gateway.gateway import GatewayDaemon
        gw = GatewayDaemon()
        gw.bootstrap()
        # Override router with mock after bootstrap
        gw.router = mock_router
        yield gw
