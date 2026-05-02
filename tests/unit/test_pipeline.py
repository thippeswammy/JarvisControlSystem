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


# ── NLU Tests ─────────────────────────────────────────────────

class TestNLU(unittest.TestCase):

    def setUp(self):
        self.nlu = NLU()

    def _parse(self, text: str, source="text", conf=1.0) -> PerceptionPacket:
        return self.nlu.parse(Utterance(text=text, source=source, confidence=conf))

    def test_session_activate(self):
        p = self._parse("hi jarvis")
        self.assertEqual(p.intent, "session_activate")

    def test_session_deactivate(self):
        p = self._parse("bye jarvis")
        self.assertEqual(p.intent, "session_deactivate")

    def test_volume_set(self):
        p = self._parse("set volume to 50")
        self.assertEqual(p.intent, "set_volume")
        self.assertEqual(p.entities.get("level"), "50")

    def test_mute(self):
        p = self._parse("mute")
        self.assertEqual(p.intent, "set_volume")
        self.assertTrue(p.entities.get("mute"))

    def test_open_app(self):
        p = self._parse("open notepad")
        self.assertEqual(p.intent, "open_app")
        self.assertEqual(p.entities.get("target"), "notepad")

    def test_open_settings_with_sub(self):
        p = self._parse("open settings wifi")
        self.assertEqual(p.intent, "open_app")
        self.assertEqual(p.entities.get("target"), "settings")
        self.assertIn("wifi", p.sub_location)

    def test_open_display_settings(self):
        p = self._parse("open display settings")
        self.assertEqual(p.intent, "open_app")
        self.assertEqual(p.entities.get("target"), "settings")
        self.assertIn("display", p.sub_location)

    def test_navigate_to(self):
        p = self._parse("navigate to bluetooth")
        self.assertEqual(p.intent, "navigate_location")
        self.assertIn("bluetooth", p.entities.get("target", ""))

    def test_minimize(self):
        p = self._parse("minimize")
        self.assertEqual(p.intent, "minimize_window")

    def test_maximize(self):
        p = self._parse("maximize")
        self.assertEqual(p.intent, "maximize_window")

    def test_press_key(self):
        p = self._parse("press ctrl+s")
        self.assertEqual(p.intent, "press_key")
        self.assertIn("ctrl", p.entities.get("key", "").lower())

    def test_type_text(self):
        p = self._parse("type hello world")
        self.assertEqual(p.intent, "type_text")
        self.assertIn("hello", p.entities.get("text", ""))

    def test_shutdown(self):
        p = self._parse("shutdown")
        self.assertEqual(p.intent, "power_action")

    def test_search_web(self):
        p = self._parse("search for python tutorials")
        self.assertEqual(p.intent, "search_web")
        self.assertIn("python", p.entities.get("query", "").lower())

    def test_unknown(self):
        p = self._parse("xyzzy frobnicate quux")
        self.assertEqual(p.intent, "unknown")

    def test_compound_command(self):
        p = self._parse("open notepad and then type hello world")
        self.assertTrue(p.compound)
        self.assertGreater(len(p.sub_commands), 1)
        intents = [s["intent"] for s in p.sub_commands]
        self.assertIn("open_app", intents)
        self.assertIn("type_text", intents)

    def test_voice_low_confidence_needs_confirmation(self):
        p = self._parse("open chrome", source="voice", conf=0.50)
        self.assertTrue(p.needs_confirmation)

    def test_voice_high_confidence_no_confirmation(self):
        p = self._parse("open chrome", source="voice", conf=0.90)
        self.assertFalse(p.needs_confirmation)


# ── Planner Tests ─────────────────────────────────────────────

class TestPlanner(unittest.TestCase):

    def setUp(self):
        from jarvis.brain.planner import Planner, _DIRECT_MAP
        self._map = _DIRECT_MAP
        # Mock memory and router
        self.memory = MagicMock()
        self.memory.recall.return_value = None
        self.memory.get_relevant_context.return_value = ""
        self.router = MagicMock()
        self.router.route.return_value = []
        self.planner = Planner(self.memory, self.router)

    def test_direct_map_volume(self):
        packet = PerceptionPacket(
            utterance=Utterance("set volume to 80"),
            intent="set_volume",
            entities={"level": "80"},
        )
        plan = self.planner.plan(packet)
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0].skill, "set_volume")
        self.assertEqual(plan[0].params["level"], "80")

    def test_direct_map_minimize(self):
        packet = PerceptionPacket(
            utterance=Utterance("minimize"),
            intent="minimize_window",
            entities={},
        )
        plan = self.planner.plan(packet)
        self.assertEqual(plan[0].skill, "minimize_window")

    def test_open_app_no_sub(self):
        packet = PerceptionPacket(
            utterance=Utterance("open notepad"),
            intent="open_app",
            entities={"target": "notepad"},
        )
        plan = self.planner.plan(packet)
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0].skill, "open_app")

    def test_open_app_with_sub_location(self):
        packet = PerceptionPacket(
            utterance=Utterance("open settings wifi"),
            intent="open_app",
            entities={"target": "settings"},
            sub_location="wifi",
        )
        # Mock the router to return navigate_location for the sub_location
        self.router.route.return_value = [
            MagicMock(skill="navigate_location", params={"target": "wifi"})
        ]
        plan = self.planner.plan(packet)
        # Should have open_app + navigate_location
        skills = [c.skill for c in plan]
        self.assertIn("open_app", skills)
        self.assertIn("navigate_location", skills)

    def test_unknown_intent_calls_llm(self):
        self.router.route.return_value = [
            MagicMock(skill="open_app", params={"target": "chrome"})
        ]
        packet = PerceptionPacket(
            utterance=Utterance("do something weird"),
            intent="unknown",
            entities={},
        )
        plan = self.planner.plan(packet)
        self.assertTrue(self.router.route.called)

    def test_compound_planning(self):
        packet = PerceptionPacket(
            utterance=Utterance("minimize and then type hello"),
            intent="minimize_window",
            entities={},
            compound=True,
            sub_commands=[
                {"intent": "minimize_window", "entities": {}, "text": "minimize"},
                {"intent": "type_text", "entities": {"text": "hello"}, "text": "type hello"},
            ],
        )
        plan = self.planner.plan(packet)
        self.assertEqual(len(plan), 2)
        self.assertEqual(plan[0].skill, "minimize_window")
        self.assertEqual(plan[1].skill, "type_text")


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

        bus.register(mock_open)
        bus.register(mock_min)
        bus.register(mock_activate)
        bus.register(mock_ask)
        bus._discovered = True
        return bus

    def _make_orch(self, success=True):
        from jarvis.brain.orchestrator import Orchestrator
        memory = MagicMock()
        memory.recall.return_value = None
        memory.get_relevant_context.return_value = ""
        memory.get_db.return_value = MagicMock()
        router = MagicMock()
        router.route.return_value = []
        bus = self._make_bus(success)
        orch = Orchestrator(memory=memory, router=router, bus=bus)
        # Bypass boot (no DB needed)
        orch._pathfinder = MagicMock()
        return orch

    def test_session_activate_full_pipeline(self):
        orch = self._make_orch()
        result = orch.process("hi jarvis")
        self.assertTrue(result.success)
        self.assertIn("Hello", result.message)

    def test_minimize_pipeline(self):
        orch = self._make_orch()
        result = orch.process("minimize")
        self.assertTrue(result.success)

    def test_open_app_pipeline(self):
        orch = self._make_orch()
        result = orch.process("open notepad")
        self.assertTrue(result.success)

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
        self.assertTrue(result.success)
        self.assertIn("heard", result.message.lower())


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
