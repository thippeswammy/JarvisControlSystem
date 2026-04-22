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
            from Jarvis.core.ui_extractor import extract_window_elements
            
            # Use the shared extractor logic
            snap = extract_window_elements()
            if not snap or snap.is_empty():
                return
                
            title = snap.window_title
            if not title:
                return
                
            # Convert structured format back to a list of strings for MemoryManager
            # so the LLM can read it concisely
            structured_lines = []
            if snap.panels:
                structured_lines.append(f"Panels: {', '.join(snap.panels)}")
            if snap.buttons:
                structured_lines.append(f"Buttons: {', '.join(snap.buttons)}")
            if snap.inputs:
                structured_lines.append(f"Inputs: {', '.join(snap.inputs)}")
            if snap.links:
                structured_lines.append(f"Links: {', '.join(snap.links)}")
            if snap.list_items:
                structured_lines.append(f"List Items: {', '.join(snap.list_items)}")
            if snap.menu_items:
                structured_lines.append(f"Menu Items: {', '.join(snap.menu_items)}")
            
            if structured_lines:
                self._memory.save_ui_map(
                    app=snap.app_name, 
                    window=title, 
                    elements=structured_lines
                )
                self._last_window_title = title
            else:
                logger.debug(f"[UISpider] No meaningful categorized elements found for '{title}'")
                
        except Exception as e:
            logger.debug(f"[UISpider] Failed to scan window: {e}")
