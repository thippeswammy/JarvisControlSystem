"""
Jarvis Context Manager
======================
Tracks live session state so every handler knows:
  - Is Jarvis active?
  - Is typing mode on?
  - What app is currently focused?
  - What was the last command?

Auto-updates active_app and active_window_title by polling pygetwindow.
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

try:
    import pygetwindow as gw
    _HAS_PYGETWINDOW = True
except ImportError:
    _HAS_PYGETWINDOW = False

from Jarvis.core.intent_engine import Intent, ActionType

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  Context Dataclass
# ─────────────────────────────────────────────
@dataclass
class Context:
    # Session flags
    is_active: bool = False           # Has "hi jarvis" been said?
    is_typing_mode: bool = False      # "start typing" / "stop typing"

    # Active window tracking (auto-updated)
    active_window_title: str = ""
    active_app: str = ""              # Lowercase short name: "chrome", "notepad"

    # Lock state (e.g. locked to Settings navigation)
    is_locked: bool = False
    lock_target: str = ""             # What we are locked to: "settings"

    # History (last command)
    last_intent: Optional[Intent] = field(default=None, repr=False)
    last_success: bool = False

    def __repr__(self):
        return (
            f"Context(active={self.is_active}, "
            f"typing={self.is_typing_mode}, "
            f"app={self.active_app!r}, "
            f"locked={self.is_locked}/{self.lock_target!r})"
        )


# ─────────────────────────────────────────────
#  Context Manager
# ─────────────────────────────────────────────
class ContextManager:
    """
    Manages the live state of the Jarvis session.
    Automatically polls pygetwindow every second to track
    the currently focused application.
    """

    def __init__(self, poll_interval: float = 1.0):
        self._context = Context()
        self._poll_interval = poll_interval
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._poll_thread: Optional[threading.Thread] = None

    # ── Public: start / stop ────────────────────
    def start(self):
        """Start the background window-tracking thread."""
        if _HAS_PYGETWINDOW:
            self._stop_event.clear()
            self._poll_thread = threading.Thread(
                target=self._poll_active_window,
                daemon=True,
                name="jarvis-context-poller",
            )
            self._poll_thread.start()
            logger.info("Context manager window-tracking started.")
        else:
            logger.warning("pygetwindow not available — active window tracking disabled.")

    def stop(self):
        """Stop the background polling thread."""
        self._stop_event.set()

    # ── Public: read context ─────────────────────
    @property
    def context(self) -> Context:
        with self._lock:
            return self._context

    # ── Public: update after each action ────────
    def update(self, intent: Intent, success: bool) -> None:
        """Call after every action to update history."""
        with self._lock:
            self._context.last_intent = intent
            self._context.last_success = success

            # Handle state-changing intents
            action = intent.action

            if action == ActionType.ACTIVATE_JARVIS:
                self._context.is_active = True

            elif action == ActionType.DEACTIVATE_JARVIS:
                self._context.is_active = False
                self._context.is_typing_mode = False
                self._context.is_locked = False
                self._context.lock_target = ""

            elif action == ActionType.TYPING_MODE_ON:
                self._context.is_typing_mode = True

            elif action == ActionType.TYPING_MODE_OFF:
                self._context.is_typing_mode = False

            elif action == ActionType.OPEN_SETTINGS and success:
                self._context.is_locked = True
                self._context.lock_target = "settings"

            elif action == ActionType.CLOSE_SETTINGS and success:
                self._context.is_locked = False
                self._context.lock_target = ""

        logger.debug(f"Context updated: {self._context}")

    # ── Public: lock / unlock ────────────────────
    def lock_to(self, target: str) -> None:
        """Lock context to a specific app or section."""
        with self._lock:
            self._context.is_locked = True
            self._context.lock_target = target.lower()

    def unlock(self) -> None:
        """Release the lock."""
        with self._lock:
            self._context.is_locked = False
            self._context.lock_target = ""

    # ── Internal: window polling thread ─────────
    def _poll_active_window(self):
        while not self._stop_event.is_set():
            try:
                win = gw.getActiveWindow()
                if win and win.title:
                    title = win.title
                    app = self._extract_app_name(title)
                    with self._lock:
                        self._context.active_window_title = title
                        self._context.active_app = app
            except Exception:
                pass   # Non-critical — silently skip
            time.sleep(self._poll_interval)

    @staticmethod
    def _extract_app_name(title: str) -> str:
        """
        Extract a short, lowercase app name from a window title.
        e.g. "Google Chrome" → "chrome"
             "Untitled - Notepad" → "notepad"
             "Visual Studio Code" → "code"
        """
        title_lower = title.lower()
        # Known app signatures
        _SIGNATURES = {
            "chrome": "chrome",
            "firefox": "firefox",
            "edge": "edge",
            "notepad": "notepad",
            "visual studio code": "code",
            "code": "code",
            "explorer": "explorer",
            "file explorer": "explorer",
            "this pc": "explorer",
            "settings": "settings",
            "calculator": "calculator",
            "word": "word",
            "excel": "excel",
            "powerpoint": "powerpoint",
            "outlook": "outlook",
            "teams": "teams",
            "spotify": "spotify",
            "discord": "discord",
            "vlc": "vlc",
        }
        for sig, name in _SIGNATURES.items():
            if sig in title_lower:
                return name
        # Fallback: take last word after " - " separator
        parts = title.split(" - ")
        return parts[-1].strip().lower() if parts else title_lower[:20]


# ─────────────────────────────────────────────
#  Smoke test
# ─────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    from Jarvis.core.intent_engine import IntentEngine, ActionType

    mgr = ContextManager(poll_interval=0.5)
    mgr.start()

    engine = IntentEngine()

    cmds = ["hi jarvis", "open notepad", "start typing", "stop typing", "close jarvis"]
    for cmd in cmds:
        intent = engine.parse(cmd)
        mgr.update(intent, success=True)
        print(f"  [{cmd}] → {mgr.context}")

    time.sleep(2)
    print(f"\nFinal context: {mgr.context}")
    mgr.stop()
