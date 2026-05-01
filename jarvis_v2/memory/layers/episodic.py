"""Episodic Memory Layer — stub (Phase 8 full implementation)"""
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)
_SESSION_DIR = Path(__file__).parent.parent.parent.parent / "memory" / "episodic" / "sessions"


class EpisodicMemory:
    """Records what happened in each session. Full impl in Phase 8."""

    def __init__(self):
        _SESSION_DIR.mkdir(parents=True, exist_ok=True)
        self._session_id = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        self._log: list[dict] = []

    def log_command(self, command: str, success: bool, app: str = "") -> None:
        self._log.append({
            "ts": datetime.now().isoformat(),
            "cmd": command,
            "ok": success,
            "app": app,
        })

    def save_session(self) -> None:
        """Write session log to disk. Called on shutdown."""
        path = _SESSION_DIR / f"{self._session_id}.md"
        lines = [f"# Session {self._session_id}\n"]
        for entry in self._log:
            icon = "✅" if entry["ok"] else "❌"
            lines.append(f"- {entry['ts']} {icon} `{entry['cmd']}` (app={entry['app']})")
        path.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"[EpisodicMemory] Session saved: {path}")
