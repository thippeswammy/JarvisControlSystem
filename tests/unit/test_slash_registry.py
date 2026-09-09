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

    def test_register_duplicate_command_overwrites_silently(self):
        """register() has no duplicate-name check: registering the same
        command twice silently replaces the existing SlashEntry with the new
        one -- no exception, no warning surfaced to the caller, and the old
        handler becomes unreachable."""
        def first_handler(args, session, gateway):
            return "first"

        def second_handler(args, session, gateway):
            return "second"

        SlashRegistry.register("/dup", first_handler, "First description", "general")
        SlashRegistry.register("/dup", second_handler, "Second description", "agent")

        commands = SlashRegistry.list_commands()
        # Still exactly one entry -- overwritten in place, not appended.
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands["/dup"].handler, second_handler)
        self.assertEqual(commands["/dup"].description, "Second description")
        self.assertEqual(commands["/dup"].category, "agent")

        res = SlashRegistry.handle("/dup", [], MagicMock(), MagicMock())
        self.assertEqual(res, "second")  # only the newest handler is reachable

    def test_register_and_lookup_are_case_insensitive(self):
        """Both register() and handle() lowercase the command name, so a
        command registered with mixed case is stored lowercase and remains
        reachable regardless of the case used to invoke it."""
        def dummy_handler(args, session, gateway):
            return "ok"

        SlashRegistry.register("/TestCmd", dummy_handler, "Mixed case description")

        commands = SlashRegistry.list_commands()
        self.assertIn("/testcmd", commands)
        self.assertNotIn("/TestCmd", commands)

        # Lookup succeeds no matter what case is used to invoke it.
        self.assertEqual(SlashRegistry.handle("/TESTCMD", [], MagicMock(), MagicMock()), "ok")
        self.assertEqual(SlashRegistry.handle("/TestCmd", [], MagicMock(), MagicMock()), "ok")
        self.assertEqual(SlashRegistry.handle("/testcmd", [], MagicMock(), MagicMock()), "ok")

    def test_unregister_is_case_insensitive(self):
        """unregister() also normalizes case, so a command registered with
        one case can be removed by passing a different case."""
        def dummy_handler(args, session, gateway):
            return "ok"

        SlashRegistry.register("/CaseCmd", dummy_handler, "Description")
        self.assertIn("/casecmd", SlashRegistry.list_commands())

        SlashRegistry.unregister("/CASECMD")
        self.assertNotIn("/casecmd", SlashRegistry.list_commands())

    def test_concurrent_registration_from_multiple_threads(self):
        """_commands is a plain class-level dict mutated with no explicit
        lock. Registering many distinct commands concurrently from separate
        threads must not raise or drop entries (CPython dict __setitem__ is
        effectively atomic under the GIL, but this pins down the expected
        behavior as a regression guard)."""
        import threading

        num_threads = 25
        errors = []

        def register_one(i):
            try:
                SlashRegistry.register(
                    f"/concurrent{i}",
                    lambda args, session, gateway: "ok",
                    f"Concurrent test command {i}",
                )
            except Exception as exc:  # pragma: no cover - failure path
                errors.append(exc)

        threads = [threading.Thread(target=register_one, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [])
        commands = SlashRegistry.list_commands()
        self.assertEqual(len(commands), num_threads)
        for i in range(num_threads):
            self.assertIn(f"/concurrent{i}", commands)
