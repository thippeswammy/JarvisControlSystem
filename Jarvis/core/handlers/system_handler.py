"""
System Handler — Volume, Brightness
Uses WINDOWS_SystemController.py as the action library.
"""
import logging
from Jarvis.core.intent_engine import ActionType, Intent
from Jarvis.core.action_registry import registry, ActionResult

logger = logging.getLogger(__name__)

_SYSTEM_TARGETS = {"volume", "brightness", "sound", "audio", "screen", "display", "light"}


def _get_controller():
    from Jarvis.WindowsFeature.WINDOWS_SystemController import DesktopSystemController
    return DesktopSystemController


@registry.register(
    actions=[ActionType.SET_VALUE],
    priority=10,
    description="Set volume or brightness to a specific value"
)
def handle_set_value(intent: Intent, context) -> ActionResult:
    target = intent.target.lower()
    value = intent.params.get("value")

    if value is None:
        return ActionResult.fail(f"Please specify a value. E.g. 'set volume to 80'")

    ctrl = _get_controller()

    if any(t in target for t in ("volume", "sound", "audio")):
        success = ctrl.set_volume(int(value))
        return ActionResult.ok(f"Volume set to {value}%.") if success else ActionResult.fail("Failed to set volume.")

    if any(t in target for t in ("brightness", "screen", "display", "light")):
        success = ctrl.set_brightness(int(value))
        return ActionResult.ok(f"Brightness set to {value}%.") if success else ActionResult.fail("Failed to set brightness.")

    return ActionResult.fail(f"Don't know how to set '{target}'. Try 'volume' or 'brightness'.")


@registry.register(
    actions=[ActionType.INCREASE],
    priority=10,
    description="Increase volume or brightness"
)
def handle_increase(intent: Intent, context) -> ActionResult:
    target = intent.target.lower()
    amount = intent.params.get("amount", 10)
    ctrl = _get_controller()

    if any(t in target for t in ("volume", "sound", "audio")):
        current = ctrl.get_volume()
        new_val = min(100, current + int(amount))
        success = ctrl.set_volume(new_val)
        return ActionResult.ok(f"Volume increased to {new_val}%.") if success else ActionResult.fail("Failed.")

    if any(t in target for t in ("brightness", "screen", "display", "light")):
        current = ctrl.get_brightness()
        new_val = min(100, current + int(amount))
        success = ctrl.set_brightness(new_val)
        return ActionResult.ok(f"Brightness increased to {new_val}%.") if success else ActionResult.fail("Failed.")

    return ActionResult.fail(f"Don't know how to increase '{target}'.")


@registry.register(
    actions=[ActionType.DECREASE],
    priority=10,
    description="Decrease volume or brightness"
)
def handle_decrease(intent: Intent, context) -> ActionResult:
    target = intent.target.lower()
    amount = intent.params.get("amount", 10)
    ctrl = _get_controller()

    if any(t in target for t in ("volume", "sound", "audio")):
        current = ctrl.get_volume()
        new_val = max(0, current - int(amount))
        success = ctrl.set_volume(new_val)
        return ActionResult.ok(f"Volume decreased to {new_val}%.") if success else ActionResult.fail("Failed.")

    if any(t in target for t in ("brightness", "screen", "display", "light")):
        current = ctrl.get_brightness()
        new_val = max(0, current - int(amount))
        success = ctrl.set_brightness(new_val)
        return ActionResult.ok(f"Brightness decreased to {new_val}%.") if success else ActionResult.fail("Failed.")

    return ActionResult.fail(f"Don't know how to decrease '{target}'.")
