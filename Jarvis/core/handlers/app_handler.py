"""
App Handler — Open and Close Applications
Uses ApplicationManager.py as the action library.
"""
import logging
from Jarvis.core.intent_engine import ActionType, Intent
from Jarvis.core.action_registry import registry, ActionResult
from Jarvis.ApplicationManager import open_application, close_application
from Jarvis.WindowsFeature.WINDOWS_SystemController import DesktopSystemController

logger = logging.getLogger(__name__)


@registry.register(
    actions=[ActionType.OPEN_APP],
    priority=10,
    description="Open an installed application"
)
def handle_open_app(intent: Intent, context) -> ActionResult:
    app_name = intent.target.strip()
    if not app_name:
        return ActionResult.fail("Which application would you like to open?")

    logger.info(f"Opening app: {app_name!r}")

    # Try direct open first
    success = open_application(app_name_query=app_name, addr="AppHandler.open ->")
    if success:
        return ActionResult.ok(f"Opening {app_name}.")

    # Fallback: Windows Search
    logger.info(f"Direct open failed for {app_name!r}, trying Windows Search")
    search_success = DesktopSystemController.open_apps_by_windows_search(
        f"open {app_name}", addr="AppHandler.search_fallback ->"
    )
    if search_success:
        return ActionResult.ok(f"Opening {app_name} via Windows Search.")

    return ActionResult.fail(f"Could not find or open '{app_name}'.")


@registry.register(
    actions=[ActionType.CLOSE_APP],
    priority=10,
    description="Close a running application"
)
def handle_close_app(intent: Intent, context) -> ActionResult:
    app_name = intent.target.strip()
    if not app_name:
        return ActionResult.fail("Which application would you like to close?")

    logger.info(f"Closing app: {app_name!r}")
    success = close_application(app_name_query=app_name, addr="AppHandler.close ->")

    if success:
        return ActionResult.ok(f"Closed {app_name}.")
    return ActionResult.fail(f"Could not close '{app_name}'. Is it running?")


@registry.register(
    actions=[ActionType.SCAN_APPS],
    priority=10,
    description="Rescan and refresh the installed applications list"
)
def handle_scan_apps(intent: Intent, context) -> ActionResult:
    from Jarvis.SystemFilePathScanner import GetAllFilePath
    try:
        logger.info("Starting app rescan...")
        GetAllFilePath(addr="AppHandler.rescan ->")
        return ActionResult.ok("Application scan complete. App list updated.")
    except Exception as e:
        logger.error(f"App scan failed: {e}", exc_info=True)
        return ActionResult.fail(f"App scan failed: {e}")
