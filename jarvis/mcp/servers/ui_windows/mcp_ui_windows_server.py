"""
UI Windows MCP Server
=====================
JSON-RPC 2.0 stdio server process for the ui_windows MCP server.
Dispatches requests to the pywinauto or C++ backends.
"""

import sys
import json
import time
import logging
import traceback
from typing import Dict, Any, List, Optional
from pathlib import Path

# Add project root to sys.path dynamically
for parent in Path(__file__).resolve().parents:
    if (parent / "jarvis").exists():
        sys.path.insert(0, str(parent))
        break

# Redirect all logger messages to stderr before doing anything else
# to prevent polluting stdout (which is strictly for JSON-RPC messages).
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger("ui_windows_server")

from jarvis.mcp.servers.ui_windows.backends.pywinauto_backend import PywinautoBackend
from jarvis.mcp.servers.ui_windows.backends.cpp_uia_backend import CppUIABackend
from jarvis.mcp.servers.ui_windows.dom_builder import enrich_dom, compute_dom_delta
from jarvis.mcp.servers.ui_windows.dom_serializer import serialize_dom

# Auto-select the best available backend
if CppUIABackend.is_available():
    logger.info("Using C++ UIA Remote Operations backend (Phase 2)")
    backend = CppUIABackend()
else:
    logger.info("Using pywinauto UIA backend")
    backend = PywinautoBackend()


class UIWindowsMCPServer:
    """
    Manages JSON-RPC requests and dispatches to the selected backend.
    """

    def __init__(self) -> None:
        self.current_app_title: Optional[str] = None
        self.last_dom_tree: Optional[Dict[str, Any]] = None

    def list_tools(self) -> Dict[str, Any]:
        """Return the tools list."""
        return {
            "tools": [
                {
                    "name": "get_dom",
                    "description": "Capture the full UI DOM tree of an app or desktop and serialize it to text.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "app_title": {"type": "string", "description": "Title or substring of window to target. If None, targets the desktop."},
                            "mode": {"type": "string", "description": "Serialization mode: FULL, INTERACTIVE_ONLY, or TARGETED.", "enum": ["FULL", "INTERACTIVE_ONLY", "TARGETED"]},
                            "depth": {"type": "integer", "description": "Max depth to traverse"},
                            "target_id": {"type": "string", "description": "Element ID to target in TARGETED mode"}
                        },
                        "required": ["mode"]
                    }
                },
                {
                    "name": "list_windows",
                    "description": "List all open top-level windows.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
                    }
                },
                {
                    "name": "launch_app",
                    "description": "Launch an application.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "app_path": {"type": "string", "description": "Path to executable (e.g. 'calc.exe') or command."}
                        },
                        "required": ["app_path"]
                    }
                },
                {
                    "name": "find_elements",
                    "description": "Search for elements in the tree by property.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "by": {"type": "string", "enum": ["name", "auto_id", "control_type"]},
                            "value": {"type": "string"},
                            "app_title": {"type": "string"}
                        },
                        "required": ["by", "value"]
                    }
                },
                {
                    "name": "click",
                    "description": "Click an element by its ID.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "element_id": {"type": "string"},
                            "app_title": {"type": "string"}
                        },
                        "required": ["element_id"]
                    }
                },
                {
                    "name": "type_text",
                    "description": "Type text into an element by its ID.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "element_id": {"type": "string"},
                            "text": {"type": "string"},
                            "app_title": {"type": "string"}
                        },
                        "required": ["element_id", "text"]
                    }
                },
                {
                    "name": "set_value",
                    "description": "Set the value of an element.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "element_id": {"type": "string"},
                            "value": {"type": "string"},
                            "app_title": {"type": "string"}
                        },
                        "required": ["element_id", "value"]
                    }
                },
                {
                    "name": "invoke",
                    "description": "Invoke/execute an element.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "element_id": {"type": "string"},
                            "app_title": {"type": "string"}
                        },
                        "required": ["element_id"]
                    }
                },
                {
                    "name": "read_value",
                    "description": "Read text, value, or state of an element.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "element_id": {"type": "string"}
                        },
                        "required": ["element_id"]
                    }
                }
            ]
        }

    def dispatch(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route tool calls to respective backend methods and handle delta capture."""
        logger.info(f"Dispatching tool '{tool_name}' with args {arguments}")

        # Update app title context if provided
        if "app_title" in arguments and arguments["app_title"]:
            self.current_app_title = arguments["app_title"]

        if tool_name == "list_windows":
            wins = backend.list_windows()
            return {
                "content": [{"type": "text", "text": f"Found {len(wins)} windows"}],
                "windows": wins
            }

        elif tool_name == "launch_app":
            res = backend.launch_app(arguments["app_path"])
            return {
                "content": [{"type": "text", "text": f"Launch app status: {res.get('success')}"}],
                "success": res.get("success", False),
                "pid": res.get("pid"),
                "error": res.get("error")
            }

        elif tool_name == "get_dom":
            app_title = arguments.get("app_title") or self.current_app_title
            depth = arguments.get("depth")
            mode = arguments.get("mode", "FULL")
            target_id = arguments.get("target_id")

            raw_dom = backend.get_dom(app_title, depth)
            enriched = enrich_dom(raw_dom)
            self.last_dom_tree = enriched

            dom_text = serialize_dom(enriched, mode, target_id)
            return {
                "content": [{"type": "text", "text": dom_text}],
                "dom_tree": enriched,
                "dom_text": dom_text
            }

        elif tool_name == "find_elements":
            by = arguments["by"]
            value = arguments["value"]
            app_title = arguments.get("app_title") or self.current_app_title

            # Ensure we have a fresh DOM tree
            raw_dom = backend.get_dom(app_title)
            enriched = enrich_dom(raw_dom)
            self.last_dom_tree = enriched

            matches: List[Dict[str, Any]] = []
            self._find_nodes_recursive(enriched, by, value, matches)
            return {
                "content": [{"type": "text", "text": f"Found {len(matches)} matches"}],
                "matches": matches
            }

        # Write actions: click, type_text, set_value, invoke
        elif tool_name in ["click", "type_text", "set_value", "invoke"]:
            app_title = arguments.get("app_title") or self.current_app_title
            element_id = arguments["element_id"]

            # Capture DOM before action
            try:
                dom_before = enrich_dom(backend.get_dom(app_title))
            except Exception as e:
                logger.warning(f"Could not capture DOM before action: {e}")
                dom_before = self.last_dom_tree

            # Execute action
            success = False
            if tool_name == "click":
                success = backend.click(element_id)
            elif tool_name == "type_text":
                success = backend.type_text(element_id, arguments["text"])
            elif tool_name == "set_value":
                success = backend.set_value(element_id, arguments["value"])
            elif tool_name == "invoke":
                success = backend.invoke(element_id)

            # Wait briefly for UI to update
            time.sleep(0.3)

            # Capture DOM after action
            try:
                dom_after = enrich_dom(backend.get_dom(app_title))
                self.last_dom_tree = dom_after
            except Exception as e:
                logger.warning(f"Could not capture DOM after action: {e}")
                dom_after = None

            # Compute delta
            delta = compute_dom_delta(dom_before, dom_after)

            return {
                "content": [{"type": "text", "text": f"Action '{tool_name}' completed. Success: {success}"}],
                "success": success,
                "dom_delta": delta
            }

        elif tool_name == "read_value":
            element_id = arguments["element_id"]
            res = backend.read_value(element_id)
            return {
                "content": [{"type": "text", "text": f"Value read: {res}"}],
                "text": res.get("text", ""),
                "value": res.get("value"),
                "state": res.get("state")
            }

        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    def _find_nodes_recursive(self, node: Dict[str, Any], by: str, value: str, matches: List[Dict[str, Any]]) -> None:
        """Helper to find matches recursively in a DOM node."""
        if not node:
            return
        val_lower = value.lower()
        if by == "name" and val_lower in node.get("name", "").lower():
            matches.append(node)
        elif by == "auto_id" and val_lower in node.get("auto_id", "").lower():
            matches.append(node)
        elif by == "control_type" and val_lower == node.get("control_type", "").lower():
            matches.append(node)

        for child in node.get("children", []):
            self._find_nodes_recursive(child, by, value, matches)


def main() -> None:
    server = UIWindowsMCPServer()
    logger.info("UI Windows MCP Server started and listening on stdin...")

    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                logger.info("stdin closed, shutting down")
                break

            request = json.loads(line)
            req_id = request.get("id")
            method = request.get("method")
            params = request.get("params", {})

            response: Dict[str, Any] = {
                "jsonrpc": "2.0",
                "id": req_id
            }

            try:
                if method == "tools/list":
                    response["result"] = server.list_tools()
                elif method == "tools/call":
                    tool_name = params.get("name")
                    arguments = params.get("arguments", {})
                    response["result"] = server.dispatch(tool_name, arguments)
                else:
                    response["error"] = {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
            except Exception as e:
                logger.error(f"Error handling request: {e}\n{traceback.format_exc()}")
                response["error"] = {
                    "code": -32603,
                    "message": f"Internal error: {e}"
                }

            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()

        except Exception as e:
            logger.error(f"Fatal error in server loop: {e}\n{traceback.format_exc()}")
            break


if __name__ == "__main__":
    main()
