"""
Slash Registry
==============
Dynamic registry for pluggable slash commands.  Allows agents, skills, and core
subsystems to register commands dynamically.
"""

import logging
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SlashEntry:
    """A registered slash command definition."""

    cmd: str
    handler: Callable
    description: str
    category: str = "general"


class SlashRegistry:
    """Central registry of all slash commands in the Jarvis OS."""

    _commands: Dict[str, SlashEntry] = {}

    @classmethod
    def register(
        cls,
        cmd: str,
        handler: Callable,
        description: str,
        category: str = "general",
    ) -> None:
        """
        Register a new slash command handler.

        Parameters
        ----------
        cmd:
            The slash command (e.g. "/help" or "/spin"). MUST start with "/".
        handler:
            Callable invoking the command: ``def handler(args, session, gateway) -> str``.
        description:
            Help text for the command.
        category:
            Category grouping (e.g. "general", "agent", "mcp").
        """
        if not cmd.startswith("/"):
            cmd = f"/{cmd}"
        cmd_lower = cmd.lower()
        cls._commands[cmd_lower] = SlashEntry(
            cmd=cmd_lower,
            handler=handler,
            description=description,
            category=category,
        )
        logger.debug(f"[SlashRegistry] Registered command: {cmd_lower} ({category})")

    @classmethod
    def unregister(cls, cmd: str) -> None:
        """Unregister a slash command."""
        if not cmd.startswith("/"):
            cmd = f"/{cmd}"
        cmd_lower = cmd.lower()
        if cmd_lower in cls._commands:
            del cls._commands[cmd_lower]
            logger.debug(f"[SlashRegistry] Unregistered command: {cmd_lower}")

    @classmethod
    def handle(cls, cmd: str, args: List[str], session, gateway) -> Optional[str]:
        """
        Lookup and execute the command. Returns the result string or None if not found.
        """
        cmd_lower = cmd.lower()
        entry = cls._commands.get(cmd_lower)
        if entry is None:
            return None
        try:
            return entry.handler(args, session, gateway)
        except Exception as exc:
            logger.exception(f"Error handling slash command {cmd_lower}: {exc}")
            return f"❌ Error executing command `{cmd_lower}`: {exc}"

    @classmethod
    def list_commands(cls) -> Dict[str, SlashEntry]:
        """Return a copy of all registered commands."""
        return dict(cls._commands)
