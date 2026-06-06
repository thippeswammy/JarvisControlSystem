import pytest
import os
import json
from unittest.mock import MagicMock, patch, PropertyMock
from jarvis.perception.nlu import NLU
from jarvis.perception.perception_packet import Utterance, PerceptionPacket
from jarvis.brain.closed_loop_engine import ClosedLoopEngine, ClosedLoopResult
from jarvis.llm.llm_interface import ClosedLoopDecision, SkillCallSpec
from jarvis.skills.skill_bus import SkillBus, SkillCall, SkillResult
from jarvis.utils.app_finder import AppFinder
from jarvis.agents.agent_bus import AgentBus
from jarvis.mcp.mcp_bus import MCPBus

# ── 1. NLU Context Routing Tests ─────────────────────────────────

def test_nlu_context_routing_ambiguous_and_pronouns():
    # Mock LLM router
    router = MagicMock()
    # Mock backend to return custom JSON
    mock_backend = MagicMock()
    router._primary = mock_backend
    router._fallback = None
    router._emergency = None
    
    # Mock clean and parse JSON method
    router._clean_and_parse_json.side_effect = lambda raw: json.loads(raw)
    
    # Utterance: 'open history' when active app context is empty (ambiguous)
    # Should route to 'llm_route'
    mock_backend._call_llm_closed_loop.return_value = json.dumps({
        "intent": "llm_route",
        "entities": {"target": "history"},
        "intent_category": "EXECUTION",
        "compound": False,
        "sub_commands": []
    })
    
    nlu = NLU(router=router)
    packet = nlu.parse(Utterance("open history"), app_context="")
    assert packet.intent == "llm_route"
    assert packet.intent_category == "EXECUTION"

# ── 2. ClosedLoopEngine Loop Prevention Tests ────────────────────

def test_closed_loop_engine_loop_prevention():
    # Mock router, bus, contexts
    router = MagicMock()
    bus = SkillBus()
    
    # Register a dummy skill
    from jarvis.skills.skill_decorator import skill
    @skill(triggers=["type"], name="type_text", category="keyboard")
    def mock_type(params):
        return SkillResult(success=True, action_taken="typed")
        
    bus.register(mock_type)
    bus._discovered = True
    
    # LLM decision returns a repeated type_text action in closed loop
    router.decide_closed_loop.return_value = ClosedLoopDecision(
        status="in_progress",
        reasoning="I will type hello",
        actions=[SkillCallSpec(skill="type_text", params={"text": "hello"})]
    )
    
    harvester = MagicMock()
    harvester.capture.return_value = MagicMock()
    
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
    
    # Run loop
    packet = MagicMock()
    snapshot = MagicMock()
    snapshot.interface = "text"
    snapshot.active_app = "notepad"
    
    # We patch _sense_world_state to return dummy state quickly
    with patch.object(engine, "_sense_world_state") as mock_sense:
        from jarvis.brain.world_state import WorldState
        mock_sense.return_value = WorldState(
            active_window={"title": "Notepad", "process": "notepad.exe"},
            running_processes=[],
            open_windows=[],
            system_resources={"cpu": 0, "ram": 0}
        )
        
        result = engine.run(
            goal="type hello",
            packet=packet,
            initial_snapshot=snapshot
        )
        
        # Verify it halted and completed is False
        assert result.completed is False
        assert "Action loop detected" in result.summary or "repeated more than 3 times" in result.summary
        # Iterations should be at most 4
        assert result.iterations <= 4

# ── 3. AppFinder Dynamic Scan Filtering Tests ──────────────────

@patch("os.path.exists")
@patch("pathlib.Path.is_file")
def test_app_finder_filters_non_executables(mock_is_file, mock_exists):
    mock_exists.return_value = True
    mock_is_file.return_value = True
    
    # Mock the directory list and glob output
    from pathlib import Path
    mock_files = [
        Path("C:\\Users\\thipp\\AppData\\Local\\com.grammarly.web-client\\EBWebView\\Default\\History"),
        Path("C:\\Users\\thipp\\AppData\\Local\\notepad.exe")
    ]
    
    with patch.object(AppFinder, "_check_registry_app_path", return_value=None), \
         patch.object(AppFinder, "_scan_start_menu_shortcuts", return_value=None), \
         patch("shutil.which", return_value=None), \
         patch("os.environ", {"PATHEXT": ".EXE;.BAT;.CMD"}), \
         patch("pathlib.Path.glob") as mock_glob:
         
        def mock_glob_side_effect(pattern):
            base = pattern.split("/")[-1]
            return [f for f in mock_files if f.name.lower() == base.lower()]
            
        mock_glob.side_effect = mock_glob_side_effect
        
        # Searching for 'history' (which matches the file 'History' but it's not an executable)
        # Should return None
        path = AppFinder.find_exe_path("history")
        assert path is None

        # Searching for 'notepad' (which matches notepad.exe)
        # Should return notepad.exe
        path = AppFinder.find_exe_path("notepad")
        assert path == os.path.abspath("C:\\Users\\thipp\\AppData\\Local\\notepad.exe")

# ── 4. AgentBus / MCPBus Redundant Discovery Skipping Tests ──────

def test_bus_discovery_skipping():
    # Test AgentBus
    agent_bus = AgentBus()
    agent_bus._discovered = True
    agent_bus._registry = {"dummy_agent": MagicMock()}
    
    # Call discover: it should return the registry count immediately without clearing or scanning
    with patch.object(agent_bus, "_discover_builtins") as mock_builtins:
        count = agent_bus.discover()
        assert count == 1
        mock_builtins.assert_not_called()
        
    # Test MCPBus
    mcp_bus = MCPBus()
    mcp_bus._discovered = True
    mcp_bus._registry = {"dummy_mcp": MagicMock()}
    
    with patch("pathlib.Path.exists", return_value=True), \
         patch("yaml.safe_load", return_value=[]):
        count = mcp_bus.discover()
        assert count == 1
