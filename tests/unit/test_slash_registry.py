"""
Unit tests for jarvis.gateway.slash_registry
"""

import unittest
from unittest.mock import MagicMock
from jarvis.gateway.slash_registry import SlashRegistry


class TestSlashRegistry(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Force import of slash_handler to populate core registry commands
        import jarvis.gateway.slash_handler
        cls._original_commands = dict(SlashRegistry._commands)

    @classmethod
    def tearDownClass(cls):
        SlashRegistry._commands.clear()
        SlashRegistry._commands.update(cls._original_commands)

    def setUp(self):
        # Clear command registry before each test to maintain isolation
        SlashRegistry._commands.clear()

    def tearDown(self):
        SlashRegistry._commands.clear()

    def test_register_and_list_commands(self):
        """Verify registering a command and listing all commands."""
        def dummy_handler(args, session, gateway):
            return "ok"

        SlashRegistry.register("/testcmd", dummy_handler, "Test command description", "general")
        commands = SlashRegistry.list_commands()
        self.assertIn("/testcmd", commands)
        self.assertEqual(commands["/testcmd"].description, "Test command description")
        self.assertEqual(commands["/testcmd"].category, "general")
        self.assertEqual(commands["/testcmd"].handler, dummy_handler)

    def test_register_normalizes_leading_slash(self):
        """Verify command name is normalized to include leading slash."""
        def dummy_handler(args, session, gateway):
            return "ok"

        SlashRegistry.register("noslash", dummy_handler, "Description")
        commands = SlashRegistry.list_commands()
        self.assertIn("/noslash", commands)
        self.assertNotIn("noslash", commands)

    def test_unregister(self):
        """Verify unregistering commands."""
        def dummy_handler(args, session, gateway):
            return "ok"

        SlashRegistry.register("/tounregister", dummy_handler, "Description")
        self.assertIn("/tounregister", SlashRegistry.list_commands())

        SlashRegistry.unregister("tounregister") # without slash
        self.assertNotIn("/tounregister", SlashRegistry.list_commands())

    def test_handle_success(self):
        """Verify executing a slash command successfully passes parameters."""
        session_mock = MagicMock()
        gateway_mock = MagicMock()

        called_args = []
        def handler(args, session, gateway):
            called_args.extend(args)
            self.assertEqual(session, session_mock)
            self.assertEqual(gateway, gateway_mock)
            return f"Processed args: {', '.join(args)}"

        SlashRegistry.register("/run", handler, "Run command")
        res = SlashRegistry.handle("/run", ["arg1", "arg2"], session_mock, gateway_mock)
        self.assertEqual(res, "Processed args: arg1, arg2")
        self.assertEqual(called_args, ["arg1", "arg2"])

    def test_handle_not_found(self):
        """Verify handle returns None if command not found."""
        res = SlashRegistry.handle("/nonexistent", [], MagicMock(), MagicMock())
        self.assertIsNone(res)

    def test_handle_exception_safety(self):
        """Verify that exceptions raised by command handlers are caught and formatted safely."""
        def broken_handler(args, session, gateway):
            raise ValueError("bad parameter value")

        SlashRegistry.register("/broken", broken_handler, "Broken command")
        res = SlashRegistry.handle("/broken", [], MagicMock(), MagicMock())
        self.assertIn("❌ Error executing command `/broken`", res)
        self.assertIn("bad parameter value", res)
