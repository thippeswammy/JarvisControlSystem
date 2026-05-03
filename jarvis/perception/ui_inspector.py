"""
UI Inspector
============
Extracts a compact, LLM-readable snapshot of the current UI state.
Uses pywinauto's UIA backend to harvest navigation items, buttons, and page titles.
Produces a stable 'state_signature' for state-keyed memory recall.
"""

import hashlib
import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)

@dataclass
class UISnapshot:
    active_app: str = ""
    page_title: str = ""
    nav_items: List[str] = field(default_factory=list)
    visible_buttons: List[str] = field(default_factory=list)
    active_section: str = ""
    state_signature: str = ""
    is_empty: bool = False

    def to_llm_context(self) -> str:
        """Compact LLM-injectable string representation."""
        if self.is_empty:
            return "UI State: Unknown (No data harvested)"
        
        parts = [
            f"Active App: {self.active_app}",
            f"Current Page: {self.page_title}"
        ]
        if self.active_section:
            parts.append(f"Active Section: {self.active_section}")
        
        if self.nav_items:
            # Cap to avoid token bloat
            nav_str = ", ".join(self.nav_items[:12])
            parts.append(f"Navigation Menu: [{nav_str}]")
            
        if self.visible_buttons:
            btn_str = ", ".join(self.visible_buttons[:10])
            parts.append(f"Visible Buttons: [{btn_str}]")
            
        return " | ".join(parts)

class UIInspector:
    """
    Inspects the live UI and generates a stable UISnapshot.
    """

    def __init__(self):
        self._uia_available = self._check_uia()

    def inspect(self, app_title: Optional[str] = None) -> UISnapshot:
        """
        Harvest UI tree from the foreground window or specified app.
        Returns a UISnapshot.
        """
        if not self._uia_available:
            return UISnapshot(is_empty=True)

        try:
            return self._harvest_ui(app_title)
        except Exception as e:
            logger.debug(f"[UIInspector] Inspection failed: {e}")
            return UISnapshot(is_empty=True)

    def _harvest_ui(self, app_title: Optional[str]) -> UISnapshot:
        from pywinauto import Desktop
        import win32gui

        desktop = Desktop(backend="uia")
        
        if app_title:
            try:
                win = desktop.window(title_re=f"(?i).*{app_title}.*")
                if not win.exists(timeout=0.1):
                    return UISnapshot(is_empty=True)
            except Exception:
                return UISnapshot(is_empty=True)
        else:
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd)
            if not title:
                return UISnapshot(is_empty=True)
            win = desktop.window(handle=hwnd)

        snap = UISnapshot(
            active_app=self._infer_app_id(win.window_text()),
            page_title=win.window_text()
        )

        # Harvest key elements
        try:
            # depth=4 is a balance between info and speed
            descendants = win.descendants(depth=4)
            for ctrl in descendants:
                try:
                    ctrl_type = ctrl.element_info.control_type
                    name = (ctrl.element_info.name or "").strip()
                    if not name or len(name) < 2:
                        continue

                    # Filter out common noise
                    if any(noise in name.lower() for noise in ["clock", "time", "date", "notification"]):
                        continue

                    if ctrl_type in ["MenuItem", "ListItem", "Hyperlink"]:
                        if name not in snap.nav_items:
                            snap.nav_items.append(name)
                    elif ctrl_type == "Button":
                        if name not in snap.visible_buttons:
                            snap.visible_buttons.append(name)
                    elif ctrl_type == "Text":
                        # If it's a large header, maybe it's the section name
                        if not snap.active_section and len(name) > 3:
                            snap.active_section = name
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"[UIInspector] Descendant walk failed: {e}")

        # Compute stable signature
        # We sort items to ensure signature is stable even if tree order shifts slightly
        sorted_nav = sorted(snap.nav_items)
        raw_sig = f"{snap.active_app}|{snap.page_title}|{','.join(sorted_nav)}"
        snap.state_signature = hashlib.sha256(raw_sig.encode()).hexdigest()[:12]

        return snap

    def _check_uia(self) -> bool:
        try:
            import pywinauto
            import win32gui
            return True
        except ImportError:
            logger.warning("[UIInspector] pywinauto/win32gui not available.")
            return False

    @staticmethod
    def _infer_app_id(title: str) -> str:
        # Simple inference logic
        title_lower = title.lower()
        if "settings" in title_lower: return "settings"
        if "notepad" in title_lower: return "notepad"
        if "chrome" in title_lower: return "chrome"
        if "explorer" in title_lower: return "explorer"
        return title.split(" - ")[-1].lower() if " - " in title else title.split(" ")[0].lower()
