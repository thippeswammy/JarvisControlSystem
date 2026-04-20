"""
Jarvis UI Spider
================
Quietly runs in the background to learn the UI elements of the currently active app.
Extracts clickable elements via AppNavigator and saves to ui_maps.md.
"""
import logging
import threading
import time
from typing import Optional

from Jarvis.navigator.app_navigator import AppNavigator
from Jarvis.core.jarvis_memory import MemoryManager

logger = logging.getLogger(__name__)

class UISpider:
    def __init__(self, memory_manager: MemoryManager, navigator: AppNavigator):
        self._memory = memory_manager
        self._navigator = navigator
        self._spider_thread: Optional[threading.Thread] = None
        self._running = False
        self._last_window_title = ""

    def start(self):
        if self._running:
            return
        self._running = True
        self._spider_thread = threading.Thread(target=self._spider_loop, daemon=True, name="UISpider")
        self._spider_thread.start()
        logger.info("UISpider background service started.")

    def stop(self):
        self._running = False
        if self._spider_thread:
            self._spider_thread.join(timeout=2)
            self._spider_thread = None

    def scan_now(self):
        """Forces an immediate synchronous scan."""
        self._scan_active_window()

    def _spider_loop(self):
        while self._running:
            try:
                # Wait for 5 seconds between checks so it's not heavy
                time.sleep(5)
                
                info = self._navigator.get_active_window_info()
                if not info:
                    continue
                    
                current_title = info.get("title", "")
                if not current_title or current_title == self._last_window_title:
                    continue # Already scanned or empty
                
                # App changed, let's wait a moment for it to settle its UI
                time.sleep(2)
                
                self._scan_active_window(current_title)
                
            except Exception as e:
                logger.error(f"[UISpider] Error in background loop: {e}")

    def _scan_active_window(self, window_title: str = None):
        try:
            info = self._navigator.get_active_window_info()
            if not info:
                return
            
            title = window_title or info.get("title", "")
            if not title:
                return
                
            app_name = title.split("-")[-1].strip() if "-" in title else "Unknown"
            
            elements = self._navigator.list_elements()
            
            # Extract unique valid names
            valid_names = []
            seen = set()
            for el in elements:
                name = el.get("name", "")
                if isinstance(name, str):
                    name = name.strip()
                    if name and len(name) > 1 and name not in seen: # Filter empty or 1-char junk
                        valid_names.append(name)
                        seen.add(name)
            
            if valid_names:
                self._memory.save_ui_map(
                    app=app_name, 
                    window=title, 
                    elements=valid_names
                )
                self._last_window_title = title
            else:
                logger.debug(f"[UISpider] No readable elements found for '{title}'")
                
        except Exception as e:
            logger.debug(f"[UISpider] Failed to scan window: {e}")
