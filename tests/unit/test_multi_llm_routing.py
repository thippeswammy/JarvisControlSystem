import unittest
from unittest.mock import MagicMock, patch
from jarvis.llm.llm_router import LLMRouter
from jarvis.llm.llm_interface import LLMInterface, LLMDecision, ClosedLoopDecision, Plan

class DummyLLM(LLMInterface):
    def __init__(self, name):
        self._name = name
        self.last_raw_response = ""

    @property
    def name(self):
        return self._name

    def health_check(self):
        return True

    def plan(self, prompt, memory_context=""):
        return Plan(steps=[])

    def decide(self, prompt, context=""):
        return LLMDecision(type="chat", message=f"Response from {self._name}")

    def decide_closed_loop(self, prompt, context=""):
        return ClosedLoopDecision(status="done", reasoning=f"Done by {self._name}", actions=[])

    def _call_llm_closed_loop(self, prompt: str, context: str):
        return f"Raw Response from {self._name}"


class TestMultiLLMRouting(unittest.TestCase):
    def setUp(self):
        self.primary = DummyLLM("primary")
        self.fallback = DummyLLM("fallback")
        self.emergency = DummyLLM("emergency")
        self.nlu_backend = DummyLLM("nlu_backend")
        
        self.routing = {
            "nlu": self.nlu_backend,
            "goal_understanding": self.primary,
        }
        
        self.router = LLMRouter(
            primary=self.primary,
            fallback=self.fallback,
            emergency=self.emergency,
            routing=self.routing
        )

    def test_constructor_stores_routing(self):
        self.assertEqual(self.router._routing.get("nlu"), self.nlu_backend)
        self.assertEqual(self.router._routing.get("goal_understanding"), self.primary)
        self.assertIsNone(self.router._routing.get("unknown_task"))

    def test_routing_by_task_with_custom_backend(self):
        # NLU task is mapped to nlu_backend
        dec = self.router.decide_for_task("nlu", "hello")
        self.assertEqual(dec.message, "Response from nlu_backend")

    def test_routing_fallback_to_primary_when_unconfigured(self):
        # "recovery" task is not mapped, should fallback to primary
        dec = self.router.decide_for_task("recovery", "hello")
        self.assertEqual(dec.message, "Response from primary")

    def test_routing_raw_call_for_task(self):
        raw = self.router.call_raw_for_task("nlu", "hello", "system")
        self.assertEqual(raw, "Raw Response from nlu_backend")

        raw_fallback = self.router.call_raw_for_task("recovery", "hello", "system")
        self.assertEqual(raw_fallback, "Raw Response from primary")

    def test_decide_closed_loop_for_task(self):
        dec = self.router.decide_closed_loop_for_task("nlu", "hello")
        self.assertEqual(dec.reasoning, "Done by nlu_backend")

        dec_fallback = self.router.decide_closed_loop_for_task("recovery", "hello")
        self.assertEqual(dec_fallback.reasoning, "Done by primary")

    # ── Error-path coverage ──────────────────────────────────────
    # decide_for_task / decide_closed_loop_for_task / call_raw_for_task are not
    # exercised at all by test_llm_router_failover.py (which only drives
    # route()/plan()), so their exception and total-failure behavior is
    # covered here instead of being duplicated there.

    def test_decide_for_task_exception_falls_back_to_next_backend(self):
        """If the routed backend's decide() raises, the router logs it, marks
        that backend unhealthy, and falls through to the next backend in the
        chain instead of propagating the exception."""
        with patch.object(self.primary, "decide", side_effect=RuntimeError("boom")):
            dec = self.router.decide_for_task("goal_understanding", "hello")

        self.assertEqual(dec.message, "Response from fallback")
        self.assertFalse(self.router._health.get("primary"))

    def test_decide_for_task_all_backends_fail_raises(self):
        """When every backend in the chain returns no decision, decide_for_task
        raises RuntimeError rather than returning None or an empty decision --
        this is the router's actual current contract for total failure."""
        with patch.object(self.primary, "decide", return_value=None), \
             patch.object(self.fallback, "decide", return_value=None), \
             patch.object(self.emergency, "decide", return_value=None):
            with self.assertRaises(RuntimeError):
                self.router.decide_for_task("goal_understanding", "hello")

    def test_decide_closed_loop_exception_falls_back_to_next_backend(self):
        """If the routed backend's decide_closed_loop() raises, the router
        falls back to the next backend in the chain."""
        with patch.object(self.primary, "decide_closed_loop", side_effect=RuntimeError("boom")):
            dec = self.router.decide_closed_loop_for_task("goal_understanding", "hello")

        self.assertEqual(dec.reasoning, "Done by fallback")
        self.assertFalse(self.router._health.get("primary"))

    def test_decide_closed_loop_all_backends_fail_returns_blocked(self):
        """Unlike decide_for_task, when every backend fails to produce a
        closed-loop decision, decide_closed_loop_for_task does NOT raise --
        it returns a 'blocked' ClosedLoopDecision as a safe default. This is a
        genuinely different failure contract from decide_for_task's raise."""
        with patch.object(self.primary, "decide_closed_loop", return_value=None), \
             patch.object(self.fallback, "decide_closed_loop", return_value=None), \
             patch.object(self.emergency, "decide_closed_loop", return_value=None):
            dec = self.router.decide_closed_loop_for_task("goal_understanding", "hello")

        self.assertEqual(dec.status, "blocked")
        self.assertEqual(dec.block_reason, "No available backend")

    def test_call_raw_for_task_exception_falls_back_to_next_backend(self):
        """If the routed backend's raw closed-loop call raises, call_raw_for_task
        falls back to the next backend in the chain."""
        with patch.object(self.primary, "_call_llm_closed_loop", side_effect=RuntimeError("boom")):
            raw = self.router.call_raw_for_task("goal_understanding", "hello", "system")

        self.assertEqual(raw, "Raw Response from fallback")
        self.assertFalse(self.router._health.get("primary"))

    def test_call_raw_for_task_all_backends_fail_returns_none(self):
        """A third distinct failure contract: unlike decide_for_task's
        RuntimeError and decide_closed_loop's blocked decision, call_raw_for_task
        silently returns None when every backend in the chain raises."""
        with patch.object(self.primary, "_call_llm_closed_loop", side_effect=RuntimeError("boom")), \
             patch.object(self.fallback, "_call_llm_closed_loop", side_effect=RuntimeError("boom")), \
             patch.object(self.emergency, "_call_llm_closed_loop", side_effect=RuntimeError("boom")):
            raw = self.router.call_raw_for_task("goal_understanding", "hello", "system")

        self.assertIsNone(raw)
        self.assertFalse(self.router._health.get("primary"))
        self.assertFalse(self.router._health.get("fallback"))
        self.assertFalse(self.router._health.get("emergency"))
