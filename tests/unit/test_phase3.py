"""
Unit Tests for Phase 3: Five-Tier World Model and State Manager
"""

import pytest
from jarvis.brain.world_state import (
    FiveTierWorldState, EnvironmentState, UIState, KnowledgeState, TaskState, AgentState, WorldState
)
from jarvis.brain.state_manager import StateManager


class TestFiveTierWorldState:
    """Tests for the FiveTierWorldState and backwards compatibility mapping."""

    def test_default_instantiation(self):
        ws = FiveTierWorldState()
        assert isinstance(ws.env_state, EnvironmentState)
        assert isinstance(ws.ui_state, UIState)
        assert isinstance(ws.knowledge_state, KnowledgeState)
        assert isinstance(ws.task_state, TaskState)
        assert isinstance(ws.agent_state, AgentState)

    def test_backwards_compatibility_properties(self):
        # Instantiate old-style WorldState
        old_ws = WorldState(
            active_window={"title": "Settings", "process": "systemsettings.exe"},
            running_processes=["explorer", "notepad"],
            open_windows=[{"title": "Settings", "process": "systemsettings.exe"}],
            system_resources={"cpu": 15, "ram": 45},
            browser_state={"profile": "Default", "tab_title": "Google", "tab_url": "https://google.com"}
        )

        # Assert property mapping works
        assert old_ws.active_window["title"] == "Settings"
        assert "explorer" in old_ws.running_processes
        assert old_ws.system_resources["cpu"] == 15
        assert old_ws.browser_state["tab_title"] == "Google"

        # Check setters
        old_ws.active_window = {"title": "Notepad"}
        assert old_ws.ui_state.active_window["title"] == "Notepad"

    def test_diff_and_to_llm_context(self):
        ws_before = FiveTierWorldState()
        ws_after = FiveTierWorldState()

        # Update environment CPU and active window
        ws_before.ui_state.active_window = {"title": "Notepad"}
        ws_after.ui_state.active_window = {"title": "Chrome"}
        ws_after.env_state.system_resources = {"cpu": 50, "ram": 50}

        diff = FiveTierWorldState.diff(ws_before, ws_after)
        assert "focus_changed" in diff
        assert diff["focus_changed"]["from"] == "Notepad"
        assert diff["focus_changed"]["to"] == "Chrome"
        
        diff_text = FiveTierWorldState.diff_to_text(diff)
        assert "Focus changed" in diff_text


class TestStateManager:
    """Tests for the StateManager."""

    def test_state_manager_updates_and_rollback(self):
        ws = FiveTierWorldState()
        mgr = StateManager(initial_state=ws)

        # Update task state logs
        mgr.update_state("task", {"progress_logs": ["Action 1 executed"]})
        assert "Action 1 executed" in mgr.get_current_state().task_state.progress_logs

        # Update knowledge variables
        mgr.update_state("knowledge", {"variables": {"session_var": "val1"}})
        assert mgr.get_current_state().knowledge_state.variables["session_var"] == "val1"

        # Rollback once (removes knowledge update)
        restored_1 = mgr.rollback()
        assert restored_1 is not None
        assert "Action 1 executed" in restored_1.task_state.progress_logs
        assert "session_var" not in restored_1.knowledge_state.variables

        # Rollback again (removes task update)
        restored_2 = mgr.rollback()
        assert restored_2 is not None
        assert "Action 1 executed" not in restored_2.task_state.progress_logs
        assert "session_var" not in restored_2.knowledge_state.variables
