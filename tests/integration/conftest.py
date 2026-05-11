"""
tests/integration/conftest.py — Integration fixtures
=====================================================
Heavier fixtures that bootstrap real subsystems with mocked I/O.
"""
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(scope="session")
def bootstrapped_gateway(tmp_path_factory):
    """
    A single GatewayDaemon bootstrapped once for the whole integration session.
    - SemanticEncoder.embed → None (no Ollama)
    - LLMRouter._check_backend → True (skips health check network calls)
    """
    tmp_db = str(tmp_path_factory.mktemp("db") / "jarvis_integration.db")

    with patch("jarvis.memory.semantic_encoder.SemanticEncoder.embed", return_value=None), \
         patch("jarvis.llm.llm_router.LLMRouter._check_backend", return_value=True):
        from jarvis.gateway.gateway import GatewayDaemon
        from jarvis.llm.llm_interface import LLMDecision

        gw = GatewayDaemon()
        gw.bootstrap()

        # Override router.decide for stable responses
        gw.router.decide = MagicMock(return_value=LLMDecision(
            intent="chat_reply",
            reply="Integration test reply.",
            skills=[],
            confidence=1.0,
            raw={}
        ))
        yield gw
