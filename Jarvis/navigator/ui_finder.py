"""
UI Finder — Smart UI Element Finder using Windows Accessibility API
===================================================================
Uses pywinauto (uia backend) to find UI controls in any Windows app.

Scoring strategy (highest score wins):
  1.0  Exact name match (case-insensitive)
  0.95 Normalized name match (strip punctuation)
  0.7–0.9  Fuzzy name match via difflib
  0.5  Partial substring match
  Bonus +0.1 if control type matches expected type
"""

import logging
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from pywinauto import Desktop
    from pywinauto.base_wrapper import BaseWrapper
    _HAS_PYWINAUTO = True
except ImportError:
    _HAS_PYWINAUTO = False
    logger.warning("pywinauto not available — UI navigation disabled.")


# ─────────────────────────────────────────────
#  Scored Element
# ─────────────────────────────────────────────
@dataclass(order=True)
class ScoredElement:
    score: float
    name: str = field(compare=False)
    control_type: str = field(compare=False)
    element: object = field(compare=False, repr=False)   # pywinauto wrapper

    def __repr__(self):
        return f"ScoredElement(score={self.score:.2f}, name={self.name!r}, type={self.control_type})"


# Control types considered "clickable"
_CLICKABLE_TYPES = {
    "Button", "Hyperlink", "MenuItem", "ListItem", "TreeItem",
    "TabItem", "RadioButton", "CheckBox", "ComboBox",
}

# Control types that accept text input
_INPUT_TYPES = {"Edit", "Document", "ComboBox"}


# ─────────────────────────────────────────────
#  UIFinder
# ─────────────────────────────────────────────
class UIFinder:
    """
    Finds UI elements in a pywinauto window by name using fuzzy scoring.
    Works on any Windows app (Win32, WinForms, WPF, UWP, Electron).
    """

    def __init__(self, min_score: float = 0.45):
        self.min_score = min_score

    # ── Get active window ────────────────────
    def get_active_window(self) -> Optional[object]:
        """Returns the pywinauto wrapper for the currently focused window."""
        if not _HAS_PYWINAUTO:
            return None
        try:
            desktop = Desktop(backend="uia")
            win = desktop.get_active()
            return win
        except Exception as e:
            logger.debug(f"get_active_window failed: {e}")
            return None

    # ── Find element by name ─────────────────
    def find_element(
        self,
        query: str,
        window=None,
        preferred_types: list[str] = None,
    ) -> Optional[ScoredElement]:
        """
        Find the best-matching UI element for the query.

        Args:
            query: Text to search for (e.g. "save", "new file", "ok")
            window: pywinauto window wrapper (uses active window if None)
            preferred_types: Control types to favor (e.g. ["Button"])

        Returns:
            ScoredElement with highest score, or None if not found.
        """
        if not _HAS_PYWINAUTO:
            return None

        win = window or self.get_active_window()
        if not win:
            logger.warning("No active window for UI search.")
            return None

        all_elements = self._get_all_elements(win)
        if not all_elements:
            return None

        scored = self._score_elements(all_elements, query, preferred_types or [])
        scored.sort(reverse=True)

        if scored and scored[0].score >= self.min_score:
            logger.debug(f"Best match for {query!r}: {scored[0]}")
            return scored[0]

        logger.debug(f"No element found for {query!r} (best: {scored[0].score:.2f} if scored else 'none')")
        return None

    # ── Get all interactable elements ────────
    def get_all_interactable(self, window=None) -> list[ScoredElement]:
        """
        Returns all clickable / input elements in the active window.
        Useful for debugging what's available.
        """
        if not _HAS_PYWINAUTO:
            return []
        win = window or self.get_active_window()
        if not win:
            return []

        all_elements = self._get_all_elements(win)
        return [
            ScoredElement(score=1.0, name=e["name"], control_type=e["type"], element=e["element"])
            for e in all_elements
            if e["type"] in (_CLICKABLE_TYPES | _INPUT_TYPES)
        ]

    # ── Find in menu ─────────────────────────
    def find_and_navigate_menu(self, window, menu_path: list[str]) -> bool:
        """
        Navigate a menu hierarchy.
        e.g. menu_path = ["File", "Save As"]
        """
        if not _HAS_PYWINAUTO:
            return False

        current_window = window or self.get_active_window()
        if not current_window:
            return False

        for step in menu_path:
            element = self.find_element(step, window=current_window, preferred_types=["MenuItem", "Button"])
            if not element:
                logger.warning(f"Menu step not found: {step!r}")
                return False
            try:
                element.element.invoke()
                import time
                time.sleep(0.3)   # Allow menu to expand
                # After clicking, re-get active window (it may have changed)
                current_window = self.get_active_window()
            except Exception as e:
                logger.error(f"Failed to click menu step {step!r}: {e}")
                return False

        return True

    # ── Internal ─────────────────────────────
    def _get_all_elements(self, window) -> list[dict]:
        """Collect all named descendants of the window."""
        results = []
        try:
            descendants = window.descendants()
            for elem in descendants:
                try:
                    name = elem.window_text().strip()
                    ctrl_type = elem.element_info.control_type
                    if name and ctrl_type:
                        results.append({
                            "name": name,
                            "type": ctrl_type,
                            "element": elem,
                        })
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"Error collecting elements: {e}")
        return results

    def _score_elements(
        self,
        elements: list[dict],
        query: str,
        preferred_types: list[str],
    ) -> list[ScoredElement]:
        """Score each element against the query."""
        q = query.lower().strip()
        q_norm = self._normalize(q)
        scored = []

        for elem in elements:
            name = elem["name"]
            ctrl_type = elem["type"]
            name_lower = name.lower().strip()
            name_norm = self._normalize(name_lower)

            # Compute score
            score = 0.0

            if name_lower == q:
                score = 1.0
            elif name_norm == q_norm:
                score = 0.95
            elif q in name_lower or name_lower in q:
                # Partial contains match — score by overlap ratio
                overlap = len(set(q.split()) & set(name_lower.split()))
                total = max(len(q.split()), len(name_lower.split()), 1)
                score = 0.5 + 0.4 * (overlap / total)
            else:
                # Fuzzy sequence match
                ratio = SequenceMatcher(None, q_norm, name_norm).ratio()
                if ratio >= 0.4:
                    score = ratio * 0.85   # Scale down fuzzy scores

            if score < self.min_score:
                continue

            # Bonus for preferred control type
            if preferred_types and ctrl_type in preferred_types:
                score = min(1.0, score + 0.1)

            # Bonus for clickable types (most likely what user wants)
            if ctrl_type in _CLICKABLE_TYPES:
                score = min(1.0, score + 0.05)

            scored.append(ScoredElement(score=score, name=name, control_type=ctrl_type, element=elem["element"]))

        return scored

    @staticmethod
    def _normalize(text: str) -> str:
        """Remove punctuation and extra spaces for comparison."""
        return re.sub(r"[^\w\s]", "", text).strip()


# ─────────────────────────────────────────────
#  Smoke test
# ─────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    finder = UIFinder()
    win = finder.get_active_window()
    if win:
        print(f"Active window: {win.window_text()}")
        elements = finder.get_all_interactable(win)
        print(f"Found {len(elements)} interactable elements:")
        for e in elements[:20]:
            print(f"  {e.control_type:15s} | {e.name}")
    else:
        print("No active window found. Open any application first.")
