"""
Stdio MCP Adapter
=================
Communicates with an MCP server over stdin/stdout using JSON-RPC 2.0.

The adapter lazily spawns the server process on first use and
terminates it when :meth:`shutdown` is called.
"""

import json
import logging
import subprocess
import threading
from typing import Optional

from jarvis.mcp.mcp_interface import MCPInterface

logger = logging.getLogger(__name__)


class StdioMCPAdapter(MCPInterface):
    """
    MCP adapter that talks to a server process via stdio.

    Usage::

        adapter = StdioMCPAdapter(
            name="my-server",
            command=["node", "server.js"],
        )
        tools = adapter.list_tools()
        result = adapter.call("search", {"query": "hello"})
        adapter.shutdown()
    """

    def __init__(
        self,
        name: str,
        command: list[str],
        description: str = "",
    ) -> None:
        self._name = name
        self._command = command
        self._description = description
        self._process: Optional[subprocess.Popen] = None
        self._request_id = 0
        self._lock = threading.Lock()

    # ── Properties ───────────────────────────────────

    @property
    def name(self) -> str:
        return self._name

    @property
    def transport(self) -> str:
        return "stdio"

    # ── Public API ───────────────────────────────────

    def list_tools(self) -> list[dict]:
        """Query the MCP server for its tool catalog."""
        try:
            resp = self._send_request("tools/list", {})
            raw_tools = resp.get("result", {}).get("tools", [])
            return [
                {
                    "name": t.get("name", ""),
                    "description": t.get("description", ""),
                    "params": t.get("inputSchema", {}),
                }
                for t in raw_tools
            ]
        except Exception as exc:
            logger.error(f"[StdioMCP:{self._name}] list_tools failed: {exc}")
            return []

    def call(self, tool: str, params: dict) -> dict:
        """Call *tool* with *params* on the MCP server."""
        try:
            resp = self._send_request(
                "tools/call",
                {"name": tool, "arguments": params},
            )
            return resp.get("result", resp)
        except Exception as exc:
            logger.error(f"[StdioMCP:{self._name}] call({tool}) failed: {exc}")
            return {"error": str(exc)}

    def health_check(self) -> bool:
        """Return True if the subprocess is still running."""
        if self._process is None:
            return False
        return self._process.poll() is None

    def shutdown(self) -> None:
        """Terminate the server subprocess if running."""
        if self._process is not None:
            logger.info(f"[StdioMCP:{self._name}] Shutting down process")
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except Exception as exc:
                logger.warning(
                    f"[StdioMCP:{self._name}] Graceful shutdown failed, "
                    f"killing: {exc}"
                )
                try:
                    self._process.kill()
                except OSError:
                    pass
            finally:
                self._process = None

    # ── Private helpers ──────────────────────────────

    def _ensure_running(self) -> None:
        """Spawn the server process if it is not already running."""
        if self._process is not None and self._process.poll() is None:
            return  # already alive

        logger.info(
            f"[StdioMCP:{self._name}] Launching: {' '.join(self._command)}"
        )
        try:
            self._process = subprocess.Popen(
                self._command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            logger.error(
                f"[StdioMCP:{self._name}] Command not found: {exc}"
            )
            raise
        except OSError as exc:
            logger.error(
                f"[StdioMCP:{self._name}] Failed to launch process: {exc}"
            )
            raise

    def _send_request(self, method: str, params: dict) -> dict:
        """
        Send a JSON-RPC 2.0 request via stdin and read the response
        from stdout.

        Thread-safe via an internal lock so concurrent calls are
        serialised.
        """
        with self._lock:
            self._ensure_running()
            assert self._process is not None
            assert self._process.stdin is not None
            assert self._process.stdout is not None

            self._request_id += 1
            request = {
                "jsonrpc": "2.0",
                "id": self._request_id,
                "method": method,
                "params": params,
            }

            raw = json.dumps(request) + "\n"
            try:
                self._process.stdin.write(raw.encode())
                self._process.stdin.flush()

                line = self._process.stdout.readline()
                if not line:
                    raise RuntimeError("Server closed stdout (empty read)")

                return json.loads(line.decode())
            except (BrokenPipeError, OSError) as exc:
                logger.error(
                    f"[StdioMCP:{self._name}] Pipe error during "
                    f"{method}: {exc}"
                )
                self.shutdown()
                raise
