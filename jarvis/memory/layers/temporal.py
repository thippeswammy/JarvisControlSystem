"""
Structured Temporal Memory Layer — Full Implementation
======================================================
Persists a chronological event record of all actions taken by Jarvis,
including timestamp, app context, action executed, success/failure status,
and latency duration in milliseconds.

Provides the agent with time-awareness and enables answering temporal queries
like "What was I working on a few minutes ago?" or "Did I close Notepad recently?".
"""

import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_DB_DEFAULT = str(_PROJECT_ROOT / "memory" / "jarvis.db")


class TemporalMemory:
    """
    Structured SQLite-backed timeline memory layer tracking actions and context.
    """

    _SCHEMA = """
    CREATE TABLE IF NOT EXISTS temporal_events (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp       TEXT NOT NULL,
        app_context     TEXT DEFAULT '',
        action          TEXT NOT NULL,
        status          TEXT NOT NULL,
        duration_ms     INTEGER DEFAULT 0
    );
    CREATE INDEX IF NOT EXISTS idx_temporal_ts ON temporal_events(timestamp);
    """

    def __init__(self, db_path: str = _DB_DEFAULT):
        if db_path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._init_db()
        logger.info(f"[TemporalMemory] Initialized with DB: {db_path}")

    def _init_db(self):
        """Create the temporal memory tables if they don't exist."""
        with self._conn:
            self._conn.executescript(self._SCHEMA)

    def log_event(
        self,
        app_context: str,
        action: str,
        status: str,
        duration_ms: int,
        timestamp: Optional[str] = None
    ) -> None:
        """
        Record a temporal action event in the database.
        
        Args:
            app_context: Active application name (e.g. "settings", "notepad")
            action: Descriptive action string (e.g. "clicked 'Windows Update'")
            status: Execution status ("SUCCESS" or "FAILED")
            duration_ms: Execution duration in milliseconds
            timestamp: Optional ISO-8601 timestamp overrides (default is now)
        """
        ts = timestamp or datetime.now().isoformat(timespec="seconds")
        
        # Ensure status is uppercase
        status_upper = status.upper().strip()
        
        with self._conn:
            self._conn.execute("""
                INSERT INTO temporal_events (timestamp, app_context, action, status, duration_ms)
                VALUES (?, ?, ?, ?, ?)
            """, (ts, app_context, action, status_upper, duration_ms))
            
        logger.debug(f"[TemporalMemory] Logged event: {ts} | {app_context} | {action} | {status_upper} ({duration_ms}ms)")

    def get_timeline(self, since_iso: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Fetch chronological events sorted by timestamp descending.
        
        Args:
            since_iso: Optional ISO-8601 string to filter events starting after this time
            limit: Maximum number of records to retrieve (default: 50)
            
        Returns:
            List of dictionaries representing temporal events.
        """
        query = "SELECT * FROM temporal_events"
        params = []
        
        if since_iso:
            query += " WHERE timestamp >= ?"
            params.append(since_iso)
            
        query += " ORDER BY timestamp DESC, id DESC LIMIT ?"
        params.append(limit)
        
        rows = self._conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def clear(self) -> None:
        """Clear all events in the temporal timeline."""
        with self._conn:
            self._conn.execute("DELETE FROM temporal_events")
        logger.info("[TemporalMemory] Timeline cleared.")

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    def as_llm_context(self, limit: int = 5) -> str:
        """
        Generates a compact timeline view for LLM context injection.
        
        Args:
            limit: Number of recent events to include in the context
            
        Returns:
            A formatted string of the recent temporal history.
        """
        events = self.get_timeline(limit=limit)
        if not events:
            return "(no recent activity recorded)"
            
        # Format events into human-readable list, starting from oldest to newest for chronological flow
        lines = []
        for event in reversed(events):
            app = event.get("app_context") or "system"
            lines.append(
                f"  - {event['timestamp']} [{event['status']}] App: {app} | "
                f"Action: {event['action']} ({event['duration_ms']}ms)"
            )
        return "Recent timeline:\n" + "\n".join(lines)
