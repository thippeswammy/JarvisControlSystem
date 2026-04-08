"""
Keyboard Handler — Key press, hold, release, type text
Uses KeyboardAutomationController.py as the action library.
"""
import logging
from Jarvis.core.intent_engine import ActionType, Intent
from Jarvis.core.action_registry import registry, ActionResult
from Jarvis.KeyboardAutomationController import (
    press_key, hold_key, release_key, type_text
)

logger = logging.getLogger(__name__)


@registry.register(
    actions=[ActionType.TYPE_TEXT],
    priority=10,
    description="Type the given text using keyboard automation"
)
def handle_type(intent: Intent, context) -> ActionResult:
    text = intent.target.strip()
    if not text:
        return ActionResult.fail("What would you like me to type?")
    type_text(text, addr="KeyboardHandler.type ->")
    return ActionResult.ok(f"Typed: {text}")


@registry.register(
    actions=[ActionType.TYPE_IN_FIELD],
    priority=10,
    description="Focus a UI field and type text into it"
)
def handle_type_in_field(intent: Intent, context) -> ActionResult:
    field_name = intent.target.strip()
    text_to_type = intent.params.get("text", intent.target_extra).strip()

    if not field_name or not text_to_type:
        return ActionResult.fail("Please say: 'type in <field name> <text>'")

    from Jarvis.navigator.app_navigator import AppNavigator
    nav = AppNavigator()
    success = nav.type_in_field(field_name, text_to_type)
    if success:
        return ActionResult.ok(f"Typed '{text_to_type}' in {field_name}.")
    # Fallback: just type the text directly
    type_text(text_to_type, addr="KeyboardHandler.type_field_fallback ->")
    return ActionResult.ok(f"Typed: {text_to_type}")


@registry.register(
    actions=[ActionType.PRESS_KEY],
    priority=10,
    description="Press a keyboard key or key combination"
)
def handle_press(intent: Intent, context) -> ActionResult:
    keys_str = intent.target.strip()
    if not keys_str:
        return ActionResult.fail("Which key should I press?")
    keys = keys_str.split()
    try:
        press_key(keys, addr="KeyboardHandler.press ->")
        return ActionResult.ok(f"Pressed: {' + '.join(keys)}")
    except Exception as e:
        logger.error(f"Press key failed: {e}")
        return ActionResult.fail(f"Could not press key '{keys_str}'.")


@registry.register(
    actions=[ActionType.HOLD_KEY],
    priority=10,
    description="Hold a keyboard key down"
)
def handle_hold(intent: Intent, context) -> ActionResult:
    keys_str = intent.target.strip()
    if not keys_str:
        return ActionResult.fail("Which key should I hold?")
    keys = keys_str.split()
    try:
        hold_key(keys, addr="KeyboardHandler.hold ->")
        return ActionResult.ok(f"Holding: {' + '.join(keys)}")
    except Exception as e:
        logger.error(f"Hold key failed: {e}")
        return ActionResult.fail(f"Could not hold key '{keys_str}'.")


@registry.register(
    actions=[ActionType.RELEASE_KEY],
    priority=10,
    description="Release a held keyboard key"
)
def handle_release(intent: Intent, context) -> ActionResult:
    keys_str = intent.target.strip()
    if not keys_str:
        return ActionResult.fail("Which key should I release?")
    keys = keys_str.split()
    try:
        release_key(keys, addr="KeyboardHandler.release ->")
        return ActionResult.ok(f"Released: {' + '.join(keys)}")
    except Exception as e:
        logger.error(f"Release key failed: {e}")
        return ActionResult.fail(f"Could not release key '{keys_str}'.")
