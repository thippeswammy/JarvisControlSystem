"""
App Handler — Open and Close Applications
Uses ApplicationManager.py as the action library.
"""
import logging
import os
import subprocess
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

@registry.register(
    actions=[ActionType.EXECUTE_PROCESS],
    priority=5,
    description="Directly execute a path, script, or ms-settings URI."
)
def handle_execute_process(intent: Intent, context) -> ActionResult:
    path = intent.params.get("path") or intent.target.strip()
    if not path:
        return ActionResult.fail("No execution path provided.")
        
    logger.info(f"Direct executing: {path!r}")
    
    try:
        if path.startswith("ms-settings:"):
            # Use os.startfile for URIs
            os.startfile(path)
        else:
            # For .exe, .py, etc. just start them decoupled
            if path.endswith(".py"):
                subprocess.Popen(["python", path], shell=True)
            else:
                os.startfile(path)
        
        name = os.path.basename(path) if not path.startswith('ms-settings:') else path
        return ActionResult.ok(f"Directly executed {name}.")
    except Exception as e:
        logger.error(f"Failed to execute {path!r}: {e}")
        return ActionResult.fail(f"Execution failed: {e}")
