"""
MCP Interface
=============
Abstract base class for Model Context Protocol adapters.

Every MCP server adapter (stdio, HTTP, etc.) must implement this
interface so the MCPBus can discover tools and dispatch calls
uniformly.
"""

import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class MCPInterface(ABC):
    """
    Abstract base for all MCP server adapters.

    Subclasses must implement:
        - name        (property)  → human-readable server name
        - transport   (property)  → 'stdio' | 'http'
        - list_tools  ()          → tool descriptors
        - call        (tool, params) → result dict
        - health_check()          → True if the server is reachable
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable server name."""

    @property
    @abstractmethod
    def transport(self) -> str:
        """Transport type: 'stdio' or 'http'."""

    @abstractmethod
    def list_tools(self) -> list[dict]:
        """
        Return available tools from this MCP server.

        Each dict has:
            {"name": str, "description": str, "params": dict}
        """

    @abstractmethod
    def call(self, tool: str, params: dict) -> dict:
        """Call a tool on this MCP server and return the result dict."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the server is alive and reachable."""

    def shutdown(self) -> None:
        """Cleanup resources.  Default is a no-op."""
