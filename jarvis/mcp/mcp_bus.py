"""
MCPBus
======
Central registry that discovers, manages, and dispatches calls to
MCP (Model Context Protocol) server adapters.

Discovery reads ``jarvis/config/mcp_servers.yaml`` and instantiates
the appropriate adapter (stdio or HTTP) for each entry.

Usage::

    bus = MCPBus()
    bus.discover()
    result = bus.call("my-server", "search", {"query": "hello"})
    catalog = bus.get_tool_catalog()
    bus.shutdown_all()
"""

import logging
from pathlib import Path
from typing import Optional

from jarvis.mcp.mcp_interface import MCPInterface
from jarvis.mcp.adapters.stdio_adapter import StdioMCPAdapter
from jarvis.mcp.adapters.http_adapter import HttpMCPAdapter

logger = logging.getLogger(__name__)

try:
    import yaml  # type: ignore[import-untyped]
except ImportError:
    yaml = None  # type: ignore[assignment]
    logger.debug("[MCPBus] PyYAML not installed — YAML config loading disabled")

_DEFAULT_CONFIG = (
    Path(__file__).parent.parent / "config" / "mcp_servers.yaml"
)


class MCPBus:
    """
    Central MCP server registry and dispatcher.

    Mirrors the SkillBus pattern: discover → register → dispatch.
    """

    def __init__(self) -> None:
        self._registry: dict[str, MCPInterface] = {}  # name → adapter
        self._discovered = False

    # ── Discovery ────────────────────────────────────

    def discover(self, config_path: Optional[str] = None) -> int:
        """
        Load MCP server definitions from a YAML config file.

        Each entry in the YAML list should have::

            - name: my-server
              transport: stdio          # or 'http'
              command: ["node", "server.js"]   # stdio only
              url: http://localhost:8080        # http only
              description: "Optional description"
              timeout: 30.0                    # http only, optional

        Returns:
            Number of servers successfully loaded.
        """
        if self._discovered:
            logger.debug("[MCPBus] Servers already discovered. Skipping.")
            return len(self._registry)

        if yaml is None:
            logger.warning(
                "[MCPBus] Cannot discover — PyYAML is not installed"
            )
            return 0

        path = Path(config_path) if config_path else _DEFAULT_CONFIG
        if not path.exists():
            logger.info(f"[MCPBus] Config not found: {path}")
            return 0

        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or []
                if isinstance(data, dict):
                    entries = data.get("mcp_servers", [])
                    if entries is None:
                        entries = []
                else:
                    entries = data
        except Exception as exc:
            logger.error(f"[MCPBus] Failed to read config {path}: {exc}")
            return 0

        if not isinstance(entries, list):
            logger.error("[MCPBus] Config root must be a YAML list")
            return 0

        loaded = 0
        for entry in entries:
            try:
                adapter = self._build_adapter(entry)
                self.register(adapter)
                loaded += 1
            except Exception as exc:
                logger.warning(
                    f"[MCPBus] Skipping entry {entry.get('name', '?')}: {exc}"
                )

        self._discovered = True
        logger.info(
            f"[MCPBus] Discovered {loaded} MCP servers: "
            f"{sorted(self._registry.keys())}"
        )
        return loaded

    # ── Registration ─────────────────────────────────

    def register(self, adapter: MCPInterface) -> None:
        """Manually register an MCP adapter."""
        if adapter.name in self._registry:
            logger.warning(
                f"[MCPBus] Overriding existing server: {adapter.name!r}"
            )
        self._registry[adapter.name] = adapter
        logger.debug(f"[MCPBus] Registered server: {adapter.name!r}")

    # ── Dispatch ─────────────────────────────────────

    def call(self, server: str, tool: str, params: dict) -> dict:
        """
        Find an adapter by *server* name and call *tool* with *params*.

        Returns an error dict if the server is not found.
        """
        adapter = self._registry.get(server)
        if adapter is None:
            logger.error(f"[MCPBus] Server not found: {server!r}")
            return {"error": f"MCP server not found: {server!r}"}
        return adapter.call(tool, params)

    # ── Catalog ──────────────────────────────────────

    def get_tool_catalog(self) -> str:
        """
        Build a formatted catalog of all MCP servers and their tools
        suitable for injection into an LLM system prompt.

        Format per tool::

            [server_name] tool_name(params): description

        If a server is unreachable, its line reads::

            server_name: offline
        """
        lines: list[str] = []
        for name in sorted(self._registry.keys()):
            adapter = self._registry[name]
            try:
                tools = adapter.list_tools()
                if not tools:
                    lines.append(f"{name}: no tools")
                    continue
                for t in tools:
                    params_str = ", ".join(t.get("params", {}).get("properties", {}).keys())
                    desc = t.get("description", "")
                    lines.append(f"[{name}] {t['name']}({params_str}): {desc}")
            except Exception:
                lines.append(f"{name}: offline")
        return "\n".join(lines)

    # ── Listing / Lifecycle ──────────────────────────

    def list_servers(self) -> list[str]:
        """Return sorted list of registered server names."""
        return sorted(self._registry.keys())

    def shutdown_all(self) -> None:
        """Call :meth:`shutdown` on every registered adapter."""
        for name, adapter in self._registry.items():
            logger.info(f"[MCPBus] Shutting down: {name}")
            try:
                adapter.shutdown()
            except Exception as exc:
                logger.warning(
                    f"[MCPBus] Error shutting down {name}: {exc}"
                )

    # ── Private helpers ──────────────────────────────

    @staticmethod
    def _build_adapter(entry: dict) -> MCPInterface:
        """Instantiate the correct adapter from a config dict."""
        name = entry["name"]
        transport = entry.get("transport", "stdio")
        description = entry.get("description", "")

        if transport == "stdio":
            command = entry.get("command")
            if not command:
                raise ValueError(f"stdio adapter '{name}' requires 'command'")
            return StdioMCPAdapter(
                name=name,
                command=command,
                description=description,
            )

        if transport == "http":
            url = entry.get("url")
            if not url:
                raise ValueError(f"http adapter '{name}' requires 'url'")
            return HttpMCPAdapter(
                name=name,
                url=url,
                description=description,
                timeout=float(entry.get("timeout", 30.0)),
            )

        raise ValueError(f"Unknown transport {transport!r} for server {name!r}")
