"""
Unit Tests for Phase 4: Generator-Critic Peer Review Auditor and agent wiring
"""

import pytest
from unittest.mock import MagicMock, patch

from jarvis.agents.agent_result import AgentResult
from jarvis.agents.memory.agent_local_memory import AgentLocalMemory
from jarvis.agents.memory.shared_context import SharedAgentContext
from jarvis.agents.agent_interface import AgentInterface
from jarvis.agents.agent_bus import AgentBus, FunctionalAgentWrapper
from jarvis.agents.peer_review import PeerReviewAuditor, AuditResult


class TestPeerReviewAuditor:
    """Tests for the PeerReviewAuditor."""

    def test_static_safety_audit_blocks_destructive_commands(self):
        auditor = PeerReviewAuditor()
        
        # Destructive command
        res = auditor.audit("rm -rf /usr/local", "test_agent")
        assert res.accepted is False
        assert "CRITICAL SAFETY VIOLATION" in res.feedback

        # Safe command
        res_safe = auditor.audit("echo 'hello'", "test_agent")
        assert res_safe.accepted is True

    def test_semantic_llm_audit_accepts(self):
        mock_router = MagicMock()
        mock_decision = MagicMock()
        mock_decision.message = '{"accepted": true, "confidence": 0.95, "feedback": "Looks great!"}'
        mock_router.decide_for_task.return_value = mock_decision

        auditor = PeerReviewAuditor(router=mock_router)
        res = auditor.audit("print('hello')", "test_agent")
        
        assert res.accepted is True
        assert res.confidence == 0.95
        assert res.feedback == "Looks great!"


class TestAgentBusPeerReviewWiring:
    """Tests for the AgentBus wiring with Generator-Critic loop."""

    def test_run_single_without_audit(self):
        bus = AgentBus()
        
        # Simple functional agent (no audit required)
        agent = FunctionalAgentWrapper(
            name="simple_agent",
            fn=lambda task, ctx, lm, sh: "Output content",
            description="Simple agent",
            audit_required=False
        )
        bus.register(agent)
        
        res = bus.run_single("simple_agent", "Do task", {})
        assert res.success is True
        assert res.output == "Output content"

    def test_run_single_with_audit_success(self):
        bus = AgentBus()
        
        # Agent requiring audit
        agent = FunctionalAgentWrapper(
            name="audited_agent",
            fn=lambda task, ctx, lm, sh: "Valid code output",
            description="Audited agent",
            audit_required=True
        )
        bus.register(agent)

        mock_router = MagicMock()
        mock_decision = MagicMock()
        mock_decision.message = '{"accepted": true, "confidence": 0.9, "feedback": "Acceptable"}'
        mock_router.decide.return_value = mock_decision

        res = bus.run_single("audited_agent", "Write code", {"_router": mock_router})
        assert res.success is True
        assert res.output == "Valid code output"
        mock_router.decide_for_task.assert_called_once()

    def test_run_single_with_audit_fail_then_success(self):
        bus = AgentBus()
        
        calls = 0
        def agent_fn(task, ctx, lm, sh):
            nonlocal calls
            calls += 1
            if calls == 1:
                return "Incorrect output"
            return "Corrected output"

        agent = FunctionalAgentWrapper(
            name="regenerated_agent",
            fn=agent_fn,
            description="Regenerating agent",
            audit_required=True
        )
        bus.register(agent)

        mock_router = MagicMock()
        
        # 1st call fails, 2nd call accepts
        mock_decision_1 = MagicMock()
        mock_decision_1.message = '{"accepted": false, "confidence": 0.4, "feedback": "Fix syntax error"}'
        mock_decision_2 = MagicMock()
        mock_decision_2.message = '{"accepted": true, "confidence": 0.95, "feedback": "Correct"}'
        mock_router.decide_for_task.side_effect = [mock_decision_1, mock_decision_2]

        res = bus.run_single("regenerated_agent", "Write code", {"_router": mock_router})
        
        assert res.success is True
        assert res.output == "Corrected output"
        assert calls == 2  # Proves regeneration was triggered with feedback
        assert mock_router.decide_for_task.call_count == 2
