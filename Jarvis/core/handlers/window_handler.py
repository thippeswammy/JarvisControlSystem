"""
Window Handler — Minimize, Maximize, Close, Switch, Snap
Uses WINDOWS_SystemController.py (WindowsAppController).
"""
import logging
from Jarvis.core.intent_engine import ActionType, Intent
from Jarvis.core.action_registry import registry, ActionResult

logger = logging.getLogger(__name__)


def _ctrl():
    from Jarvis.WindowsFeature.WINDOWS_SystemController import WindowsAppController
    return WindowsAppController


@registry.register(
    actions=[ActionType.MINIMIZE],
    priority=10,
    description="Minimize the active window"
)
def handle_minimize(intent: Intent, context) -> ActionResult:
    success = _ctrl().minimize_window()
    return ActionResult.ok("Window minimized.") if success else ActionResult.fail("Could not minimize window.")


@registry.register(
    actions=[ActionType.MAXIMIZE],
    priority=10,
    description="Maximize the active window"
)
def handle_maximize(intent: Intent, context) -> ActionResult:
    success = _ctrl().maximize_window()
    return ActionResult.ok("Window maximized.") if success else ActionResult.fail("Could not maximize window.")


@registry.register(
    actions=[ActionType.CLOSE_WINDOW],
    priority=10,
    description="Close the active window"
)
def handle_close_window(intent: Intent, context) -> ActionResult:
    success = _ctrl().close_window()
    return ActionResult.ok("Window closed.") if success else ActionResult.fail("Could not close window.")


@registry.register(
    actions=[ActionType.SWITCH_WINDOW],
    priority=10,
    description="Switch focus to the next window"
)
def handle_switch_window(intent: Intent, context) -> ActionResult:
    success = _ctrl().switch_windows()
    return ActionResult.ok("Switched window.") if success else ActionResult.fail("Could not switch window.")


@registry.register(
    actions=[ActionType.SNAP_LEFT],
    priority=10,
    description="Snap active window to the left half"
)
def handle_snap_left(intent: Intent, context) -> ActionResult:
    success = _ctrl().move_window_to_left()
    return ActionResult.ok("Window snapped left.") if success else ActionResult.fail("Could not snap left.")


@registry.register(
    actions=[ActionType.SNAP_RIGHT],
    priority=10,
    description="Snap active window to the right half"
)
def handle_snap_right(intent: Intent, context) -> ActionResult:
    success = _ctrl().move_window_to_right()
    return ActionResult.ok("Window snapped right.") if success else ActionResult.fail("Could not snap right.")
