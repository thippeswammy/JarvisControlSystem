"""
Session Handler — Activate / Deactivate Jarvis, Typing Mode
"""
from Jarvis.core.intent_engine import ActionType, Intent
from Jarvis.core.action_registry import registry, ActionResult


@registry.register(
    actions=[ActionType.ACTIVATE_JARVIS],
    priority=0,
    description="Activate Jarvis session"
)
def handle_activate(intent: Intent, context) -> ActionResult:
    if context and context.is_active:
        return ActionResult.ok("Jarvis is already active.")
    return ActionResult.ok("Jarvis activated. How can I help?")


@registry.register(
    actions=[ActionType.DEACTIVATE_JARVIS],
    priority=0,
    description="Deactivate Jarvis session"
)
def handle_deactivate(intent: Intent, context) -> ActionResult:
    return ActionResult.ok("Jarvis deactivated. Say 'Hi Jarvis' to wake me up.")


@registry.register(
    actions=[ActionType.TYPING_MODE_ON],
    priority=0,
    description="Enable continuous typing mode"
)
def handle_typing_on(intent: Intent, context) -> ActionResult:
    return ActionResult.ok("Typing mode activated. Everything you say will be typed.")


@registry.register(
    actions=[ActionType.TYPING_MODE_OFF],
    priority=0,
    description="Disable continuous typing mode"
)
def handle_typing_off(intent: Intent, context) -> ActionResult:
    return ActionResult.ok("Typing mode deactivated.")
