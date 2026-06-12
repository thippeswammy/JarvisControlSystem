"""
pywinauto Backend
=================
Implements the UIBackend using the pywinauto library's UIA backend.
"""

import os
import re
import time
import hashlib
import logging
from typing import Any, Optional, Dict, List

from pywinauto import Application, Desktop
from pywinauto.controls.hwndwrapper import HwndWrapper
from pywinauto.findwindows import ElementNotFoundError

from jarvis.mcp.servers.ui_windows.backends.base_backend import UIBackend

logger = logging.getLogger(__name__)

# Standard mapping for control type abbreviations
CONTROL_TYPE_ABBREVIATIONS = {
    "Button": "btn",
    "Edit": "edt",
    "Document": "doc",
    "CheckBox": "chk",
    "RadioButton": "rad",
    "ComboBox": "cmb",
    "ListItem": "item",
    "TreeItem": "item",
    "TabItem": "item",
    "MenuItem": "menu",
    "Slider": "sld",
    "ScrollBar": "scbar",
    "Text": "txt",
    "Static": "txt",
    "Pane": "pan",
    "Group": "grp",
    "Hyperlink": "lnk",
    "Window": "win",
}


class PywinautoBackend(UIBackend):
    """
    UI Backend implementation using pywinauto UIA.
    """

    def __init__(self) -> None:
        self._element_cache: Dict[str, Any] = {}  # element_id -> pywinauto wrapper
        self._desktop = Desktop(backend="uia")

    def list_windows(self) -> List[Dict[str, Any]]:
        """List open top-level windows."""
        windows = []
        for win in self._desktop.windows():
            try:
                # Filter out windows with no title to keep it clean
                title = win.window_text()
                if not title:
                    continue
                windows.append({
                    "title": title,
                    "pid": win.process_id(),
                    "class_name": win.class_name(),
                    "handle": win.handle
                })
            except Exception as e:
                logger.debug(f"Error reading window properties: {e}")
        return windows

    def launch_app(self, app_path: str) -> Dict[str, Any]:
        """Launch an app and handle cleanup for known apps like Calculator."""
        filename = os.path.basename(app_path).lower()
        if filename in ["calc.exe", "calculator.exe", "calculatorapp.exe"]:
            logger.info("Cleaning up existing Calculator instances before launching...")
            os.system("taskkill /f /im CalculatorApp.exe >nul 2>&1")
            os.system("taskkill /f /im Calculator.exe >nul 2>&1")
            time.sleep(0.5)

        try:
            logger.info(f"Launching app: {app_path}")
            app = Application(backend="uia").start(app_path)
            time.sleep(2.0)  # Wait for it to render
            
            # Find the PID
            pid = app.process
            return {"success": True, "pid": pid, "error": None}
        except Exception as e:
            logger.error(f"Failed to launch app {app_path}: {e}")
            return {"success": False, "pid": None, "error": str(e)}

    def get_dom(self, app_title: Optional[str] = None, depth: Optional[int] = None) -> Dict[str, Any]:
        """Traverse UIA tree and build hierarchical dict. Rebuilds cache."""
        self._element_cache.clear()
        generated_ids: Dict[str, int] = {}  # tracks ID counts to resolve duplicates

        if app_title:
            # Find specific window
            logger.info(f"Searching for target window: {app_title}")
            target_win = None
            for w in self._desktop.windows():
                try:
                    w_text = w.window_text()
                    if app_title.lower() in w_text.lower():
                        target_win = w
                        break
                except Exception:
                    pass
            if not target_win:
                raise ValueError(f"Window matching '{app_title}' not found")
            root_elem = target_win
        else:
            # Target desktop root
            root_elem = self._desktop

        # Start traversal
        return self._traverse(root_elem, None, 0, depth, generated_ids)

    def click(self, element_id: str) -> bool:
        """Click an element by its cached ID."""
        wrapper = self._element_cache.get(element_id)
        if not wrapper:
            logger.error(f"Element ID '{element_id}' not found in cache")
            return False

        try:
            # Ensure it is focused and visible
            if hasattr(wrapper, "set_focus"):
                wrapper.set_focus()
            
            # Try UIA invoke pattern first
            try:
                wrapper.click()
                logger.info(f"Clicked element '{element_id}' using click()")
                return True
            except Exception:
                # Fallback to physical mouse click
                wrapper.click_input()
                logger.info(f"Clicked element '{element_id}' using click_input()")
                return True
        except Exception as e:
            logger.error(f"Click failed on element '{element_id}': {e}")
            return False

    def type_text(self, element_id: str, text: str) -> bool:
        """Type text into an element."""
        wrapper = self._element_cache.get(element_id)
        if not wrapper:
            logger.error(f"Element ID '{element_id}' not found in cache")
            return False

        try:
            if hasattr(wrapper, "set_focus"):
                wrapper.set_focus()

            # Attempt to clear existing content
            try:
                if hasattr(wrapper, "set_text"):
                    wrapper.set_text("")
                else:
                    wrapper.type_keys("^a{BACKSPACE}")
            except Exception:
                pass

            # Type the new text
            wrapper.type_keys(text, with_spaces=True)
            logger.info(f"Typed text '{text}' into element '{element_id}'")
            return True
        except Exception as e:
            logger.error(f"Type text failed on element '{element_id}': {e}")
            return False

    def set_value(self, element_id: str, value: Any) -> bool:
        """Set value of an element."""
        wrapper = self._element_cache.get(element_id)
        if not wrapper:
            logger.error(f"Element ID '{element_id}' not found in cache")
            return False

        try:
            if hasattr(wrapper, "set_focus"):
                wrapper.set_focus()

            # If it's a combobox
            if hasattr(wrapper, "select"):
                wrapper.select(value)
                logger.info(f"Selected value '{value}' on ComboBox '{element_id}'")
                return True

            # If it's a checkbox / radio button
            if hasattr(wrapper, "check") and hasattr(wrapper, "uncheck"):
                if value in [True, "true", "True", 1, "1", "Checked", "checked"]:
                    wrapper.check()
                else:
                    wrapper.uncheck()
                logger.info(f"Set check/uncheck status to '{value}' on CheckBox '{element_id}'")
                return True

            # Fallback to type text
            if hasattr(wrapper, "set_text"):
                wrapper.set_text(str(value))
                logger.info(f"Set text value '{value}' on element '{element_id}'")
                return True

            logger.warning(f"No specific value set method found for control type '{wrapper.control_type()}'. Trying click.")
            wrapper.click()
            return True
        except Exception as e:
            logger.error(f"Set value failed on element '{element_id}': {e}")
            return False

    def invoke(self, element_id: str) -> bool:
        """Invoke/activate an element."""
        wrapper = self._element_cache.get(element_id)
        if not wrapper:
            logger.error(f"Element ID '{element_id}' not found in cache")
            return False

        try:
            if hasattr(wrapper, "set_focus"):
                wrapper.set_focus()

            # Check if invoke is directly supported
            if hasattr(wrapper, "invoke"):
                wrapper.invoke()
                logger.info(f"Invoked element '{element_id}' using invoke()")
                return True
            
            # Fallback to click
            wrapper.click()
            logger.info(f"Invoked element '{element_id}' using click() fallback")
            return True
        except Exception as e:
            logger.error(f"Invoke failed on element '{element_id}': {e}")
            return False

    def read_value(self, element_id: str) -> Dict[str, Any]:
        """Read value of an element."""
        wrapper = self._element_cache.get(element_id)
        if not wrapper:
            logger.error(f"Element ID '{element_id}' not found in cache")
            return {"text": "", "value": None, "state": None}

        try:
            text = wrapper.window_text() or ""
            value = None
            state = None

            # Get value if it has get_value
            if hasattr(wrapper, "get_value"):
                try:
                    value = wrapper.get_value()
                except Exception:
                    pass

            # Check checked state
            if hasattr(wrapper, "is_checked"):
                try:
                    state = "checked" if wrapper.is_checked() else "unchecked"
                except Exception:
                    pass

            # Fallback for value from text
            if value is None and text:
                value = text

            return {
                "text": text,
                "value": value,
                "state": state
            }
        except Exception as e:
            logger.error(f"Read value failed on element '{element_id}': {e}")
            return {"text": "", "value": None, "state": None}

    # ── Traversal Helpers ─────────────────────────────

    def _traverse(
        self,
        element: Any,
        parent_name: Optional[str],
        current_depth: int,
        max_depth: Optional[int],
        generated_ids: Dict[str, int]
    ) -> Dict[str, Any]:
        """Recursively traverse the UIA tree and build a node dict."""
        try:
            info = element.element_info
            name = info.name or ""
            control_type = info.control_type or "Unknown"
            auto_id = info.automation_id or ""
            enabled = bool(info.enabled)
            visible = bool(info.visible)
            
            rect = None
            r = info.rectangle
            if r:
                rect = {"x": r.left, "y": r.top, "w": r.width(), "h": r.height()}
        except Exception as e:
            logger.debug(f"Error accessing element info: {e}")
            return {}

        # Resolve element ID
        element_id = self._build_element_id(control_type, name, auto_id, parent_name, generated_ids)
        self._element_cache[element_id] = element

        node = {
            "element_id": element_id,
            "name": name,
            "control_type": control_type,
            "auto_id": auto_id,
            "enabled": enabled,
            "visible": visible,
            "rect": rect,
            "children": []
        }

        # Check depth limit
        if max_depth is not None and current_depth >= max_depth:
            return node

        # Traverse children
        try:
            children = element.children()
        except Exception:
            children = []

        for child in children:
            child_node = self._traverse(child, name or parent_name, current_depth + 1, max_depth, generated_ids)
            if child_node:
                node["children"].append(child_node)

        return node

    def _build_element_id(
        self,
        control_type: str,
        name: str,
        auto_id: str,
        parent_name: Optional[str],
        generated_ids: Dict[str, int]
    ) -> str:
        """Create a stable, unique, and readable element ID using parent and name hashes."""
        abbrev = CONTROL_TYPE_ABBREVIATIONS.get(control_type, control_type[:3].lower())
        
        # Determine unique token base for the name
        # Prioritize auto_id to ensure the element ID is stable even if name/text updates dynamically.
        name_token = auto_id or name
        if not name_token:
            name_token = "unnamed"

        cleaned_name = self._clean_string(name_token)
        if not cleaned_name:
            cleaned_name = self._get_hash(name_token)[:8]

        cleaned_parent = "root"
        if parent_name:
            cleaned_parent = self._clean_string(parent_name) or self._get_hash(parent_name)[:8]

        base_id = f"{abbrev}_{cleaned_name}_{cleaned_parent}"
        
        # Disambiguate duplicate IDs
        count = generated_ids.get(base_id, 0)
        if count == 0:
            generated_ids[base_id] = 1
            return base_id
        else:
            generated_ids[base_id] = count + 1
            return f"{base_id}_{count}"

    @staticmethod
    def _clean_string(s: str) -> str:
        """Clean string to keep alphanumeric characters only and limit length."""
        s = re.sub(r'[^a-zA-Z0-9]', '', s)
        return s[:12]

    @staticmethod
    def _get_hash(s: str) -> str:
        """Compute deterministic MD5 hash for a string."""
        return hashlib.md5(s.encode('utf-8')).hexdigest()
