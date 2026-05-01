"""
Episodic Memory Layer — Full Implementation
===========================================
Records what happened in each session: commands, results, apps used.
Implements the retention policy (30 logs, then compress to index.md).

Design spec (Part 4, Layer 2):
  - Per-session log: memory/episodic/sessions/YYYY-MM-DD_HHMMSS.md
  - index.md: summary of frequent tasks and last-used apps (from all sessions)
  - Retention: keep last 30 session logs, compress older to index.md

Usage:
    ep = EpisodicMemory()
    ep.log_command("open display settings", success=True, app="settings")
    ep.save_session()         # called on shutdown

    ctx = ep.as_llm_context() # top-5 commands in last 3 sessions (for LLM RAG)
"""
import json
import logging
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_MEMORY_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "memory"
_SESSION_DIR = _MEMORY_ROOT / "episodic" / "sessions"
_INDEX_FILE  = _MEMORY_ROOT / "episodic" / "index.md"

# Retention: keep at most this many session log files.
# Older files are compressed into index.md and deleted.
_MAX_SESSION_LOGS = 30


class EpisodicMemory:
    """
    Records what Jarvis did in the current session and persists it to disk.

    One instance = one session. Create a new instance per process start.
    """

    def __init__(self):
        _SESSION_DIR.mkdir(parents=True, exist_ok=True)
        self._session_id = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        self._log: list[dict] = []
        self._start_time = datetime.now()

    # ── Recording ────────────────────────────────────────────────────────────

    def log_command(
        self,
        command: str,
        success: bool,
        app: str = "",
        skill: str = "",
        from_memory: bool = False,
    ) -> None:
        """Record one command execution in this session."""
        self._log.append({
            "ts": datetime.now().isoformat(timespec="seconds"),
            "cmd": command.strip(),
            "ok": success,
            "app": app,
            "skill": skill,
            "from_memory": from_memory,
        })

    # ── Persistence ──────────────────────────────────────────────────────────

    def save_session(self) -> Optional[Path]:
        """
        Write this session to disk.
        Applies retention policy: delete oldest logs if > MAX_SESSION_LOGS.
        Returns the path written, or None if no commands were logged.
        """
        if not self._log:
            logger.debug("[EpisodicMemory] Empty session — not saving.")
            return None

        path = _SESSION_DIR / f"{self._session_id}.md"
        duration_s = (datetime.now() - self._start_time).seconds

        lines = [
            f"# Session {self._session_id}",
            f"<!-- duration={duration_s}s commands={len(self._log)} -->",
            "",
        ]
        for entry in self._log:
            icon = "✅" if entry["ok"] else "❌"
            mem_tag = " [memory]" if entry.get("from_memory") else ""
            lines.append(
                f"- {entry['ts']} {icon} `{entry['cmd']}` "
                f"(app={entry['app']}, skill={entry['skill']}{mem_tag})"
            )

        path.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"[EpisodicMemory] Session saved: {path}")

        self._apply_retention_policy()
        self._rebuild_index()
        return path

    def _apply_retention_policy(self) -> None:
        """Delete the oldest session logs if we exceed MAX_SESSION_LOGS."""
        logs = sorted(_SESSION_DIR.glob("*.md"))
        excess = len(logs) - _MAX_SESSION_LOGS
        if excess > 0:
            for old_log in logs[:excess]:
                old_log.unlink(missing_ok=True)
                logger.debug(f"[EpisodicMemory] Purged old log: {old_log.name}")

    def _rebuild_index(self) -> None:
        """
        Rebuild index.md from all remaining session logs.
        Collects: total commands, success rate, top-5 commands, top-3 apps.
        """
        logs = sorted(_SESSION_DIR.glob("*.md"))
        all_cmds: list[str] = []
        all_apps: list[str] = []
        total_commands = 0
        total_success = 0

        for log_path in logs:
            for line in log_path.read_text(encoding="utf-8").splitlines():
                if not line.startswith("- "):
                    continue
                total_commands += 1
                if "✅" in line:
                    total_success += 1
                # Extract backtick-quoted command
                parts = line.split("`")
                if len(parts) >= 3:
                    all_cmds.append(parts[1])
                # Extract app=
                if "app=" in line:
                    try:
                        app_part = line.split("app=")[1].split(",")[0].split(")")[0].strip()
                        if app_part:
                            all_apps.append(app_part)
                    except IndexError:
                        pass

        cmd_counts = Counter(all_cmds).most_common(5)
        app_counts = Counter(all_apps).most_common(3)
        success_rate = f"{100*total_success//total_commands}%" if total_commands else "N/A"

        lines = [
            "# Episodic Memory — Index",
            f"<!-- sessions={len(logs)} total_commands={total_commands} success_rate={success_rate} -->",
            "",
            "## Frequent Commands",
        ]
        for cmd, count in cmd_counts:
            lines.append(f"- `{cmd}` × {count}")
        lines += ["", "## Frequent Apps"]
        for app, count in app_counts:
            lines.append(f"- {app} × {count}")
        lines += ["", f"## Sessions ({len(logs)} total)"]
        for log_path in reversed(logs[-10:]):  # last 10 session names
            lines.append(f"- {log_path.stem}")

        _INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
        _INDEX_FILE.write_text("\n".join(lines), encoding="utf-8")

    # ── LLM Context (RAG) ────────────────────────────────────────────────────

    def as_llm_context(self, max_sessions: int = 3, top_n: int = 5, include_current: bool = True) -> str:
        """
        Return a compact string summarising recent session history for LLM injection.
        Token budget: ~150 tokens max.
        """
        cmd_counter: Counter = Counter()
        
        # 1. Past sessions
        logs = sorted(_SESSION_DIR.glob("*.md"))
        recent_logs = logs[-max_sessions:] if logs else []
        for log_path in recent_logs:
            for line in log_path.read_text(encoding="utf-8").splitlines():
                if not line.startswith("- ") or "✅" not in line:
                    continue
                parts = line.split("`")
                if len(parts) >= 3:
                    cmd_counter[parts[1]] += 1

        # 2. Current session (most recent first)
        if include_current and self._log:
            for entry in reversed(self._log[-10:]):
                if entry["ok"]:
                    cmd_counter[entry["cmd"]] += 1

        top = cmd_counter.most_common(top_n)
        if not top:
            return "(no episodic history)"

        parts = ["Recent successful commands:"]
        for cmd, count in top:
            parts.append(f"  - '{cmd}' (×{count})")
        return "\n".join(parts)

    # ── Current session view ─────────────────────────────────────────────────

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def command_count(self) -> int:
        return len(self._log)

    @property
    def success_count(self) -> int:
        return sum(1 for e in self._log if e["ok"])
