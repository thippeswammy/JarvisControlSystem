import pytest
import os
import json
from unittest.mock import MagicMock, patch
from jarvis.perception.nlu import NLU
from jarvis.perception.perception_packet import Utterance
from jarvis.brain.closed_loop_engine import ClosedLoopEngine
from jarvis.llm.llm_interface import ClosedLoopDecision, SkillCallSpec
from jarvis.skills.skill_bus import SkillBus, SkillCall, SkillResult
from jarvis.agents.agent_bus import AgentBus
from jarvis.mcp.mcp_bus import MCPBus
from jarvis.brain.verification_loop import VerificationLoop
from jarvis.llm.llm_interface import LLMInterface

# ── TEST-030: Read Action Verification ────────────────────────────────
def test_test030_read_action_verification():
    harvester = MagicMock()
    # UIA state hash doesn't change
    harvester.harvest_and_hash.return_value = ("state", "hash123")
    
    comparator = MagicMock()
    recovery = MagicMock()
    
    loop = VerificationLoop(harvester, comparator, recovery)
    
    bus = MagicMock()
    bus.dispatch.return_value = SkillResult(success=True, action_taken="active window title")
    
    # get_active_window_title is in SKIP_VERIFY_SKILLS
    call = SkillCall(skill="get_active_window_title", params={})
    packet = MagicMock()
    snapshot = MagicMock()
    learner = MagicMock()
    
    res = loop.execute_and_verify(call, bus, packet, snapshot, learner)
    assert res.success is True
    assert res.action_taken == "active window title"
    # Harvester should NOT have been called since we skip verification
    harvester.harvest_and_hash.assert_not_called()


# ── TEST-031: Repeat Action Suppression ────────────────────────────────
def test_test031_repeat_action_suppression():
    router = MagicMock()
    bus = SkillBus()
    
    # Register a dummy skill
    from jarvis.skills.skill_decorator import skill
    @skill(triggers=["dummy"], name="dummy_mutation", category="test")
    def mock_dummy(params):
        return SkillResult(success=True, action_taken="mutated")
        
    bus.register(mock_dummy)
    bus._discovered = True
    
    # Decision returns same action repeatedly
    router.decide_closed_loop.return_value = ClosedLoopDecision(
        status="in_progress",
        reasoning="I will mutate",
        actions=[SkillCallSpec(skill="dummy_mutation", params={"x": 1})]
    )
    
    harvester = MagicMock()
    harvester.capture.return_value = MagicMock()
    # Mock verify to soft-pass
    harvester.harvest_and_hash.return_value = ("state", "hash123")
    
    episodic = MagicMock()
    temporal = MagicMock()
    
    engine = ClosedLoopEngine(
        router=router,
        bus=bus,
        context_harvester=harvester,
        episodic=episodic,
        temporal=temporal,
        max_iterations=10
    )
    
    packet = MagicMock()
    snapshot = MagicMock()
    snapshot.interface = "text"
    snapshot.active_app = "notepad"
    
    with patch.object(engine, "_sense_world_state") as mock_sense:
        from jarvis.brain.world_state import WorldState
        mock_sense.return_value = WorldState(
            active_window={"title": "Notepad", "process": "notepad.exe"},
            running_processes=[],
            open_windows=[],
            system_resources={"cpu": 0, "ram": 0}
        )
        
        result = engine.run(
            goal="run dummy",
            packet=packet,
            initial_snapshot=snapshot
        )
        
        # Verify it halted and completed is False
        assert result.completed is False
        assert "repeated more than 2 times" in result.summary
        # Loop limit is > 2, so it runs twice, and on the third time it fails before dispatch
        assert len(result.results) == 2


# ── TEST-032: Context Injection (NLU) ────────────────────────────────
def test_test032_context_injection_nlu():
    router = MagicMock()
    mock_backend = MagicMock()
    router._primary = mock_backend
    router._fallback = None
    router._emergency = None
    
    # NLU calls closed loop LLM
    mock_backend._call_llm_closed_loop.return_value = json.dumps({
        "intent": "llm_route",
        "entities": {"target": "history"},
        "intent_category": "EXECUTION",
        "compound": False,
        "sub_commands": []
    })
    router._clean_and_parse_json.side_effect = lambda raw: json.loads(raw)
    
    nlu = NLU(router=router)
    # With app_context="calculator", relative command routes to llm_route
    packet = nlu.parse(Utterance("in calculator open history"), app_context="calculator")
    assert packet.intent == "llm_route"
    assert packet.intent_category == "EXECUTION"


# ── TEST-033: Invalid JSON Recovery ──────────────────────────────────
def test_test033_invalid_json_recovery():
    # Test that _heal_json heals truncated/malformed JSON
    # Unclosed braces
    bad_json = '{"status": "in_progress", "reasoning": "thought", "actions": [{"skill": "type_text"'
    healed = LLMInterface._heal_json(bad_json)
    
    # Parse healed
    parsed = json.loads(healed)
    assert parsed["status"] == "in_progress"
    assert parsed["reasoning"] == "thought"
    assert isinstance(parsed["actions"], list)


# ── TEST-034: Agent/MCP Restart Stability ────────────────────────────
def test_test034_agent_mcp_restart_stability(caplog):
    # Test duplicate agent registration idempotency
    agent_bus = AgentBus()
    agent_mock = MagicMock()
    agent_mock.name = "test_agent"
    
    agent_bus.register(agent_mock)
    
    # Registering again should be silent and NOT log "Overriding" warning
    import logging
    with caplog.at_level(logging.WARNING):
        agent_bus.register(agent_mock)
        assert "Overriding existing agent" not in caplog.text

    # Test MCP registration idempotency
    mcp_bus = MCPBus()
    # Mocking registry
    mcp_server = MagicMock()
    mcp_server.name = "ui_windows"
    mcp_server.transport_type = "stdio"
    mcp_server.command = "python server.py"
    
    mcp_bus.register(mcp_server)
    
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        mcp_bus.register(mcp_server)
        assert "Overriding existing MCP server" not in caplog.text


# ── TEST-035: Goal Completion Detection ──────────────────────────────
def test_test035_goal_completion_detection():
    router = MagicMock()
    bus = SkillBus()
    
    # Decision returns status="done"
    router.decide_closed_loop.return_value = ClosedLoopDecision(
        status="done",
        reasoning="Task completed successfully.",
        summary="Task completed successfully.",
        actions=[]
    )
    
    harvester = MagicMock()
    episodic = MagicMock()
    temporal = MagicMock()
    
    engine = ClosedLoopEngine(
        router=router,
        bus=bus,
        context_harvester=harvester,
        episodic=episodic,
        temporal=temporal,
        max_iterations=10
    )
    
    packet = MagicMock()
    snapshot = MagicMock()
    snapshot.interface = "text"
    snapshot.active_app = "notepad"
    
    with patch.object(engine, "_sense_world_state") as mock_sense:
        from jarvis.brain.world_state import WorldState
        mock_sense.return_value = WorldState(
            active_window={"title": "Notepad", "process": "notepad.exe"},
            running_processes=[],
            open_windows=[],
            system_resources={"cpu": 0, "ram": 0}
        )
        
        result = engine.run(
            goal="do calculation",
            packet=packet,
            initial_snapshot=snapshot
        )
        
        # Verify it completed successfully and halted in 1 iteration (chat_reply dispatched)
        assert result.completed is True
        assert result.iterations == 1
        assert len(result.results) == 1
        assert "Goal COMPLETE" in result.summary or "completed successfully" in result.summary
