"""
Test Continuous Learning
========================
Automated script to test Jarvis's background UI spidering and reactive execution memory.
It opens 5 applications, lets the crawler learn them, and verifies memory updates.
"""

import sys
import os
import time
import logging

# Add project root to sys.path so we can import Jarvis modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from Jarvis.core.jarvis_engine import JarvisEngine
from Jarvis.core.jarvis_memory import MemoryManager

def main():
    logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")
    logger = logging.getLogger("TestRun")
    
    logger.info("Initializing Jarvis Engine with Background Trackers ON...")
    # This automatically starts the ContextManager and the UISpider background thread.
    engine = JarvisEngine(enable_window_tracking=True)
    
    # 5 standard Windows applications to test the learning flow
    test_apps = [
        "notepad",
        "calculator",
        "paint",
        "settings",
        "task manager"
    ]
    
    logger.info("Activating Jarvis...")
    engine.process("hi jarvis")
    
    logger.info(f"Starting continuous learning loop for {len(test_apps)} apps.")
    
    for app in test_apps:
        logger.info(f"\n--- Testing App: {app.upper()} ---")
        
        # 1. Ask Jarvis to open the app.
        # If it's not in memory, it will use AppHandler UI search fallback.
        # This will trigger `_learn_app_path_async` upon success.
        result = engine.process(f"open {app}")
        
        if result.success:
            logger.info(f"Successfully triggered open for {app}. Waiting for background learning...")
            # 2. Wait for 10 seconds.
            # This gives enough time for:
            # - The app to visibly launch on the desktop
            # - _learn_app_path_async to grab the executable path
            # - UISpider to wake up, see the new window, and extract text elements
            for i in range(10, 0, -1):
                print(f"  Learning... {i}s", end="\r")
                time.sleep(1)
            print("  Learning... done.")
            
            # 3. Close the app to clean up
            engine.process(f"close {app}")
            time.sleep(2)
        else:
            logger.error(f"Failed to open {app}: {result.message}")
            
    # Clean up the engine
    engine.shutdown()
    
    logger.info("\n--- Verification: Checking Memory ---")
    mem = MemoryManager()
    
    # Check apps.md
    apps_memory = mem._load_recipes_from_file(os.path.join(mem.MEMORY_DIR, "apps.md"), "apps")
    learned_apps = [r.command for r in apps_memory]
    logger.info(f"Known Apps in apps.md: {len(learned_apps)}")
    for a in learned_apps[-5:]:
        logger.info(f"  - {a}")
        
    # Check ui_maps.md
    ui_map_memory = mem._load_recipes_from_file(os.path.join(mem.MEMORY_DIR, "ui_maps.md"), "ui_maps")
    logger.info(f"Known UI Maps in ui_maps.md: {len(ui_map_memory)}")
    for r in ui_map_memory[-5:]:
        logger.info(f"  - {r.precondition_app} / {r.precondition_window}: {len(r.steps)} elements mapped.")

if __name__ == "__main__":
    main()
