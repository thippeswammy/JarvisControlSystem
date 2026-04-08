"""
Jarvis Action Registry
======================
Decorator-based registry of all command handlers.

Design principles:
- Adding a new capability = add one decorated function, zero core changes
- Handlers are prioritized by registration order within same action
- Each handler receives (intent, context) and returns ActionResult
- The registry dispatches to the first matching handler that returns success

Usage:
    registry = ActionRegistry.get_instance()

    @registry.register(actions=[ActionType.OPEN_APP])
    def my_handler(intent: Intent, context: Context) -> ActionResult:
        ...

    result = registry.dispatch(intent, context)
"""

import logging
from dataclasses import dataclass, field
from typing import Callable, Optional
from Jarvis.core.intent_engine import Intent, ActionType

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  Action Result
# ─────────────────────────────────────────────
@dataclass
class ActionResult:
    success: bool
    message: str = ""                           # Human-readable feedback for TTS
    data: dict = field(default_factory=dict)    # Any returned data
    action: Optional[ActionType] = None         # Which action was taken

    @classmethod
    def ok(cls, message: str = "", **data) -> "ActionResult":
        return cls(success=True, message=message, data=data)

    @classmethod
    def fail(cls, message: str = "", **data) -> "ActionResult":
        return cls(success=False, message=message, data=data)

    @classmethod
    def unknown(cls) -> "ActionResult":
        return cls(success=False, message="Command not recognized.")

    def __bool__(self):
        return self.success


# ─────────────────────────────────────────────
#  Handler Entry
# ─────────────────────────────────────────────
@dataclass
class HandlerEntry:
    func: Callable[[Intent, object], ActionResult]
    actions: list[ActionType]
    priority: int           # Lower = runs first
    description: str


# ─────────────────────────────────────────────
#  Action Registry (Singleton)
# ─────────────────────────────────────────────
class ActionRegistry:
    _instance: Optional["ActionRegistry"] = None

    def __init__(self):
        self._handlers: list[HandlerEntry] = []
        self._registration_counter = 0   # Used as default priority (FIFO)

    @classmethod
    def get_instance(cls) -> "ActionRegistry":
        if cls._instance is None:
            cls._instance = ActionRegistry()
        return cls._instance

    # ── Registration decorator ──────────────────
    def register(
        self,
        actions: list[ActionType],
        priority: int = None,
        description: str = "",
    ):
        """
        Decorator to register a handler function.

        Args:
            actions: List of ActionTypes this handler responds to.
            priority: Lower number = higher priority (default: registration order).
            description: Human-readable description.

        Example:
            @registry.register(actions=[ActionType.OPEN_APP])
            def handle_open(intent, context):
                ...
        """
        def decorator(func: Callable[[Intent, object], ActionResult]):
            p = priority if priority is not None else self._registration_counter
            entry = HandlerEntry(
                func=func,
                actions=actions,
                priority=p,
                description=description or func.__doc__ or func.__name__,
            )
            self._handlers.append(entry)
            self._handlers.sort(key=lambda h: h.priority)
            self._registration_counter += 1
            logger.debug(f"Registered handler {func.__name__!r} for {[a.name for a in actions]}")
            return func
        return decorator

    # ── Dispatch ────────────────────────────────
    def dispatch(self, intent: Intent, context=None) -> ActionResult:
        """
        Find the first matching handler for this intent and call it.
        Falls back to UNKNOWN result if nothing handles it.
        """
        matching = [
            h for h in self._handlers
            if intent.action in h.actions
        ]

        if not matching:
            logger.warning(f"No handler for action: {intent.action.name} target={intent.target!r}")
            return ActionResult.unknown()

        for handler in matching:
            try:
                result = handler.func(intent, context)
                if result and result.success:
                    result.action = intent.action
                    logger.info(
                        f"Handler {handler.func.__name__!r} succeeded for "
                        f"{intent.action.name}({intent.target!r})"
                    )
                    return result
            except Exception as e:
                logger.error(
                    f"Handler {handler.func.__name__!r} raised error: {e}",
                    exc_info=True
                )
                continue

        # All handlers failed
        logger.warning(f"All handlers failed for: {intent}")
        return ActionResult.fail(
            message=f"Could not complete: {intent.raw}"
        )

    def list_actions(self) -> list[dict]:
        """Returns a summary of all registered handlers (for debugging)."""
        result = []
        for h in self._handlers:
            result.append({
                "handler": h.func.__name__,
                "actions": [a.name for a in h.actions],
                "priority": h.priority,
                "description": h.description,
            })
        return result


# ─────────────────────────────────────────────
#  Module-level singleton access
# ─────────────────────────────────────────────
registry = ActionRegistry.get_instance()


# ─────────────────────────────────────────────
#  Smoke test
# ─────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    from Jarvis.core.intent_engine import Intent, ActionType

    reg = ActionRegistry.get_instance()

    @reg.register(actions=[ActionType.OPEN_APP], description="Test open app handler")
    def test_open(intent: Intent, context) -> ActionResult:
        print(f"  → Opening: {intent.target}")
        return ActionResult.ok(f"Opened {intent.target}")

    @reg.register(actions=[ActionType.CLOSE_APP], description="Test close app handler")
    def test_close(intent: Intent, context) -> ActionResult:
        print(f"  → Closing: {intent.target}")
        return ActionResult.ok(f"Closed {intent.target}")

    from Jarvis.core.intent_engine import IntentEngine
    engine = IntentEngine()

    for cmd in ["open notepad", "close chrome", "set brightness 50"]:
        intent = engine.parse(cmd)
        result = reg.dispatch(intent)
        print(f"  {cmd!r} → {result}")
