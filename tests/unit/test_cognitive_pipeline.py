"""
Tests for the Phase 1 cognitive pipeline:
  - GoalModel dataclass
  - GoalUnderstandingLayer
  - GroundingLayer
  - KnowledgeGapEngine
"""

import pytest
from unittest.mock import MagicMock, patch

from jarvis.perception.perception_packet import (
    GoalModel, PerceptionPacket, Utterance, ContextSnapshot,
)
from jarvis.perception.goal_understanding import GoalUnderstandingLayer
from jarvis.perception.grounding_layer import GroundingLayer
from jarvis.perception.knowledge_gap_engine import KnowledgeGapEngine, KnowledgeGap


# ── GoalModel Tests ────────────────────────────────────

class TestGoalModel:
    """Tests for the GoalModel dataclass."""

    def test_default_values(self):
        goal = GoalModel()
        assert goal.primary_goal == ""
        assert goal.intents == []
        assert goal.constraints == []
        assert goal.target_app is None
        assert goal.confidence == 1.0
        assert goal.is_complete is True
        assert goal.knowledge_gaps == []

    def test_custom_values(self):
        goal = GoalModel(
            primary_goal="Search for ROS2 tutorials",
            intents=["web_search", "content_generation"],
            constraints=["use python"],
            target_app="chrome",
            confidence=0.95,
        )
        assert goal.primary_goal == "Search for ROS2 tutorials"
        assert "web_search" in goal.intents
        assert goal.target_app == "chrome"

    def test_goal_model_on_perception_packet(self):
        """GoalModel should be attachable to PerceptionPacket."""
        goal = GoalModel(primary_goal="test goal")
        packet = PerceptionPacket(
            utterance=Utterance(text="test"),
            goal_model=goal,
        )
        assert packet.goal_model is not None
        assert packet.goal_model.primary_goal == "test goal"

    def test_goal_model_default_none_on_packet(self):
        """GoalModel should default to None on PerceptionPacket."""
        packet = PerceptionPacket(utterance=Utterance(text="test"))
        assert packet.goal_model is None


# ── GoalUnderstandingLayer Tests ───────────────────────

class TestGoalUnderstandingLayer:
    """Tests for GoalUnderstandingLayer."""

    def test_no_router_returns_minimal_goal(self):
        layer = GoalUnderstandingLayer(router=None)
        goal = layer.understand("open notepad")
        assert goal.primary_goal == "open notepad"
        assert "app_interaction" in goal.intents
        assert goal.target_app == "notepad"
        assert goal.confidence == 0.6

    def test_empty_text_returns_empty_goal(self):
        layer = GoalUnderstandingLayer(router=None)
        goal = layer.understand("")
        assert goal.primary_goal == ""
        assert goal.confidence == 0.0

    def test_minimal_goal_search_intent(self):
        layer = GoalUnderstandingLayer(router=None)
        goal = layer.understand("search for python tutorials")
        assert "web_search" in goal.intents

    def test_minimal_goal_write_intent(self):
        layer = GoalUnderstandingLayer(router=None)
        goal = layer.understand("write a summary about AI")
        assert "content_generation" in goal.intents

    def test_minimal_goal_system_control(self):
        layer = GoalUnderstandingLayer(router=None)
        goal = layer.understand("set volume to 50")
        assert "system_control" in goal.intents

    def test_minimal_goal_close_app(self):
        layer = GoalUnderstandingLayer(router=None)
        goal = layer.understand("close settings")
        assert "app_interaction" in goal.intents
        assert goal.target_app == "settings"

    def test_app_context_used_as_fallback(self):
        layer = GoalUnderstandingLayer(router=None)
        goal = layer.understand("do something", app_context="notepad")
        assert goal.target_app == "notepad"

    def test_llm_goal_extraction(self):
        """Test LLM-based goal extraction with mocked router."""
        mock_router = MagicMock()
        mock_backend = MagicMock()
        mock_backend.name = "test"
        mock_backend._call_llm_closed_loop.return_value = '{"primary_goal": "Find ROS2 tutorials on GitHub", "intents": ["web_search"], "constraints": [], "target_app": "chrome", "required_knowledge": [], "confidence": 0.95}'
        mock_router._primary = mock_backend
        mock_router._fallback = None
        mock_router._emergency = None
        mock_router._clean_and_parse_json.return_value = {
            "primary_goal": "Find ROS2 tutorials on GitHub",
            "intents": ["web_search"],
            "constraints": [],
            "target_app": "chrome",
            "required_knowledge": [],
            "confidence": 0.95,
        }

        layer = GoalUnderstandingLayer(router=mock_router)
        goal = layer.understand("Search for ROS2 on GitHub")
        assert goal.primary_goal == "Find ROS2 tutorials on GitHub"
        assert "web_search" in goal.intents
        assert goal.target_app == "chrome"
        assert goal.confidence == 0.95


# ── GroundingLayer Tests ───────────────────────────────

class TestGroundingLayer:
    """Tests for GroundingLayer."""

    def test_no_ambiguous_references(self):
        grounding = GroundingLayer()
        goal = GoalModel(primary_goal="open notepad")
        result = grounding.ground(goal)
        assert result.resolved_references == {}
        assert result.primary_goal == "open notepad"

    def test_resolve_it_from_context(self):
        grounding = GroundingLayer()
        goal = GoalModel(primary_goal="close it")
        snapshot = ContextSnapshot(active_app="notepad", active_window_title="Untitled - Notepad")
        result = grounding.ground(goal, snapshot=snapshot)
        assert "it" in result.resolved_references
        assert result.resolved_references["it"] == "notepad"
        assert result.target_app == "notepad"

    def test_resolve_the_app_from_context(self):
        grounding = GroundingLayer()
        goal = GoalModel(primary_goal="minimize the app")
        snapshot = ContextSnapshot(active_app="chrome", active_window_title="Google Chrome")
        result = grounding.ground(goal, snapshot=snapshot)
        assert "the app" in result.resolved_references
        assert result.resolved_references["the app"] == "chrome"

    def test_no_snapshot_leaves_unresolved(self):
        grounding = GroundingLayer()
        goal = GoalModel(primary_goal="close it")
        result = grounding.ground(goal, snapshot=None)
        # Without snapshot, "it" cannot be resolved by context
        # It stays unresolved (no router either)
        assert result.primary_goal == "close it"

    def test_resolve_again_from_episodic(self):
        mock_episodic = MagicMock()
        mock_episodic.as_llm_context.return_value = "open notepad → SUCCESS (skill: open_app)"
        grounding = GroundingLayer(episodic=mock_episodic)
        goal = GoalModel(primary_goal="do that again")
        result = grounding.ground(goal)
        assert "again" in result.resolved_references


# ── KnowledgeGapEngine Tests ──────────────────────────

class TestKnowledgeGapEngine:
    """Tests for KnowledgeGapEngine."""

    def test_complete_goal_no_gaps(self):
        engine = KnowledgeGapEngine()
        goal = GoalModel(
            primary_goal="open notepad",
            intents=["app_interaction"],
            target_app="notepad",
            confidence=0.9,
        )
        result = engine.check(goal)
        assert not result.clarification_needed
        assert len(result.gaps) == 0

    def test_low_confidence_triggers_gap(self):
        engine = KnowledgeGapEngine(confidence_threshold=0.5)
        goal = GoalModel(
            primary_goal="maybe open something",
            confidence=0.3,
        )
        result = engine.check(goal)
        assert result.has_gaps
        assert any(g.parameter == "goal_clarity" for g in result.gaps)

    def test_empty_goal_triggers_gap(self):
        engine = KnowledgeGapEngine()
        goal = GoalModel(primary_goal="")
        result = engine.check(goal)
        assert result.clarification_needed
        assert any(g.parameter == "primary_goal" for g in result.gaps)

    def test_missing_target_app_for_app_interaction(self):
        engine = KnowledgeGapEngine()
        goal = GoalModel(
            primary_goal="do something with files",
            intents=["app_interaction"],
            target_app=None,
            confidence=0.9,
        )
        result = engine.check(goal)
        assert result.has_gaps
        assert any(g.parameter == "target_app" for g in result.gaps)

    def test_target_app_inferable_from_text(self):
        engine = KnowledgeGapEngine()
        goal = GoalModel(
            primary_goal="write code in vscode",
            intents=["app_interaction", "text_edit"],
            target_app=None,
            confidence=0.9,
        )
        result = engine.check(goal)
        # vscode is in the known apps list, so it should be inferable
        target_app_gaps = [g for g in result.gaps if g.parameter == "target_app"]
        assert len(target_app_gaps) == 0

    def test_fill_gap_updates_goal(self):
        engine = KnowledgeGapEngine()
        goal = GoalModel(
            primary_goal="open something",
            knowledge_gaps=["target_app"],
        )
        updated = engine.fill_gap(goal, "target_app", "notepad")
        assert updated.target_app == "notepad"
        assert "target_app" not in updated.knowledge_gaps

    def test_required_knowledge_creates_optional_gaps(self):
        engine = KnowledgeGapEngine()
        goal = GoalModel(
            primary_goal="check the weather",
            intents=["web_search"],
            required_knowledge=["current_weather_data"],
            confidence=0.9,
        )
        result = engine.check(goal)
        knowledge_gaps = [g for g in result.gaps if g.parameter.startswith("knowledge_")]
        assert len(knowledge_gaps) == 1
        assert knowledge_gaps[0].severity == "optional"

    def test_is_complete_flag_updated(self):
        engine = KnowledgeGapEngine()
        goal = GoalModel(
            primary_goal="",
            confidence=0.9,
        )
        result = engine.check(goal)
        assert not result.goal.is_complete
