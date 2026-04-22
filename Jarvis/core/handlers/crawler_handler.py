"""
Crawler Handler
===============
Handles requests to manually trigger the background system scanner.
"""
import logging
from Jarvis.core.intent_engine import ActionType, Intent
from Jarvis.core.action_registry import registry, ActionResult
from Jarvis.core.jarvis_memory import MemoryManager
from Jarvis.core.system_crawler import SystemCrawler

logger = logging.getLogger(__name__)

@registry.register(
    actions=[ActionType.SYSTEM_SCAN],
    priority=10,
    description="Trigger a background system scan to learn app paths."
)
def handle_system_scan(intent: Intent, context) -> ActionResult:
    logger.info("Initializing system scanner from handler...")
    mem = MemoryManager()
    crawler = SystemCrawler(memory_manager=mem)
    crawler.scan_all_async()
    return ActionResult.ok("I've started a deep system scan in the background. I will quietly learn all the paths.")
