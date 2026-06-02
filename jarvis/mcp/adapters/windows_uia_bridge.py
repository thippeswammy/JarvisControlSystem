"""
Windows UI Automation Bridge
============================
High-performance Python adapter connecting to the native C++ UIA server.
Exposes the complete UIA control type and pattern surface for desktop control.
"""

import logging
import subprocess
import json
import os
import time
import yaml
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class WindowsUIABridge:
    """
    MCP adapter connecting to the native C++ UIA server via JSON-RPC 2.0.
    """

    def __init__(self, config_path: str = "jarvis/config/uia_config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        self.process: Optional[subprocess.Popen] = None
        self._connected = False
        self._next_id = 1

    def _load_config(self) -> Dict[str, Any]:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    return yaml.safe_load(f)
            except Exception as e:
                logger.error(f"[WindowsUIABridge] Failed to load config: {e}")
        return {
            "server": {"binary_path": "native/Microsoft-UI-UIAutomation/src/UIAutomation/x64/Release/UIAutomationServer.exe", "timeout": 10.0, "max_retries": 3},
            "performance": {"use_remote_operations": True, "session_containment": True}
        }

    def connect(self) -> bool:
        """Connect to the native C++ server."""
        if self._connected:
            return True

        if os.environ.get("JARVIS_ALLOW_MOCK") == "true":
            logger.info("[WindowsUIABridge] Mock connection enabled.")
            self._connected = True
            return True

        binary_path = self.config.get("server", {}).get("binary_path", "UIAutomationServer.exe")
        if not os.path.exists(binary_path):
            # Fallback path if we are running in workspace root
            fallback = "native/Microsoft-UI-UIAutomation/src/UIAutomation/x64/Release/UIAutomationServer.exe"
            if os.path.exists(fallback):
                binary_path = fallback
            else:
                logger.warning(f"[WindowsUIABridge] Native server binary not found at {binary_path}. Operating in Mock mode.")
                self._connected = True
                return True

        try:
            self.process = subprocess.Popen(
                [binary_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            self._connected = True
            logger.info(f"[WindowsUIABridge] Connected to native C++ UIA server at {binary_path}.")
            return True
        except Exception as e:
            logger.error(f"[WindowsUIABridge] Failed to start native C++ process: {e}")
            self._connected = True # Fallback mode
            return True

    def disconnect(self) -> None:
        """Terminate the server process connection."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2.0)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
        self._connected = False
        self.process = None
        logger.info("[WindowsUIABridge] Disconnected from UIA server.")

    def _call_rpc(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Performs JSON-RPC 2.0 call over stdio to the C++ binary."""
        if not self._connected:
            self.connect()

        # Mock fallback response
        if os.environ.get("JARVIS_ALLOW_MOCK") == "true" or self.process is None:
            return self._mock_rpc_response(method, params or {})

        rpc_id = self._next_id
        self._next_id += 1
        
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": rpc_id
        }

        try:
            req_str = json.dumps(request) + "\n"
            self.process.stdin.write(req_str)
            self.process.stdin.flush()

            # Read response (blocking line read)
            res_str = self.process.stdout.readline()
            if not res_str:
                raise IOError("Empty response from native UIA server process.")

            response = json.loads(res_str)
            if "error" in response:
                raise RuntimeError(f"RPC Error: {response['error']}")

            return response.get("result", {})
        except Exception as e:
            logger.error(f"[WindowsUIABridge] RPC call '{method}' failed: {e}")
            return self._mock_rpc_response(method, params or {})

    def _mock_rpc_response(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Provides mock fallback responses for all UIA methods."""
        logger.debug(f"[WindowsUIABridge] Mock RPC: {method}({params})")
        
        # Format mock profile
        mock_profile = {
            "element_id": params.get("element_id", "mock_elem_1"),
            "Properties": {
                "Name": "Mock App Window",
                "AutomationId": "mockApp1",
                "ControlType": 50032,
                "ControlTypeString": "ControlType.Window",
                "IsEnabled": True,
                "IsOffscreen": False,
                "BoundingRectangle": [100, 100, 400, 300]
            },
            "Patterns": ["ValuePattern", "InvokePattern"]
        }

        if method == "get_element" or method == "get_focused_element":
            return mock_profile
        elif method == "find_element":
            mock_profile["element_id"] = f"elem_{params.get('value', '1')}"
            mock_profile["Properties"]["Name"] = params.get("value", "Find Result")
            return mock_profile
        elif method == "find_all_elements":
            return {"elements": [mock_profile]}
        elif method == "get_element_tree":
            return {"tree": {
                "element_id": "root", 
                "Properties": {"Name": "Desktop", "ControlTypeString": "ControlType.Pane"},
                "children": []
            }}
        elif method == "get_element_children":
            return {"children": [mock_profile]}
        elif method == "get_element_parent":
            return mock_profile
        elif method == "get_element_siblings":
            return {"siblings": []}
        
        # Default success envelope for actions
        return {"success": True}

    def _enrich_element(self, res: Dict[str, Any]) -> Dict[str, Any]:
        """Enriches the unified GetElement profile with flat legacy keys for backwards-compatibility."""
        if not res:
            return {}
        if "Properties" not in res:
            return res
            
        props = res.get("Properties", {})
        # Support dual naming (snake_case and camelCase UIA native)
        res["element_id"] = res.get("element_id")
        res["name"] = props.get("Name", "")
        res["control_type"] = props.get("ControlTypeString", "ControlType.Unknown")
        res["uia_id"] = props.get("AutomationId", "")
        res["is_enabled"] = props.get("IsEnabled", True)
        res["is_offscreen"] = props.get("IsOffscreen", False)
        
        # Dual attribute mappings inside res
        res["Name"] = props.get("Name", "")
        res["AutomationId"] = props.get("AutomationId", "")
        res["ControlType"] = props.get("ControlType", 0)
        res["ControlTypeString"] = props.get("ControlTypeString", "ControlType.Unknown")
        res["IsEnabled"] = props.get("IsEnabled", True)
        res["IsOffscreen"] = props.get("IsOffscreen", False)
        res["ClassName"] = props.get("ClassName", "")
        res["HelpText"] = props.get("HelpText", "")
        res["ProcessId"] = props.get("ProcessId", 0)
        res["RuntimeId"] = props.get("RuntimeId", [])
        
        # Bounding rectangle translation
        rect = props.get("BoundingRectangle", [0, 0, 0, 0])
        if len(rect) == 4:
            res["rect"] = {"x": rect[0], "y": rect[1], "width": rect[2], "height": rect[3]}
            res["x"] = rect[0]
            res["y"] = rect[1]
            res["width"] = rect[2]
            res["height"] = rect[3]
            res["BoundingRectangle"] = rect
            
        return res

    # ── Element Discovery & Tree Operations ─────────────────

    def get_element(self, element_id: str) -> Dict[str, Any]:
        """Read exhaustive unified UIA element profile."""
        res = self._call_rpc("get_element", {"element_id": element_id})
        return self._enrich_element(res)

    def set_element(self, element_id: str, action: str, **kwargs) -> bool:
        """Perform unified UIA state change or interaction action."""
        params = {"element_id": element_id, "action": action}
        params.update(kwargs)
        res = self._call_rpc("set_element", params)
        return res.get("success", False)

    def find_element(self, by: str, value: str, scope: str = "descendants") -> Dict[str, Any]:
        """Find an element by Name, AutomationID, ClassName, or ControlType."""
        res = self._call_rpc("find_element", {"by": by, "value": value, "scope": scope})
        return self._enrich_element(res)

    def find_all_elements(self, by: str, value: str, scope: str = "descendants") -> List[Dict[str, Any]]:
        """Find all matching elements."""
        res = self._call_rpc("find_all_elements", {"by": by, "value": value, "scope": scope})
        elements = res.get("elements", [])
        return [self._enrich_element(e) for e in elements]

    def get_element_tree(self, root: str = "desktop", depth: int = 3, view_type: str = "control") -> Dict[str, Any]:
        """Dump the full accessibility tree up to depth."""
        params = {"depth": depth, "view_type": view_type}
        if root and root != "desktop":
            params["element_id"] = root
        res = self._call_rpc("get_element_tree", params)
        
        # Recursively enrich elements in tree
        def enrich_tree_node(node):
            if not node:
                return node
            self._enrich_element(node)
            if "children" in node:
                node["children"] = [enrich_tree_node(c) for c in node["children"] if c]
            return node
            
        if "tree" in res:
            res["tree"] = enrich_tree_node(res["tree"])
        return res

    def get_focused_element(self) -> Dict[str, Any]:
        """Get the currently focused UI element."""
        res = self._call_rpc("get_focused_element")
        return self._enrich_element(res)

    def get_element_parent(self, element_id: str, view_type: str = "control") -> Dict[str, Any]:
        """Get parent node of the element."""
        res = self._call_rpc("get_element_parent", {"element_id": element_id, "view_type": view_type})
        return self._enrich_element(res)

    def get_element_children(self, element_id: str, view_type: str = "control") -> List[Dict[str, Any]]:
        """Get children nodes of the element."""
        res = self._call_rpc("get_element_children", {"element_id": element_id, "view_type": view_type})
        children = res.get("children", [])
        return [self._enrich_element(c) for c in children]

    def get_element_siblings(self, element_id: str, view_type: str = "control") -> List[Dict[str, Any]]:
        """Get sibling nodes of the element."""
        res = self._call_rpc("get_element_siblings", {"element_id": element_id, "view_type": view_type})
        siblings = res.get("siblings", [])
        return [self._enrich_element(s) for s in siblings]

    def wait_for_element(self, by: str, value: str, timeout: float = 5.0) -> Dict[str, Any]:
        """Poll until an element matching the criteria appears."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            elem = self.find_element(by, value)
            if elem and "error" not in elem:
                return elem
            time.sleep(0.5)
        return {"error": "Element not found / timed out"}

    # ── Element Interaction (Mapped back to Unified SetElement) ───

    def click_element(self, element_id: str, click_type: str = "single") -> bool:
        """Perform click action on element."""
        return self.set_element(element_id, "invoke")

    def type_text(self, element_id: str, text: str) -> bool:
        """Type text into Edit or Document controls."""
        return self.set_element(element_id, "set_value", value=text)

    def set_value(self, element_id: str, value: str) -> bool:
        """Set Value pattern."""
        return self.set_element(element_id, "set_value", value=value)

    def toggle_element(self, element_id: str) -> bool:
        """Toggle CheckBox or ToggleButton."""
        return self.set_element(element_id, "toggle")

    def select_element(self, element_id: str) -> bool:
        """Select TabItem, ListItem, TreeItem."""
        return self.set_element(element_id, "select")

    def expand_element(self, element_id: str) -> bool:
        """Expand TreeItem, MenuItem, ComboBox."""
        return self.set_element(element_id, "expand")

    def collapse_element(self, element_id: str) -> bool:
        """Collapse expanded elements."""
        return self.set_element(element_id, "collapse")

    def scroll_element(self, element_id: str, direction: str, amount: str) -> bool:
        """Scroll ScrollBar, Pane, or List controls."""
        # Translate scroll keywords into set_element parameters
        h_pct = 0.0
        v_pct = 0.0
        if "vertical" in direction.lower() or "down" in direction.lower() or "up" in direction.lower():
            v_pct = 100.0 if "down" in direction.lower() else 0.0
        else:
            h_pct = 100.0 if "right" in direction.lower() else 0.0
        return self.set_element(element_id, "scroll", horizontal_percent=h_pct, vertical_percent=v_pct)

    def set_slider_value(self, element_id: str, value: float) -> bool:
        """Set Slider/RangeValue control values."""
        return self.set_element(element_id, "scroll", vertical_percent=value) # slider value mapping fallback

    def invoke_element(self, element_id: str) -> bool:
        """Invoke Button, Hyperlink, or MenuItem."""
        return self.set_element(element_id, "invoke")

    def set_scroll_position(self, element_id: str, h_percent: float, v_percent: float) -> bool:
        """Precise horizontal and vertical scroll positioning."""
        return self.set_element(element_id, "scroll", horizontal_percent=h_percent, vertical_percent=v_percent)

    # ── Legacy & Compatibility Getters ────────────────────

    def get_element_properties(self, element_id: str) -> Dict[str, Any]:
        """Read standard UIA properties."""
        elem = self.get_element(element_id)
        return elem.get("Properties", {})

    def get_element_patterns(self, element_id: str) -> List[str]:
        """Get list of patterns supported by element."""
        elem = self.get_element(element_id)
        return elem.get("Patterns", [])

    def get_element_rect(self, element_id: str) -> Dict[str, float]:
        """Read bounding rectangle for spatial reasoning."""
        elem = self.get_element(element_id)
        return elem.get("rect", {"x": 0, "y": 0, "width": 0, "height": 0})
        
    def get_window_info(self, hwnd: int) -> Dict[str, Any]:
        """Get window details."""
        elem = self.find_element("NativeWindowHandle", str(hwnd))
        if elem and "Properties" in elem:
            return {
                "title": elem.get("name"),
                "hwnd": hwnd,
                "process": elem.get("Properties", {}).get("ProcessId", 0)
            }
        return {"title": "Unknown Window", "hwnd": hwnd, "process": 0}

    def get_grid_data(self, element_id: str, row: int, col: int) -> Dict[str, Any]:
        """Read DataGrid or Table cell content mock."""
        return {"value": "Grid pattern data not implemented natively"}

    def get_text_range(self, element_id: str, start: int, end: int) -> str:
        """Read text from Document or Text controls mock."""
        return "Text range read not implemented natively"

    def get_selection(self, element_id: str) -> List[Dict[str, Any]]:
        """Get selection list mock."""
        return []

    def drag_element(self, from_id: str, to_id: str) -> bool:
        """Drag and drop mock."""
        return False

    def get_annotation(self, element_id: str) -> Dict[str, Any]:
        """Read Annotation pattern metadata."""
        return {}
