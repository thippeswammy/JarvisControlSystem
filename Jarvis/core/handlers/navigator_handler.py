"""
Navigator Handler — Click UI Elements, Navigate Menus, Scroll, Explore
Delegates to AppNavigator (pywinauto generic navigator).
"""
import logging
from Jarvis.core.intent_engine import ActionType, Intent
from Jarvis.core.action_registry import registry, ActionResult

logger = logging.getLogger(__name__)


def _nav():
    from Jarvis.navigator.app_navigator import AppNavigator
    return AppNavigator()


@registry.register(
    actions=[ActionType.CLICK_ELEMENT],
    priority=10,
    description="Click a UI element in the active application"
)
def handle_click(intent: Intent, context) -> ActionResult:
    target = intent.target.strip()
    if not target:
        return ActionResult.fail("What should I click?")

    nav = _nav()
    success = nav.click_element(target)
    if success:
        return ActionResult.ok(f"Clicked '{target}'.")
    return ActionResult.fail(f"Could not find '{target}' to click.")


@registry.register(
    actions=[ActionType.NAVIGATE_MENU],
    priority=10,
    description="Navigate a menu path (e.g. File → Save As)"
)
def handle_navigate_menu(intent: Intent, context) -> ActionResult:
    menu_path = intent.params.get("menu_path", [])
    if not menu_path:
        # Treat target as single menu item
        menu_path = [intent.target.strip()]

    if not menu_path or all(not p for p in menu_path):
        return ActionResult.fail("Which menu should I navigate?")

    nav = _nav()
    success = nav.navigate_menu(menu_path)
    path_str = " → ".join(menu_path)
    if success:
        return ActionResult.ok(f"Navigated: {path_str}")
    return ActionResult.fail(f"Could not navigate: {path_str}")


@registry.register(
    actions=[ActionType.NAVIGATE_LOCATION],
    priority=10,
    description="Navigate to a folder, drive, or named location in File Explorer"
)
def handle_navigate_location(intent: Intent, context) -> ActionResult:
    target = intent.target.strip()
    resolved = intent.params.get("resolved_path", target)

    from Jarvis.navigator.explorer_handler import ExplorerHandler
    explorer = ExplorerHandler()

    # Check if it's a named shortcut ("documents", "this pc", "c drive")
    success = explorer.navigate_to_named_location(target)
    if success:
        return ActionResult.ok(f"Navigated to {target}.")

    # Try as raw path
    if resolved:
        success = explorer.navigate_to_path(resolved)
        if success:
            return ActionResult.ok(f"Navigated to {resolved}.")

    return ActionResult.fail(f"Could not navigate to '{target}'.")


@registry.register(
    actions=[ActionType.SCROLL],
    priority=10,
    description="Scroll the active window up, down, left, or right"
)
def handle_scroll(intent: Intent, context) -> ActionResult:
    direction = intent.params.get("direction", "down")
    amount = intent.params.get("amount", 3)

    nav = _nav()
    success = nav.scroll(direction=direction, amount=int(amount))
    if success:
        return ActionResult.ok(f"Scrolled {direction}.")
    return ActionResult.fail(f"Could not scroll {direction}.")
