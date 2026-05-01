"""Preference Memory Layer — stub (Phase 8 full implementation)"""
import logging
from collections import Counter

logger = logging.getLogger(__name__)


class PreferenceMemory:
    """Tracks user behavior patterns. Full impl in Phase 8."""

    def __init__(self):
        self._command_counts: Counter = Counter()
        self._app_counts: Counter = Counter()

    def record(self, command: str, app: str = "") -> None:
        self._command_counts[command.lower()] += 1
        if app:
            self._app_counts[app.lower()] += 1

    def top_commands(self, n: int = 5) -> list[str]:
        return [cmd for cmd, _ in self._command_counts.most_common(n)]

    def top_apps(self, n: int = 3) -> list[str]:
        return [app for app, _ in self._app_counts.most_common(n)]

    def as_context(self) -> str:
        cmds = self.top_commands()
        apps = self.top_apps()
        parts = []
        if cmds:
            parts.append(f"Frequent commands: {', '.join(cmds)}")
        if apps:
            parts.append(f"Frequent apps: {', '.join(apps)}")
        return "\n".join(parts) if parts else "(no preferences yet)"
