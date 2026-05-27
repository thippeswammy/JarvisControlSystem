"""
Conversation State Manager & Window Focus Controller
===================================================
Tracks active desktop applications and provides robust window reuse/focus methods
using dynamic window process lookup, fuzzy matching, and semantic fallback.
"""

import logging
import sys
import time
from typing import Dict, Any, Optional
from fuzzywuzzy import fuzz

logger = logging.getLogger(__name__)

class WindowStateTracker:
    """Tracks running and active windows for conversational context."""
    def __init__(self):
        self.active_apps: Dict[str, Dict[str, Any]] = {}
        self.focused_app: Optional[str] = None

    def register_app(self, app_id: str, title: str, hwnd: int, minimized: bool = False):
        app_clean = app_id.lower().strip()
        self.active_apps[app_clean] = {
            "title": title,
            "hwnd": hwnd,
            "minimized": minimized,
            "last_seen": time.time()
        }
        logger.info(f"[WindowStateTracker] Registered active app: {app_clean} (title={title!r}, hwnd={hwnd})")

    def get_app(self, app_id: str) -> Optional[Dict[str, Any]]:
        app_clean = app_id.lower().strip()
        return self.active_apps.get(app_clean)

    def remove_app(self, app_id: str):
        app_clean = app_id.lower().strip()
        if app_clean in self.active_apps:
            del self.active_apps[app_clean]
            logger.info(f"[WindowStateTracker] Deregistered app: {app_clean}")

    def update_focused(self, app_id: str):
        self.focused_app = app_id.lower().strip()


class WindowFocusController:
    """Restores and focuses existing windows dynamically using UIA and process mapping."""
    
    @staticmethod
    def focus_window(app_id: str, router: Optional[Any] = None) -> bool:
        """
        Dynamically finds an existing window for the requested app name,
        restores it if minimized, and sets foreground focus.
        No hardcoded synonym mapping is used. Uses fuzzy and semantic mapping.
        """
        target = app_id.lower().strip()
        logger.info(f"[WindowFocusController] Attempting dynamic focus for target: {target}")

        try:
            import win32gui
            import win32con
            import win32process
            import psutil
            from pywinauto import Desktop
        except ImportError:
            logger.warning("[WindowFocusController] win32gui / pywinauto not available.")
            return False

        desktop = Desktop(backend="uia")
        windows = desktop.windows()
        
        candidates = []
        for win in windows:
            title = win.window_text()
            if not title:
                continue
            
            # Resolve executable process name dynamically via hwnd
            hwnd = win.handle
            proc_name = ""
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                proc = psutil.Process(pid)
                proc_name = proc.name().replace(".exe", "").lower()
            except Exception:
                pass
            
            # Calculate fuzzy match score against title and process name
            title_score = fuzz.partial_ratio(target, title.lower())
            proc_score = fuzz.ratio(target, proc_name) if proc_name else 0
            best_score = max(title_score, proc_score)
            
            if best_score > 60:  # Candidate threshold
                candidates.append({
                    "window": win,
                    "title": title,
                    "process": proc_name,
                    "score": best_score
                })

        # Sort candidates by score descending
        candidates.sort(key=lambda x: x["score"], reverse=True)
        
        target_win = None
        if candidates:
            best_candidate = candidates[0]
            # 2. LLM Semantic Fallback / Confident Match check
            if best_candidate["score"] >= 75:
                target_win = best_candidate["window"]
                logger.info(f"[WindowFocusController] High confidence fuzzy match ({best_candidate['score']}%): {best_candidate['title']} ({best_candidate['process']})")
            elif router is not None:
                # Ask the LLM to disambiguate the candidates semantically
                logger.info("[WindowFocusController] Low confidence fuzzy match. Triggering LLM Semantic Fallback...")
                prompt = (
                    f"The user wants to focus the window: '{target}'.\n"
                    f"Choose the single best matching window index from the following running applications:\n"
                )
                for idx, c in enumerate(candidates):
                    prompt += f"[{idx}] Title: '{c['title']}', Process: '{c['process']}'\n"
                prompt += "\nRespond ONLY with the chosen index integer (e.g. 0). Do not write anything else."
                
                try:
                    decision = router.decide(prompt=prompt, context="You are the Jarvis Window Disambiguator.")
                    match = re.search(r"\d+", decision.message or "")
                    if match:
                        chosen_idx = int(match.group(0))
                        if 0 <= chosen_idx < len(candidates):
                            target_win = candidates[chosen_idx]["window"]
                            logger.info(f"[WindowFocusController] LLM selected candidate: {candidates[chosen_idx]['title']}")
                except Exception as le:
                    logger.debug(f"[WindowFocusController] LLM disambiguation failed: {le}")

            if target_win is None:
                # Default to best candidate if LLM is unavailable
                target_win = best_candidate["window"]
                logger.info(f"[WindowFocusController] Falling back to best fuzzy match candidate: {best_candidate['title']}")

        if target_win is not None:
            hwnd = target_win.handle
            try:
                # 3. Restore and focus
                if win32gui.IsIconic(hwnd):
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    time.sleep(0.2)
                
                win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                win32gui.SetForegroundWindow(hwnd)
                target_win.set_focus()
                
                logger.info(f"[WindowFocusController] Successfully focused matching window.")
                return True
            except Exception as e:
                logger.warning(f"[WindowFocusController] Focus failed: {e}")
                try:
                    target_win.set_focus()
                    return True
                except Exception:
                    pass

        return False
