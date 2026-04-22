"""
Search Handler — Windows Search and general search
"""
import logging
from Jarvis.core.intent_engine import ActionType, Intent
from Jarvis.core.action_registry import registry, ActionResult

logger = logging.getLogger(__name__)


@registry.register(
    actions=[ActionType.SEARCH],
    priority=10,
    description="Search Windows or the web for a query"
)
def handle_search(intent: Intent, context) -> ActionResult:
    query = intent.target.strip()
    if not query:
        return ActionResult.fail("What would you like to search for?")

    from Jarvis.WindowsFeature.WINDOWS_SystemController import DesktopSystemController
    query_parts = query.split()
    try:
        DesktopSystemController.search_windows_for_term(query_parts, addr="SearchHandler ->")
        return ActionResult.ok(f"Searching for: {query}")
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return ActionResult.fail(f"Search failed: {e}")
