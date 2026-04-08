"""
Unit Tests — Action Registry
=============================
Tests registration, dispatch, priority, and failure handling.
Run: pytest TEST/unit/test_action_registry.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
from Jarvis.core.intent_engine import Intent, ActionType
from Jarvis.core.action_registry import ActionRegistry, ActionResult


@pytest.fixture
def fresh_registry():
    """Always use a fresh registry for each test (not the global singleton)."""
    reg = ActionRegistry()  # new instance, not singleton
    return reg


def make_intent(action: ActionType, target: str = "test") -> Intent:
    return Intent(action=action, target=target, raw=target)


# ─────────────────────────────────────────────
#  Registration
# ─────────────────────────────────────────────
class TestRegistration:
    def test_register_single_action(self, fresh_registry):
        @fresh_registry.register(actions=[ActionType.OPEN_APP])
        def handler(intent, ctx): return ActionResult.ok("opened")

        assert len(fresh_registry._handlers) == 1

    def test_register_multiple_actions(self, fresh_registry):
        @fresh_registry.register(actions=[ActionType.OPEN_APP, ActionType.CLOSE_APP])
        def handler(intent, ctx): return ActionResult.ok("done")

        # One handler entry covers both actions
        assert len(fresh_registry._handlers) == 1
        assert ActionType.OPEN_APP in fresh_registry._handlers[0].actions
        assert ActionType.CLOSE_APP in fresh_registry._handlers[0].actions

    def test_multiple_handlers_same_action(self, fresh_registry):
        @fresh_registry.register(actions=[ActionType.OPEN_APP], priority=10)
        def h1(intent, ctx): return ActionResult.ok("h1")

        @fresh_registry.register(actions=[ActionType.OPEN_APP], priority=20)
        def h2(intent, ctx): return ActionResult.ok("h2")

        assert len(fresh_registry._handlers) == 2

    def test_priority_ordering(self, fresh_registry):
        @fresh_registry.register(actions=[ActionType.OPEN_APP], priority=20)
        def h_low(intent, ctx): return ActionResult.ok("low priority")

        @fresh_registry.register(actions=[ActionType.OPEN_APP], priority=5)
        def h_high(intent, ctx): return ActionResult.ok("high priority")

        # Handlers sorted by priority (lower = first)
        assert fresh_registry._handlers[0].priority == 5
        assert fresh_registry._handlers[1].priority == 20


# ─────────────────────────────────────────────
#  Dispatch
# ─────────────────────────────────────────────
class TestDispatch:
    def test_dispatch_success(self, fresh_registry):
        @fresh_registry.register(actions=[ActionType.OPEN_APP])
        def h(intent, ctx): return ActionResult.ok(f"opened {intent.target}")

        result = fresh_registry.dispatch(make_intent(ActionType.OPEN_APP, "chrome"), None)
        assert result.success is True
        assert "chrome" in result.message

    def test_dispatch_no_handler(self, fresh_registry):
        result = fresh_registry.dispatch(make_intent(ActionType.OPEN_APP), None)
        assert result.success is False

    def test_dispatch_unknown_action(self, fresh_registry):
        result = fresh_registry.dispatch(make_intent(ActionType.UNKNOWN), None)
        assert result.success is False

    def test_dispatch_tries_next_on_failure(self, fresh_registry):
        """If first handler fails, should try next handler."""
        @fresh_registry.register(actions=[ActionType.OPEN_APP], priority=1)
        def h_fail(intent, ctx): return ActionResult.fail("first fails")

        @fresh_registry.register(actions=[ActionType.OPEN_APP], priority=2)
        def h_success(intent, ctx): return ActionResult.ok("second succeeds")

        result = fresh_registry.dispatch(make_intent(ActionType.OPEN_APP), None)
        assert result.success is True
        assert "second succeeds" in result.message

    def test_dispatch_catches_handler_exception(self, fresh_registry):
        """Handler raising an exception should not crash — try next handler."""
        @fresh_registry.register(actions=[ActionType.OPEN_APP], priority=1)
        def h_raise(intent, ctx): raise RuntimeError("unexpected error")

        @fresh_registry.register(actions=[ActionType.OPEN_APP], priority=2)
        def h_ok(intent, ctx): return ActionResult.ok("fallback ok")

        result = fresh_registry.dispatch(make_intent(ActionType.OPEN_APP), None)
        assert result.success is True

    def test_result_action_set_on_success(self, fresh_registry):
        @fresh_registry.register(actions=[ActionType.CLOSE_APP])
        def h(intent, ctx): return ActionResult.ok("closed")

        intent = make_intent(ActionType.CLOSE_APP, "chrome")
        result = fresh_registry.dispatch(intent, None)
        assert result.action == ActionType.CLOSE_APP


# ─────────────────────────────────────────────
#  ActionResult
# ─────────────────────────────────────────────
class TestActionResult:
    def test_ok_is_truthy(self):
        assert bool(ActionResult.ok("done")) is True

    def test_fail_is_falsy(self):
        assert bool(ActionResult.fail("fail")) is False

    def test_unknown_is_falsy(self):
        assert bool(ActionResult.unknown()) is False

    def test_ok_message(self):
        r = ActionResult.ok("hello")
        assert r.message == "hello"
        assert r.success is True

    def test_fail_message(self):
        r = ActionResult.fail("oops")
        assert r.message == "oops"
        assert r.success is False

    def test_data_passed(self):
        r = ActionResult.ok("done", app_name="notepad", pid=1234)
        assert r.data["app_name"] == "notepad"
        assert r.data["pid"] == 1234
