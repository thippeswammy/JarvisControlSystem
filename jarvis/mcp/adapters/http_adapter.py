"""
HTTP MCP Adapter
================
Communicates with an MCP server over HTTP using :mod:`urllib.request`
(no external dependencies).

Tool listing uses GET, tool calls use POST, and health checks
hit a ``/health`` endpoint.
"""

import json
import logging
import urllib.error
import urllib.request
from typing import Any

from jarvis.mcp.mcp_interface import MCPInterface

logger = logging.getLogger(__name__)


class HttpMCPAdapter(MCPInterface):
    """
    MCP adapter that talks to a server over HTTP.

    Usage::

        adapter = HttpMCPAdapter(
            name="remote-server",
            url="http://localhost:8080",
        )
        tools = adapter.list_tools()
        result = adapter.call("search", {"query": "hello"})
    """

    def __init__(
        self,
        name: str,
        url: str,
        description: str = "",
        timeout: float = 30.0,
    ) -> None:
        self._name = name
        self._url = url.rstrip("/")
        self._description = description
        self._timeout = timeout

    # ── Properties ───────────────────────────────────

    @property
    def name(self) -> str:
        return self._name

    @property
    def transport(self) -> str:
        return "http"

    # ── Public API ───────────────────────────────────

    def list_tools(self) -> list[dict]:
        """GET ``/tools`` and return normalised tool descriptors."""
        try:
            data = self._request("/tools")
            raw_tools = data if isinstance(data, list) else data.get("tools", [])
            return [
                {
                    "name": t.get("name", ""),
                    "description": t.get("description", ""),
                    "params": t.get("inputSchema", t.get("params", {})),
                }
                for t in raw_tools
            ]
        except Exception as exc:
            logger.error(f"[HttpMCP:{self._name}] list_tools failed: {exc}")
            return []

    def call(self, tool: str, params: dict) -> dict:
        """POST ``/tools/call`` with the tool name and arguments."""
        try:
            payload = {"name": tool, "arguments": params}
            result = self._request("/tools/call", payload=payload)
            return result if isinstance(result, dict) else {"result": result}
        except Exception as exc:
            logger.error(f"[HttpMCP:{self._name}] call({tool}) failed: {exc}")
            return {"error": str(exc)}

    def health_check(self) -> bool:
        """GET ``/health`` — returns True on HTTP 200."""
        try:
            self._request("/health")
            return True
        except Exception:
            return False

    # ── Private helpers ──────────────────────────────

    def _request(
        self,
        endpoint: str,
        payload: dict | None = None,
    ) -> Any:
        """
        Make an HTTP request to the MCP server.

        Uses POST when *payload* is provided, GET otherwise.
        """
        url = f"{self._url}{endpoint}"

        if payload is not None:
            body = json.dumps(payload).encode()
            req = urllib.request.Request(
                url,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
        else:
            req = urllib.request.Request(url, method="GET")

        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                raw = resp.read().decode()
                if not raw:
                    return {}
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            logger.error(
                f"[HttpMCP:{self._name}] HTTP {exc.code} from "
                f"{endpoint}: {exc.reason}"
            )
            raise
        except urllib.error.URLError as exc:
            logger.error(
                f"[HttpMCP:{self._name}] Connection error for "
                f"{endpoint}: {exc.reason}"
            )
            raise
        except TimeoutError:
            logger.error(
                f"[HttpMCP:{self._name}] Timeout ({self._timeout}s) "
                f"for {endpoint}"
            )
            raise
