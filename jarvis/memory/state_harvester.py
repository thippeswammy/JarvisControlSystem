"""
State Harvester
===============
Extracts UIState from the live UI accessibility tree.
Returns a normalized state dict and its MD5 hash.

UIState captures VALUES, not just labels:
    - Toggle states (on/off)
    - Combobox selections
    - Checkbox states
    - Slider values (bucketed to 10% bands to avoid hash churn)
    - Visibility of key elements

This hash is used by the VerificationLoop to confirm an action
actually changed the UI state as expected.
"""

import hashlib
import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Elements whose text changes are noise (ignore these for state hashing)
_NOISE_LABELS = {
    "clock", "time", "date", "battery", "notification", "taskbar",
    "start", "cortana", "search", "system tray",
}

# Maximum slider resolution for state hashing (bucket to avoid micro-changes)
_SLIDER_BUCKET_SIZE = 10  # 0-9 = 0, 10-19 = 10, etc.


class StateHarvester:
    """
    Extracts and hashes the current UI state using pywinauto.

    Usage:
        harvester = StateHarvester()
        state_dict = harvester.harvest()
        state_hash = harvester.compute_hash(state_dict)
    """

    def __init__(self):
        self._uia_available = self._check_uia()

    def harvest(self, app_title: Optional[str] = None) -> dict:
        """
        Extract UIState from the focused window (or app_title if given).
        Returns a dict of {element_id: value}.
        Empty dict if UI automation not available.
        """
        if not self._uia_available:
            return {}

        try:
            return self._harvest_via_uia(app_title)
        except Exception as e:
            logger.debug(f"[StateHarvester] Harvest failed: {e}")
            return {}

    def compute_hash(self, state_dict: dict) -> str:
        """
        Compute a stable MD5 hash of a state dict.
        Sorts keys for determinism.
        """
        normalized = json.dumps(state_dict, sort_keys=True)
        return hashlib.md5(normalized.encode()).hexdigest()

    def harvest_and_hash(self, app_title: Optional[str] = None) -> tuple[dict, str]:
        """Convenience: returns (state_dict, state_hash)."""
        state = self.harvest(app_title)
        return state, self.compute_hash(state)

    # ── Private ──────────────────────────────────────

    def _harvest_via_uia(self, app_title: Optional[str] = None) -> dict:
        """Use pywinauto UIA backend to extract state values."""
        from pywinauto import Desktop
        import pywinauto.controls.uia_controls as uia

        state: dict[str, Any] = {}
        desktop = Desktop(backend="uia")

        try:
            if app_title:
                try:
                    win = desktop.window(title_re=f"(?i).*{app_title}.*")
                    # Force a check to see if it exists
                    if not win.exists(timeout=0.1):
                        raise Exception("Window not found")
                except Exception:
                    # Fallback: list titles to log
                    titles = [w.window_text() for w in desktop.windows()]
                    logger.debug(f"[StateHarvester] '{app_title}' not found. Visible: {titles}")
                    return {}
            else:
                # Use the foreground window
                import win32gui
                hwnd = win32gui.GetForegroundWindow()
                title = win32gui.GetWindowText(hwnd)
                if not title:
                    return {}
                win = desktop.window(handle=hwnd)

            # Include the window title in the state (very robust)
            state["_window_title"] = win.window_text()

            # Walk the control tree — depth 4 for complex apps
            try:
                desc = win.descendants(depth=4)
                # logger.debug(f"[StateHarvester] Found {len(desc)} descendants for '{app_title}'")
                
                for ctrl in desc:
                    try:
                        ctrl_type = ctrl.element_info.control_type
                        name = (ctrl.element_info.name or "").strip()

                        # Skip noise
                        if any(noise in name.lower() for noise in _NOISE_LABELS):
                            continue
                        if not name:
                            continue

                        key = f"{ctrl_type}:{name}"

                        if ctrl_type == "CheckBox":
                            state[key] = ctrl.get_toggle_state()
                        elif ctrl_type == "ToggleButton":
                            state[key] = ctrl.get_toggle_state()
                        elif ctrl_type == "ComboBox":
                            state[key] = str(ctrl.selected_text() or "")
                        elif ctrl_type == "Slider":
                            raw_val = ctrl.element_info.rich_text or "0"
                            try:
                                val = int(float(raw_val))
                                bucketed = (val // _SLIDER_BUCKET_SIZE) * _SLIDER_BUCKET_SIZE
                                state[key] = bucketed
                            except ValueError:
                                state[key] = raw_val
                        elif ctrl_type == "RadioButton":
                            state[key] = ctrl.get_toggle_state()

                    except Exception:
                        pass  # Skip any control that fails to query
            except Exception as e:
                logger.debug(f"[StateHarvester] descendants() failed for '{app_title}': {e}")
                # We still return 'state' because it at least has the window title

        except Exception as e:
            logger.debug(f"[StateHarvester] Window access failed: {e}")

        return state

    @staticmethod
    def _check_uia() -> bool:
        try:
            import pywinauto  # noqa: F401
            return True
        except ImportError:
            logger.warning("[StateHarvester] pywinauto not available. State hashing disabled.")
            return False
