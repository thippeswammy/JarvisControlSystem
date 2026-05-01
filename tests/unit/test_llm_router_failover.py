"""
Unit Tests — LLM Router Failover
=================================
Verifies the primary → fallback → mock chain without real network calls.
Uses unittest.mock to simulate backend states.

Test cases:
    1. Primary healthy → primary used
    2. Primary fails → fallback used
    3. Both fail → mock used (emergency fallback)
    4. Mock always returns a plan (never None)
    5. Health monitor updates status correctly
"""

import unittest
from unittest.mock import MagicMock, patch

from jarvis_v2.llm.llm_interface import SkillCallSpec
from jarvis_v2.llm.backends.mock_llm import MockLLM
from jarvis_v2.llm.llm_router import LLMRouter


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

    def test_primary_used_when_healthy(self):
        """Primary backend is called when healthy."""
        plan = self.router.route("open notepad")
        self.primary.plan.assert_called_once()
        self.fallback.plan.assert_not_called()
        self.assertEqual(plan[0].skill, "open_app")

    def test_fallback_used_when_primary_fails(self):
        """Fallback is used when primary returns None (failed)."""
        self.primary.plan.return_value = None
        plan = self.router.route("open wifi settings")
        self.fallback.plan.assert_called_once()
        self.assertEqual(plan[0].skill, "navigate_location")

    def test_mock_used_when_both_fail(self):
        """Mock emergency fallback is used when primary and fallback both fail."""
        self.primary.plan.return_value = None
        self.fallback.plan.return_value = None
        plan = self.router.route("open notepad")
        self.assertIsNotNone(plan)
        self.assertGreater(len(plan), 0)
        # Mock should match "open notepad" → open_app skill
        self.assertEqual(plan[0].skill, "open_app")

    def test_unhealthy_primary_skipped(self):
        """Unhealthy primary is skipped entirely (plan not called)."""
        self.router._health["local/ollama"] = False
        plan = self.router.route("open notepad")
        self.primary.plan.assert_not_called()
        self.fallback.plan.assert_called_once()

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

    def test_route_never_returns_none(self):
        """Router.route() always returns a list (possibly empty but not None)."""
        self.primary.plan.return_value = None
        self.fallback.plan.return_value = None
        plan = self.router.route("some completely unknown command xyz123")
        self.assertIsNotNone(plan)
        self.assertIsInstance(plan, list)

    def test_health_status_updated_on_exception(self):
        """Backend that raises an exception is marked unhealthy."""
        self.primary.plan.side_effect = Exception("Connection refused")
        plan = self.router.route("open notepad")
        # After exception, primary should be marked unhealthy
        self.assertFalse(self.router._health.get("local/ollama", True))
        # Plan still returned (from fallback or mock)
        self.assertIsNotNone(plan)


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
