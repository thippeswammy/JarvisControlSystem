"""
Jarvis Context Collector
========================
Automatically gathers the "present condition" snapshot:
  - What app is active and focused
  - What location / page is currently open (Explorer path, Settings page, etc.)
  - What folders / UI elements are visible on screen
  - Recent command history this session

This snapshot is passed to:
  1. LLMFallbackModule  → so the LLM knows exactly where Jarvis is right now
  2. MemoryManager      → so saved recipes carry their preconditions

The richer this context is, the better the LLM and memory recall perform.
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from pywinauto import Desktop
    _HAS_PYWINAUTO = True
except ImportError:
    _HAS_PYWINAUTO = False

try:
    import pyautogui
    _HAS_PYAUTOGUI = True
except ImportError:
    _HAS_PYAUTOGUI = False


# ─────────────────────────────────────────────
#  Context Snapshot
# ─────────────────────────────────────────────
@dataclass
class ContextSnapshot:
    """
    A rich, timestamped record of WHERE Jarvis is right now.

    Used both by the LLM (to understand context) and by MemoryManager
    (to store preconditions alongside a saved recipe so it only replays
    when the conditions match).
    """
    # ── Active app ──────────────────────────────
    active_app: str = ""                   # e.g. "settings", "explorer", "chrome"
    active_window_title: str = ""          # full window title string

    # ── Location / path ─────────────────────────
    # For Explorer: current folder path (e.g. "C:\\Users\\thipp\\Documents")
    # For Settings: page name (e.g. "display", "bluetooth")
    # For browsers: page URL or tab title
    current_location: str = ""

    # ── Visible targets ─────────────────────────
    # Folder names visible in Explorer, menu items visible in Settings, etc.
    visible_targets: list[str] = field(default_factory=list)

    # ── Recent session history ───────────────────
    # Last N commands that succeeded this session – used as "how did we get here"
    recent_commands: list[str] = field(default_factory=list)

    def as_text(self) -> str:
        """
        Returns a concise human-readable (and LLM-readable) description
        of the current state. This is injected into the LLM prompt.
        """
        parts = [
            f"Active App: {self.active_app or 'unknown'}",
            f"Window: {self.active_window_title or 'unknown'}",
            f"Current Location: {self.current_location or 'unknown'}",
        ]
        if self.visible_targets:
            parts.append(f"Visible Targets: {', '.join(self.visible_targets[:20])}")
        if self.recent_commands:
            parts.append(f"Recent Commands: {' → '.join(self.recent_commands[-5:])}")
        return "\n".join(parts)

    def as_precondition_block(self) -> str:
        """
        Returns a compact string used as the 'Preconditions' block
        stored inside a memory .md recipe.
        e.g.  app=settings | location=display | path=N/A
        """
        return (
            f"app={self.active_app or 'any'} | "
            f"location={self.current_location or 'any'} | "
            f"window={self.active_window_title or 'any'}"
        )


# ─────────────────────────────────────────────
#  Context Collector
# ─────────────────────────────────────────────
class ContextCollector:
    """
    Collects a live ContextSnapshot by inspecting the active window.

    Usage:
        collector = ContextCollector()
        snap = collector.collect(recent_commands=["hi jarvis", "open settings"])
    """

    def collect(self, recent_commands: list[str] = None) -> ContextSnapshot:
        snap = ContextSnapshot(recent_commands=recent_commands or [])

        try:
            self._collect_active_window(snap)
        except Exception as e:
            logger.debug(f"ContextCollector._collect_active_window failed: {e}")

        try:
            self._collect_visible_targets(snap)
        except Exception as e:
            logger.debug(f"ContextCollector._collect_visible_targets failed: {e}")

        logger.debug(f"ContextSnapshot: {snap.as_text()}")
        return snap

    # ── Active window ────────────────────────────
    def _collect_active_window(self, snap: ContextSnapshot):
        if not _HAS_PYWINAUTO:
            return

        import win32gui
        handle = win32gui.GetForegroundWindow()
        if not handle:
            return

        desktop = Desktop(backend="uia")
        win = desktop.window(handle=handle).wrapper_object()

        title = ""
        try:
            title = win.window_text()
        except Exception:
            pass

        snap.active_window_title = title
        snap.active_app = self._classify_app(title)
        snap.current_location = self._extract_location(snap.active_app, win, title)

    def _classify_app(self, title: str) -> str:
        """Derive a short app key from the window title."""
        t = title.lower()
        for keyword, name in [
            ("settings", "settings"),
            ("file explorer", "explorer"),
            ("this pc", "explorer"),
            ("documents", "explorer"),
            ("downloads", "explorer"),
            ("notepad", "notepad"),
            ("chrome", "chrome"),
            ("edge", "edge"),
            ("firefox", "firefox"),
            ("calculator", "calculator"),
            ("code", "code"),
            ("visual studio", "visual_studio"),
            ("linkedin", "linkedin"),
            ("spotify", "spotify"),
            ("slack", "slack"),
            ("discord", "discord"),
            ("teams", "teams"),
        ]:
            if keyword in t:
                return name
        # fallback: last word of title
        parts = title.split(" - ")
        return parts[-1].strip().lower()[:20] if parts else "unknown"

    def _extract_location(self, app: str, win, title: str) -> str:
        """
        Extract a meaningful location string depending on the app.

        - Explorer → reads the address bar path
        - Settings  → parses the Settings page from the window title
        - Others    → returns the window title as-is
        """
        if app == "settings":
            # Windows Settings window title is like "Settings - Display" or just "Settings"
            if " - " in title:
                return title.split(" - ", 1)[1].strip().lower()
            return "home"

        if app == "explorer":
            return self._read_explorer_path(win) or title

        return title

    def _read_explorer_path(self, win) -> Optional[str]:
        """Read the path currently shown in Explorer's address bar."""
        try:
            # The address bar is typically an Edit control inside the breadcrumb toolbar
            addr = win.child_window(control_type="Edit", title_re="Address.*")
            return addr.get_value()
        except Exception:
            pass
        try:
            # Alternate: look by automation id
            addr = win.child_window(auto_id="1001")
            return addr.get_value()
        except Exception:
            pass
        return None

    # ── Visible targets ──────────────────────────
    def _collect_visible_targets(self, snap: ContextSnapshot):
        """
        Gather names of things visible in the active window.
        For Explorer: file/folder names.
        For Settings: visible setting labels.
        """
        if not _HAS_PYWINAUTO:
            return

        try:
            import win32gui
            handle = win32gui.GetForegroundWindow()
            if not handle:
                return

            desktop = Desktop(backend="uia")
            win = desktop.window(handle=handle).wrapper_object()

            targets = []

            if snap.active_app == "explorer":
                # List items in the file list panel
                try:
                    for item in win.descendants(control_type="ListItem"):
                        name = item.window_text().strip()
                        if name:
                            # Check if item is selected
                            state = ""
                            try:
                                if item.is_selected():
                                    state = " (selected)"
                            except Exception:
                                pass
                            targets.append(f"{name}{state}")
                except Exception:
                    pass

                # Find search box
                try:
                    search = win.child_window(control_type="Edit", title_re="Search.*")
                    if search.exists():
                        targets.append("Search Box")
                except Exception:
                    pass

            elif snap.active_app == "settings":
                # Collect visible button/hyperlink text (settings items)
                try:
                    for ctrl_type in ["Button", "Hyperlink", "ListItem", "Text", "MenuItem"]:
                        for item in win.descendants(control_type=ctrl_type):
                            name = item.window_text().strip()
                            if name and 2 < len(name) < 60:
                                # Check if it's a sidebar item or main content
                                try:
                                    if item.is_selected():
                                        name = f"{name} [active]"
                                except Exception:
                                    pass
                                targets.append(name)
                except Exception:
                    pass

                # Search box in settings
                try:
                    search = win.child_window(control_type="Edit", auto_id="SearchBox")
                    if search.exists():
                        targets.append("Settings Search")
                except Exception:
                    pass
            
            else:
                # Generic app — just grab buttons and menu items
                try:
                    for ctrl_type in ["Button", "MenuItem", "Hyperlink"]:
                        for item in win.descendants(control_type=ctrl_type):
                            name = item.window_text().strip()
                            if name and 2 < len(name) < 40:
                                targets.append(name)
                except Exception:
                    pass

            snap.visible_targets = list(dict.fromkeys(targets))[:30]  # dedupe, cap at 30
        except Exception as e:
            logger.debug(f"_collect_visible_targets failed: {e}")
