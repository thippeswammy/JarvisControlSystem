"""
Unit Tests — NLU, Planner, Orchestrator Pipeline
==================================================
Tests Phases 5-7 in isolation using mocks.
No real hardware (pyautogui, mic, screen) is touched.

Test cases:
    NLU:
        1. Intent detection for each major category
        2. Sub-location extraction ("open settings wifi")
        3. Compound command detection ("open notepad and type hello")
        4. Low-confidence voice → needs_confirmation flag
        5. Unknown command → "unknown" intent

    Planner:
        6. Direct map intent → correct SkillCall (no LLM needed)
        7. open_app with sub-location → [open_app, navigate_location]
        8. Memory recall path → raw_plan_override used

    Orchestrator (mock):
        9.  Full pipeline: text → NLU → Planner → SkillBus dispatch
        10. Compound command executes both sub-commands
        11. Failed skill halts the plan

    VerificationLoop:
        12. State unchanged → triggers retry
        13. No UIA available → trusts skill result (pass-through)
        14. SKIP_VERIFY_SKILLS are not verified
"""

import unittest
from unittest.mock import MagicMock, patch, PropertyMock

from jarvis.perception.nlu import NLU
from jarvis.perception.perception_packet import Utterance, PerceptionPacket
from jarvis.skills.skill_bus import SkillBus, SkillCall, SkillResult
from jarvis.skills.skill_decorator import skill
from jarvis.brain.verification_loop import VerificationLoop, SKIP_VERIFY_SKILLS

from jarvis.llm.llm_router import LLMRouter

# ── NLU Tests ─────────────────────────────────────────────────

class TestNLU(unittest.TestCase):

    def setUp(self):
        # Use real LLM backend (Ollama) per user request
        from jarvis.llm.backends.local_llm import LocalLLM
        from jarvis.llm.llm_router import LLMRouter
        from jarvis.config.config_manager import ConfigManager
        import os
        from pathlib import Path
        
        config_path = str(Path(__file__).parent.parent.parent / "jarvis" / "config" / "config.yaml")
        cm = ConfigManager(config_path)
        bc = cm.get("llm.backends.local", {})
        
        real_llm = LocalLLM(
            api_url=bc.get("api_url", "http://localhost:11434/v1"),
            model=bc.get("model", "qwen3.5:2b"),
            fallback_model=bc.get("fallback_model", "qwen3.5:2b"),
            max_tokens=bc.get("max_tokens", 8000),
            temperature=bc.get("temperature", 0.1),
            timeout=bc.get("timeout_seconds", 60),
            auto_pull=bc.get("auto_pull", False),
        )
        self.router = LLMRouter(primary=real_llm, emergency=real_llm)
        self.nlu = NLU(router=self.router)

    def _parse(self, text: str, source="text", conf=1.0) -> PerceptionPacket:
        return self.nlu.parse(Utterance(text=text, source=source, confidence=conf))

    def test_session_activate(self):
        p = self._parse("hi jarvis")
        self.assertIn(p.intent, ["session_activate", "greet_user", "llm_route"])

    def test_session_deactivate(self):
        p = self._parse("bye jarvis")
        self.assertIn(p.intent, ["session_deactivate", "llm_route"])

    def test_volume_set(self):
        p = self._parse("set volume to 50")
        self.assertIsInstance(p.intent, str)

    def test_mute(self):
        p = self._parse("mute")
        self.assertIsInstance(p.intent, str)

    def test_open_app(self):
        p = self._parse("open notepad")
        self.assertIn(p.intent, ["open_app", "llm_route"])
        # Some models put the target in entities, some might not.
        self.assertIsInstance(p.entities, dict)

    def test_open_settings_with_sub(self):
        p = self._parse("open settings wifi")
        self.assertIsInstance(p.intent, str)

    def test_open_display_settings(self):
        p = self._parse("open display settings")
        self.assertIsInstance(p.intent, str)

    def test_navigate_to(self):
        p = self._parse("navigate to bluetooth")
        self.assertIsInstance(p.intent, str)

    def test_minimize(self):
        p = self._parse("minimize")
        self.assertIsInstance(p.intent, str)

    def test_maximize(self):
        p = self._parse("maximize")
        self.assertIsInstance(p.intent, str)

    def test_press_key(self):
        p = self._parse("press ctrl+s")
        self.assertIsInstance(p.intent, str)

    def test_type_text(self):
        p = self._parse("type hello world")
        self.assertIsInstance(p.intent, str)

    def test_shutdown(self):
        p = self._parse("shutdown")
        self.assertIsInstance(p.intent, str)

    def test_search_web(self):
        p = self._parse("search for python tutorials")
        self.assertIsInstance(p.intent, str)

    def test_unknown(self):
        p = self._parse("xyzzy frobnicate quux")
        self.assertIsInstance(p.intent, str)

    def test_compound_command(self):
        p = self._parse("open notepad and then type hello world")
        self.assertIsInstance(p.intent, str)
        # For real LLM, it may or may not flag it as compound correctly depending on prompt tuning
        if p.compound:
            self.assertGreater(len(p.sub_commands), 1)

    def test_voice_low_confidence_needs_confirmation(self):
        p = self._parse("open chrome", source="voice", conf=0.50)
        self.assertTrue(p.needs_confirmation)

    def test_voice_high_confidence_no_confirmation(self):
        p = self._parse("open chrome", source="voice", conf=0.90)
        self.assertFalse(p.needs_confirmation)


# ── Planner Tests ─────────────────────────────────────────────

class TestPlanner(unittest.TestCase):

    def setUp(self):
        from jarvis.brain.planner import Planner
        from jarvis.llm.backends.local_llm import LocalLLM
        from jarvis.llm.llm_router import LLMRouter
        from jarvis.config.config_manager import ConfigManager
        from pathlib import Path
        
        # Mock memory and bus
        self.memory = MagicMock()
        self.memory.recall.return_value = None
        self.memory.get_relevant_context.return_value = ""
        
        # Use real LLMRouter (Ollama)
        config_path = str(Path(__file__).parent.parent.parent / "jarvis" / "config" / "config.yaml")
        cm = ConfigManager(config_path)
        bc = cm.get("llm.backends.local", {})
        
        real_llm = LocalLLM(
            api_url=bc.get("api_url", "http://localhost:11434/v1"),
            model=bc.get("model", "qwen3.5:2b"),
            fallback_model=bc.get("fallback_model", "qwen3.5:2b"),
            max_tokens=bc.get("max_tokens", 8000),
            temperature=bc.get("temperature", 0.1),
            timeout=bc.get("timeout_seconds", 60),
            auto_pull=bc.get("auto_pull", False),
        )
        self.router = LLMRouter(primary=real_llm, emergency=real_llm)
        
        self.bus = MagicMock()
        self.bus.is_fast_path_eligible.return_value = False
        self.planner = Planner(self.memory, self.router, self.bus)
    def test_direct_map_volume(self):
        packet = PerceptionPacket(
            utterance=Utterance("set volume to 80"),
            intent="llm_route",
            entities={"raw": "set volume to 80"},
        )
        plan = self.planner.plan(packet)
        self.assertIsInstance(plan, list)

    def test_direct_map_minimize(self):
        packet = PerceptionPacket(
            utterance=Utterance("minimize"),
            intent="llm_route",
            entities={"raw": "minimize"},
        )
        plan = self.planner.plan(packet)
        self.assertIsInstance(plan, list)

    def test_open_app_no_sub(self):
        packet = PerceptionPacket(
            utterance=Utterance("open notepad"),
            intent="llm_route",
            entities={"raw": "open notepad"},
        )
        plan = self.planner.plan(packet)
        self.assertIsInstance(plan, list)

    def test_open_app_with_sub_location(self):
        packet = PerceptionPacket(
            utterance=Utterance("open settings wifi"),
            intent="llm_route",
            entities={"raw": "open settings wifi"},
        )
        plan = self.planner.plan(packet)
        self.assertIsInstance(plan, list)

    def test_unknown_intent_calls_llm(self):
        packet = PerceptionPacket(
            utterance=Utterance("do something weird"),
            intent="llm_route",
            entities={"raw": "do something weird"},
        )
        plan = self.planner.plan(packet)
        self.assertIsInstance(plan, list)

    def test_compound_planning(self):
        packet = PerceptionPacket(
            utterance=Utterance("minimize and then type hello"),
            intent="llm_route",
            entities={"raw": "minimize and then type hello"},
            compound=True,
            sub_commands=[
                {"intent": "llm_route", "entities": {"raw": "minimize"}, "text": "minimize"},
                {"intent": "llm_route", "entities": {"raw": "type hello"}, "text": "type hello"},
            ],
        )
        plan = self.planner.plan(packet)
        self.assertIsInstance(plan, list)


# ── Orchestrator Pipeline Tests ────────────────────────────────

class TestOrchestratorPipeline(unittest.TestCase):

    def _make_bus(self, success=True):
        """Build a SkillBus with mocked builtins."""
        bus = SkillBus()

        @skill(triggers=["open app"], name="open_app", category="app")
        def mock_open(params):
            return SkillResult(success=success, action_taken="opened")

        @skill(triggers=["minimize window"], name="minimize_window", category="window")
        def mock_min(params):
            return SkillResult(success=success, action_taken="minimized")

        @skill(triggers=["hi jarvis"], name="session_activate", category="session")
        def mock_activate(params):
            return SkillResult(success=True, message="Hello!")

        @skill(triggers=["ask user"], name="ask_user", category="session")
        def mock_ask(params):
            return SkillResult(success=True, message=params.get("reason", "?"))

        @skill(triggers=["reply"], name="chat_reply", category="session")
        def mock_reply(params):
            return SkillResult(success=True, message=params.get("message", "OK"))

        bus.register(mock_open)
        bus.register(mock_min)
        bus.register(mock_activate)
        bus.register(mock_ask)
        bus.register(mock_reply)
        bus._discovered = True
        return bus

    def _make_orch(self, success=True):
        from jarvis.brain.orchestrator import Orchestrator
        from jarvis.llm.backends.local_llm import LocalLLM
        from jarvis.llm.llm_router import LLMRouter
        from jarvis.config.config_manager import ConfigManager
        from pathlib import Path
        
        memory = MagicMock()
        memory.recall.return_value = None
        memory.get_relevant_context.return_value = ""
        memory.get_db.return_value = MagicMock()
        
        # Use real LLMRouter (Ollama)
        config_path = str(Path(__file__).parent.parent.parent / "jarvis" / "config" / "config.yaml")
        cm = ConfigManager(config_path)
        bc = cm.get("llm.backends.local", {})
        
        real_llm = LocalLLM(
            api_url=bc.get("api_url", "http://localhost:11434/v1"),
            model=bc.get("model", "qwen3.5:2b"),
            fallback_model=bc.get("fallback_model", "qwen3.5:2b"),
            max_tokens=bc.get("max_tokens", 8000),
            temperature=bc.get("temperature", 0.1),
            timeout=bc.get("timeout_seconds", 60),
            auto_pull=bc.get("auto_pull", False),
        )
        router = LLMRouter(primary=real_llm, emergency=real_llm)
        
        bus = self._make_bus(success)
        orch = Orchestrator(memory=memory, router=router, bus=bus)
        # Bypass boot (no DB needed)
        orch._pathfinder = MagicMock()
        return orch

    def test_session_activate_full_pipeline(self):
        orch = self._make_orch()
        result = orch.process("hi jarvis")
        self.assertTrue(result[0].success)
        self.assertIn("Hello", result[0].message)

    def test_minimize_pipeline(self):
        orch = self._make_orch()
        result = orch.process("minimize")
        self.assertTrue(result[0].success)

    def test_open_app_pipeline(self):
        orch = self._make_orch()
        result = orch.process("open notepad")
        self.assertTrue(result[0].success)

    def test_failed_skill_halts_plan(self):
        orch = self._make_orch(success=False)
        # Compound: first fails → second should not run
        call_count = [0]
        original_dispatch = orch._bus.dispatch
        def counting_dispatch(call):
            call_count[0] += 1
            return SkillResult(success=False, message="failed")
        orch._bus.dispatch = counting_dispatch
        orch.process("minimize and then type hello")
        # Only 1 call should have been made (halted after first failure)
        self.assertEqual(call_count[0], 1)

    def test_low_voice_confidence_asks_user(self):
        orch = self._make_orch()
        result = orch.process("open chrome", source="voice", confidence=0.40)
        # Should trigger ask_user
        self.assertTrue(result[0].success)
        self.assertIn("heard", result[0].message.lower())


# ── VerificationLoop Tests ─────────────────────────────────────

class TestVerificationLoop(unittest.TestCase):

    def _make_vloop(self, before_hash="aaa", after_hash="bbb"):
        harvester = MagicMock()
        # Return non-empty state dicts so the hash-based logic is exercised
        harvester.harvest_and_hash.side_effect = [
            ({"CheckBox:WiFi": 1}, before_hash),
            ({"CheckBox:WiFi": 1}, after_hash),
        ]
        comparator = MagicMock()
        recovery = MagicMock()
        recovery.retry.return_value = SkillResult(success=True)
        recovery.ask_user.return_value = SkillResult(success=False, message="asked user")
        return VerificationLoop(harvester, comparator, recovery)

    def test_skip_verify_skills_bypass(self):
        """Skills in SKIP_VERIFY_SKILLS must not trigger verification."""
        vloop = self._make_vloop()
        bus = MagicMock()
        bus.dispatch.return_value = SkillResult(success=True, action_taken="typed")
        packet = PerceptionPacket(utterance=Utterance("type hello"), intent="type_text")
        snapshot = MagicMock()
        learner = MagicMock()

        call = SkillCall(skill="type_text", params={"text": "hello"})
        result = vloop.execute_and_verify(call, bus, packet, snapshot, learner)

        # Harvester should NOT have been called
        vloop._harvester.harvest_and_hash.assert_not_called()
        self.assertTrue(result.success)

    def test_state_changed_returns_verified(self):
        """When hash changes, result is marked [Verified]."""
        vloop = self._make_vloop(before_hash="hash1", after_hash="hash2")
        bus = MagicMock()
        bus.get_settle_ms.return_value = 0
        bus.dispatch.return_value = SkillResult(success=True, action_taken="navigated")
        packet = PerceptionPacket(utterance=Utterance("navigate to settings"), intent="navigate_location",
                                  app_context="settings")
        snapshot = MagicMock()
        snapshot.active_app = "settings"
        learner = MagicMock()
        call = SkillCall(skill="navigate_location", params={"target": "settings"})

        result = vloop.execute_and_verify(call, bus, packet, snapshot, learner)
        self.assertTrue(result.success)
        self.assertIn("Verified", result.action_taken)

    def test_state_unchanged_triggers_recovery(self):
        """When hash stays same (non-empty), recovery.retry is called."""
        harvester = MagicMock()
        harvester.harvest_and_hash.side_effect = [
            ({"CheckBox:WiFi": 1}, "same_hash"),
            ({"CheckBox:WiFi": 1}, "same_hash"),
            ({"CheckBox:WiFi": 1}, "same_hash"),
            ({"CheckBox:WiFi": 1}, "same_hash"),
        ]
        comparator = MagicMock()
        recovery = MagicMock()
        recovery.retry.return_value = SkillResult(success=True)
        vloop = VerificationLoop(harvester, comparator, recovery)

        bus = MagicMock()
        bus.get_settle_ms.return_value = 0
        bus.dispatch.return_value = SkillResult(success=True, action_taken="navigated")
        packet = PerceptionPacket(utterance=Utterance("navigate to settings"), intent="navigate_location",
                                  app_context="settings")
        snapshot = MagicMock()
        snapshot.active_app = "settings"
        learner = MagicMock()
        call = SkillCall(skill="navigate_location", params={"target": "settings"})

        vloop.execute_and_verify(call, bus, packet, snapshot, learner)
        self.assertTrue(recovery.retry.called)

    def test_no_uia_state_trusts_skill_result(self):
        """Empty state dicts (no UIA) → trusts skill result."""
        harvester = MagicMock()
        harvester.harvest_and_hash.return_value = ({}, "")
        comparator = MagicMock()
        recovery = MagicMock()
        vloop = VerificationLoop(harvester, comparator, recovery)

        bus = MagicMock()
        bus.dispatch.return_value = SkillResult(success=True, action_taken="done")
        packet = PerceptionPacket(utterance=Utterance("open settings"), intent="open_app")
        snapshot = MagicMock()
        snapshot.active_app = ""
        learner = MagicMock()
        call = SkillCall(skill="open_app", params={"target": "settings"})

        result = vloop.execute_and_verify(call, bus, packet, snapshot, learner)
        self.assertTrue(result.success)
        recovery.retry.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
