"""
Unit Tests — LLM Router (No Auto-Fallback)
===========================================
Verifies that the router calls only the selected backend (task routing
override, else primary) and never silently substitutes another backend,
local, or mock on failure. Uses unittest.mock to simulate backend states.

Test cases:
    1. Primary healthy → primary used
    2. Primary returns empty plan → raises naming primary, fallback untouched
    3. Primary raises → raises naming primary, fallback untouched
    4. Unhealthy primary → raises immediately without ever calling it
    5. Health monitor updates status correctly on exception
"""

import unittest
from unittest.mock import MagicMock, patch

from jarvis.llm.llm_interface import SkillCallSpec
from jarvis.llm.backends.mock_llm import MockLLM
from jarvis.llm.llm_router import LLMRouter


def _make_backend(name: str, healthy: bool, plan_result):
    """Helper: create a mock LLMInterface backend."""
    b = MagicMock()
    b.name = name
    b.health_check.return_value = healthy
    b.plan.return_value = plan_result
    return b


class TestLLMRouterFailover(unittest.TestCase):

    def setUp(self):
        """Create a router with mocked backends. Disable health monitor thread."""
        import os
        self._old_allow_mock = os.environ.get("JARVIS_ALLOW_MOCK")
        os.environ["JARVIS_ALLOW_MOCK"] = "true"

        self.primary = _make_backend(
            "local/ollama",
            healthy=True,
            plan_result=[SkillCallSpec(skill="open_app", params={"target": "notepad"})],
        )
        self.fallback = _make_backend(
            "tunneled/qwen",
            healthy=True,
            plan_result=[SkillCallSpec(skill="navigate_location", params={"target": "wifi"})],
        )
        self.emergency = MockLLM()

        # Build router with health monitor disabled (interval=0 → immediate stop)
        with patch.object(LLMRouter, "_health_monitor_loop"):
            self.router = LLMRouter(
                primary=self.primary,
                fallback=self.fallback,
                emergency=self.emergency,
                health_check_interval=9999,  # Effectively disabled in test
            )
            # Manually set health status
            self.router._health = {
                "local/ollama": True,
                "tunneled/qwen": True,
                self.emergency.name: True,
            }

    def tearDown(self):
        import os
        if self._old_allow_mock is not None:
            os.environ["JARVIS_ALLOW_MOCK"] = self._old_allow_mock
        elif "JARVIS_ALLOW_MOCK" in os.environ:
            del os.environ["JARVIS_ALLOW_MOCK"]

    def test_primary_used_when_healthy(self):
        """Primary backend is called when healthy."""
        plan = self.router.route("open notepad")
        self.primary.plan.assert_called_once()
        self.fallback.plan.assert_not_called()
        self.assertEqual(plan[0].skill, "open_app")

    def test_fallback_not_used_when_primary_returns_empty(self):
        """Primary returning None raises immediately; fallback is never touched."""
        self.primary.plan.return_value = None
        with self.assertRaises(RuntimeError) as ctx:
            self.router.route("open wifi settings")
        self.assertIn("local/ollama", str(ctx.exception))
        self.fallback.plan.assert_not_called()

    def test_mock_not_used_when_primary_fails(self):
        """Emergency mock is never silently substituted when primary fails."""
        self.primary.plan.return_value = None
        with patch.object(self.emergency, "plan") as mock_plan:
            with self.assertRaises(RuntimeError):
                self.router.route("open notepad")
            mock_plan.assert_not_called()

    def test_unhealthy_primary_raises_without_trying_others(self):
        """Unhealthy primary raises immediately; plan() is never called on it or on fallback."""
        self.router._health["local/ollama"] = False
        with self.assertRaises(RuntimeError) as ctx:
            self.router.route("open notepad")
        self.assertIn("local/ollama", str(ctx.exception))
        self.primary.plan.assert_not_called()
        self.fallback.plan.assert_not_called()

    def test_mock_always_returns_plan(self):
        """MockLLM never returns None for common commands."""
        mock = MockLLM()
        commands = [
            "open notepad",
            "set volume to 80",
            "minimize window",
            "press enter",
            "hi jarvis",
            "close jarvis",
        ]
        for cmd in commands:
            with self.subTest(cmd=cmd):
                result = mock.plan(cmd)
                self.assertIsNotNone(result, f"Mock returned None for: {cmd!r}")
                self.assertGreater(len(result), 0)

    def test_route_raises_when_primary_produces_nothing(self):
        """Router.route() raises rather than returning None/empty when the
        selected backend produces no plan."""
        self.primary.plan.return_value = None
        with self.assertRaises(RuntimeError):
            self.router.route("some completely unknown command xyz123")

    def test_health_status_updated_on_exception(self):
        """Backend that raises an exception is marked unhealthy, and the
        exception propagates (no silent fallback)."""
        self.primary.plan.side_effect = Exception("Connection refused")
        with self.assertRaises(RuntimeError) as ctx:
            self.router.route("open notepad")
        self.assertIn("local/ollama", str(ctx.exception))
        # After exception, primary should be marked unhealthy
        self.assertFalse(self.router._health.get("local/ollama", True))
        self.fallback.plan.assert_not_called()


class TestMockLLMPatterns(unittest.TestCase):
    """Test MockLLM heuristic pattern matching directly."""

    def setUp(self):
        self.mock = MockLLM()

    def test_open_app(self):
        plan = self.mock.plan("open chrome")
        self.assertEqual(plan[0].skill, "open_app")
        self.assertEqual(plan[0].params["target"], "chrome")

    def test_volume(self):
        plan = self.mock.plan("set volume to 50")
        self.assertEqual(plan[0].skill, "set_volume")
        self.assertEqual(plan[0].params["level"], 50)

    def test_minimize(self):
        plan = self.mock.plan("minimize window")
        self.assertEqual(plan[0].skill, "minimize_window")

    def test_session_activate(self):
        plan = self.mock.plan("hi jarvis")
        self.assertEqual(plan[0].skill, "session_activate")

    def test_session_deactivate(self):
        plan = self.mock.plan("bye jarvis")
        self.assertEqual(plan[0].skill, "session_deactivate")

    def test_unknown_returns_ask_user(self):
        plan = self.mock.plan("do something impossible xyz99")
        self.assertEqual(plan[0].skill, "ask_user")


if __name__ == "__main__":
    unittest.main(verbosity=2)
