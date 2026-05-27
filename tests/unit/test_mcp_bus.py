"""
Unit tests for jarvis.mcp.mcp_bus
"""

import unittest
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path

from jarvis.mcp.mcp_interface import MCPInterface
from jarvis.mcp.mcp_bus import MCPBus
from jarvis.mcp.adapters.stdio_adapter import StdioMCPAdapter
from jarvis.mcp.adapters.http_adapter import HttpMCPAdapter


class MockMCPAdapter(MCPInterface):
    def __init__(self, name="mock-server", transport="stdio"):
        self._name = name
        self._transport = transport
        self.call_called = 0
        self.shutdown_called = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def transport(self) -> str:
        return self._transport

    def list_tools(self) -> list[dict]:
        return [
            {
                "name": "greet",
                "description": "Greet a user",
                "params": {
                    "type": "object",
                    "properties": {
                        "username": {"type": "string"}
                    }
                }
            }
        ]

    def call(self, tool: str, params: dict) -> dict:
        self.call_called += 1
        if tool == "greet":
            return {"greeting": f"Hello, {params.get('username', 'stranger')}!"}
        return {"error": "unknown tool"}

    def health_check(self) -> bool:
        return True

    def shutdown(self) -> None:
        self.shutdown_called += 1


class TestMCPBus(unittest.TestCase):

    def test_mcp_bus_init(self):
        """Verify initialization of MCPBus."""
        bus = MCPBus()
        self.assertFalse(bus._discovered)
        self.assertEqual(len(bus._registry), 0)

    def test_manual_registration(self):
        """Verify manual registration of MCP adapters."""
        bus = MCPBus()
        adapter = MockMCPAdapter(name="mock-srv")
        bus.register(adapter)
        self.assertIn("mock-srv", bus._registry)
        self.assertEqual(bus._registry["mock-srv"], adapter)

    def test_call_success(self):
        """Verify dispatching a tool call to the appropriate server adapter."""
        bus = MCPBus()
        adapter = MockMCPAdapter(name="mock-srv")
        bus.register(adapter)

        res = bus.call("mock-srv", "greet", {"username": "IronMan"})
        self.assertEqual(res.get("greeting"), "Hello, IronMan!")
        self.assertEqual(adapter.call_called, 1)

    def test_call_not_found(self):
        """Verify handling calls to a non-existent server."""
        bus = MCPBus()
        res = bus.call("nonexistent", "greet", {})
        self.assertIn("error", res)
        self.assertIn("not found", res["error"])

    def test_list_servers(self):
        """Verify list_servers returns sorted list of registered servers."""
        bus = MCPBus()
        bus.register(MockMCPAdapter(name="server-b"))
        bus.register(MockMCPAdapter(name="server-a"))
        self.assertEqual(bus.list_servers(), ["server-a", "server-b"])

    def test_get_tool_catalog_online(self):
        """Verify formatting of catalog with online tools."""
        bus = MCPBus()
        adapter = MockMCPAdapter(name="mock-srv")
        bus.register(adapter)

        catalog = bus.get_tool_catalog()
        self.assertEqual(catalog, "[mock-srv] greet(username): Greet a user")

    def test_get_tool_catalog_offline(self):
        """Verify formatting of catalog when server is offline/raises exception."""
        bus = MCPBus()
        adapter = MockMCPAdapter(name="broken")
        def broken_list_tools():
            raise RuntimeError("server offline")
        adapter.list_tools = broken_list_tools
        bus.register(adapter)

        catalog = bus.get_tool_catalog()
        self.assertEqual(catalog, "broken: offline")

    def test_shutdown_all(self):
        """Verify shutdown is called on every registered adapter."""
        bus = MCPBus()
        a1 = MockMCPAdapter(name="srv1")
        a2 = MockMCPAdapter(name="srv2")
        bus.register(a1)
        bus.register(a2)

        bus.shutdown_all()
        self.assertEqual(a1.shutdown_called, 1)
        self.assertEqual(a2.shutdown_called, 1)

    def test_build_adapter_stdio(self):
        """Verify building a stdio adapter from configuration dict."""
        bus = MCPBus()
        entry = {
            "name": "fs-server",
            "transport": "stdio",
            "command": ["python", "fs.py"],
            "description": "Filesystem tools"
        }
        adapter = bus._build_adapter(entry)
        self.assertIsInstance(adapter, StdioMCPAdapter)
        self.assertEqual(adapter.name, "fs-server")
        self.assertEqual(adapter.transport, "stdio")

    def test_build_adapter_http(self):
        """Verify building an HTTP adapter from configuration dict."""
        bus = MCPBus()
        entry = {
            "name": "web-server",
            "transport": "http",
            "url": "http://localhost:8000",
            "description": "Web tools",
            "timeout": 15.0
        }
        adapter = bus._build_adapter(entry)
        self.assertIsInstance(adapter, HttpMCPAdapter)
        self.assertEqual(adapter.name, "web-server")
        self.assertEqual(adapter.transport, "http")

    def test_build_adapter_invalid(self):
        """Verify raising errors on invalid adapter configs."""
        bus = MCPBus()
        # Stdio without command
        with self.assertRaises(ValueError):
            bus._build_adapter({"name": "err1", "transport": "stdio"})

        # HTTP without url
        with self.assertRaises(ValueError):
            bus._build_adapter({"name": "err2", "transport": "http"})

        # Unknown transport
        with self.assertRaises(ValueError):
            bus._build_adapter({"name": "err3", "transport": "ftp"})

    @patch("builtins.open", new_callable=mock_open, read_data="""
- name: srv1
  transport: stdio
  command: ["cmd1"]
- name: srv2
  transport: http
  url: "http://url"
""")
    @patch("pathlib.Path.exists", return_value=True)
    def test_discover_config(self, mock_exists, mock_file):
        """Verify loading definitions from YAML and performing discovery registration."""
        bus = MCPBus()
        loaded = bus.discover(config_path="/fake/path.yaml")
        self.assertEqual(loaded, 2)
        self.assertTrue(bus._discovered)
        self.assertIn("srv1", bus._registry)
        self.assertIn("srv2", bus._registry)
