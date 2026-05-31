"""
Unit Tests for Phase 2: Capability Planning, safety gating (Execution Authority),
and User Interaction.
"""

import pytest
from unittest.mock import MagicMock, patch

from jarvis.perception.perception_packet import GoalModel
from jarvis.skills.skill_bus import SkillCall, SkillResult
from jarvis.brain.interaction_adapter import (
    InteractionAdapter, AdapterRegistry, TelegramInteractionAdapter, TUIInteractionAdapter
)
from jarvis.brain.user_interaction_manager import UserInteractionManager
from jarvis.brain.capability_planner import CapabilityPlanner
from jarvis.brain.execution_authority import ExecutionAuthority


# ── InteractionAdapter & Registry Tests ─────────────────

class TestInteractionAdapterAndRegistry:
    """Tests for InteractionAdapter ABC, concrete adapters, and registry."""

    def test_registry_registration_and_retrieval(self):
        registry = AdapterRegistry()
        mock_tg_channel = MagicMock()
        tg_adapter = TelegramInteractionAdapter(channel_adapter=mock_tg_channel)
        
        registry.register(tg_adapter)
        assert registry.get_adapter("telegram") == tg_adapter
        assert registry.get_adapter("tui") is None

    def test_registry_active_adapter_inference(self):
        registry = AdapterRegistry()
        mock_tg_channel = MagicMock()
        tg_adapter = TelegramInteractionAdapter(channel_adapter=mock_tg_channel)
        registry.register(tg_adapter)

        # telegram:12345 should resolve to telegram adapter
        active = registry.get_active_adapter("telegram:12345")
        assert active == tg_adapter

        # telegram-test:12345 should also resolve to telegram adapter
        active_test = registry.get_active_adapter("telegram-test:12345")
        assert active_test == tg_adapter

    def test_wait_for_response_with_registered_session(self):
        mock_tg_channel = MagicMock()
        tg_adapter = TelegramInteractionAdapter(channel_adapter=mock_tg_channel)
        
        # Mock session with event queue
        mock_session = MagicMock()
        mock_session.id = "telegram:123"
        mock_event = MagicMock()
        mock_event.text = "yes, go ahead"
        mock_session.event_queue.get.return_value = mock_event

        tg_adapter.register_session(mock_session)
        response = tg_adapter.wait_for_response("telegram:123", timeout=1.0)
        
        assert response == "yes, go ahead"
        mock_session.event_queue.get.assert_called_once_with(timeout=1.0)


# ── UserInteractionManager Tests ────────────────────────

class TestUserInteractionManager:
    """Tests for UserInteractionManager."""

    def test_prompt_clarification_sends_and_receives(self):
        registry = AdapterRegistry()
        mock_adapter = MagicMock()
        mock_adapter.adapter_type = "telegram"
        mock_adapter.wait_for_response.return_value = "use notepad"
        registry.register(mock_adapter)

        manager = UserInteractionManager(registry=registry)
        response = manager.prompt_clarification("telegram:123", "Which editor?")
        
        mock_adapter.send_message.assert_called_once_with("telegram:123", "Which editor?")
        assert response == "use notepad"

    def test_request_confirmation_accepts(self):
        registry = AdapterRegistry()
        mock_adapter = MagicMock()
        mock_adapter.adapter_type = "telegram"
        mock_adapter.wait_for_response.return_value = "Yes, proceed"
        registry.register(mock_adapter)

        manager = UserInteractionManager(registry=registry)
        approved = manager.request_confirmation("telegram:123", "Delete system files")
        
        assert approved is True

    def test_request_confirmation_denies_on_negative_or_timeout(self):
        registry = AdapterRegistry()
        mock_adapter = MagicMock()
        mock_adapter.adapter_type = "telegram"
        
        # Test explicit deny
        mock_adapter.wait_for_response.return_value = "No, cancel"
        registry.register(mock_adapter)
        manager = UserInteractionManager(registry=registry)
        approved = manager.request_confirmation("telegram:123", "Delete system files")
        assert approved is False

        # Test timeout (wait_for_response returns None)
        mock_adapter.wait_for_response.return_value = None
        approved_timeout = manager.request_confirmation("telegram:123", "Delete system files")
        assert approved_timeout is False


# ── CapabilityPlanner Tests ────────────────────────────

class TestCapabilityPlanner:
    """Tests for CapabilityPlanner."""

    def test_resolve_capabilities(self):
        planner = CapabilityPlanner()
        goal = GoalModel(
            primary_goal="Search web and generate text",
            intents=["web_search", "content_generation"]
        )
        caps = planner.resolve_capabilities(goal)
        assert "web_access" in caps
        assert "text_generation" in caps

    def test_select_providers(self):
        planner = CapabilityPlanner()
        providers = planner.select_providers(["web_access", "text_edit"])
        
        assert len(providers) == 2
        assert providers[0]["provider_name"] == "browser_agent"
        assert providers[0]["provider_type"] == "agent"
        assert providers[1]["provider_name"] == "type_text"
        assert providers[1]["provider_type"] == "skill"

    def test_update_provider_health(self):
        planner = CapabilityPlanner()
        
        # Should start at 1.0, decay on failure
        planner.update_provider_health("browser_agent", success=False)
        assert planner.provider_health["browser_agent"] == 0.8
        
        # Boost on success
        planner.update_provider_health("browser_agent", success=True)
        assert planner.provider_health["browser_agent"] == 0.85


# ── ExecutionAuthority Tests ───────────────────────────

class TestExecutionAuthority:
    """Tests for ExecutionAuthority."""

    def test_evaluate_risk_safe_plan(self):
        auth = ExecutionAuthority()
        plan = [
            SkillCall(skill="chat_reply", params={}),
            SkillCall(skill="open_app", params={"app": "notepad"})
        ]
        assert auth.evaluate_risk(plan) == "SAFE"

    def test_evaluate_risk_moderate_plan(self):
        auth = ExecutionAuthority()
        plan = [
            SkillCall(skill="open_app", params={"app": "notepad"}),
            SkillCall(skill="close_app", params={})
        ]
        assert auth.evaluate_risk(plan) == "MODERATE"

    def test_evaluate_risk_high_plan(self):
        auth = ExecutionAuthority()
        plan = [
            SkillCall(skill="run_shell", params={"cmd": "dir"}),
        ]
        assert auth.evaluate_risk(plan) == "HIGH"

    def test_evaluate_risk_contextual_key_press(self):
        auth = ExecutionAuthority()
        
        # Safe keypress
        plan_safe = [SkillCall(skill="press_key", params={"key": "a"})]
        assert auth.evaluate_risk(plan_safe) == "MODERATE"
        
        # Destructive keypress
        plan_destructive = [SkillCall(skill="press_key", params={"key": "delete"})]
        assert auth.evaluate_risk(plan_destructive) == "HIGH"

    def test_validate_safe_plan_auto_approves(self):
        auth = ExecutionAuthority(full_autonomy=False)
        plan = [SkillCall(skill="chat_reply", params={})]
        assert auth.validate(plan) is True

    def test_validate_high_risk_prompts_user(self):
        auth = ExecutionAuthority(full_autonomy=False)
        plan = [SkillCall(skill="run_shell", params={"cmd": "rm -rf"})]
        
        mock_im = MagicMock()
        mock_im.request_confirmation.return_value = True
        
        assert auth.validate(plan, interaction_manager=mock_im, session_id="telegram:123") is True
        mock_im.request_confirmation.assert_called_once()

    def test_validate_high_risk_full_autonomy_skips_prompt(self):
        auth = ExecutionAuthority(full_autonomy=True)
        plan = [SkillCall(skill="run_shell", params={"cmd": "rm -rf"})]
        
        mock_im = MagicMock()
        assert auth.validate(plan, interaction_manager=mock_im, session_id="telegram:123") is True
        mock_im.request_confirmation.assert_not_called()
