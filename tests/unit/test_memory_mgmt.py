import json
import os
import sqlite3

import pytest
from unittest.mock import MagicMock
from jarvis.memory.memory_manager import MemoryManager
from jarvis.memory.graph_db import GraphNode, GraphEdge

@pytest.fixture
def mock_db():
    db = MagicMock()
    db.get_all_nodes.return_value = [GraphNode(id="n1", app_id="a1", type="APP", label="L1")]
    db.get_all_edges.return_value = [
        GraphEdge(id="e1", from_id="n1", to_id="n2", triggers=["open browser"], confidence=0.8)
    ]
    db.list_apps.return_value = ["a1"]
    return db

def test_memory_stats(mock_db, tmp_path):
    db_file = tmp_path / "test_stats.db"
    
    # Don't write dummy content, let GraphDB initialize it
    mem = MemoryManager(str(db_file))
    mem._db = mock_db
    stats = mem.get_stats()
    
    assert stats["nodes"] == 1
    assert stats["edges"] == 1
    assert stats["db_size_kb"] >= 0

def test_memory_search(mock_db):
    mem = MemoryManager(":memory:")
    mem._db = mock_db
    
    # Fuzzy match
    results = mem.search_edges("browser")
    assert len(results) > 0
    assert results[0][0].id == "e1"

def test_memory_health(mock_db):
    mem = MemoryManager(":memory:")
    mem._db = mock_db

    health = mem.analyze_health()
    assert "low_confidence_count" in health
    assert "orphan_nodes_count" in health


# ── Missing / nonexistent DB path ─────────────────────────────────────
# These use a real temp SQLite DB (not a MagicMock) via tmp_db_path/tmp_path,
# since MemoryManager/GraphDB actually touch the filesystem on init.

def test_memory_manager_creates_missing_nested_dirs(tmp_path):
    """Pointing at a path whose parent directories don't exist yet must not
    raise: MemoryManager/GraphDB are expected to create the directory tree."""
    nested_path = tmp_path / "a" / "b" / "c" / "jarvis.db"
    assert not nested_path.parent.exists()

    mem = MemoryManager(str(nested_path))
    try:
        assert nested_path.parent.is_dir()
        assert nested_path.exists()
        stats = mem.get_stats()
        assert stats["nodes"] == 0
        assert stats["edges"] == 0
    finally:
        mem.close()


def test_memory_manager_nonexistent_db_file_bootstraps_empty_db(tmp_db_path):
    """A path that doesn't exist yet (the normal case) should become a
    valid, empty SQLite DB after init rather than erroring."""
    assert not os.path.exists(tmp_db_path)

    mem = MemoryManager(tmp_db_path)
    try:
        assert os.path.exists(tmp_db_path)
        stats = mem.get_stats()
        assert stats["nodes"] == 0
        assert stats["edges"] == 0
        assert stats["apps"] == 0
        assert stats["success_rate"] == 0
    finally:
        mem.close()


def test_memory_manager_rejects_non_sqlite_file(tmp_path):
    """If a file already exists at the path but isn't a SQLite DB (e.g. a
    stray/corrupted file), init should fail loudly instead of silently
    proceeding or corrupting the file further."""
    bad_path = tmp_path / "not_a_db.db"
    bad_path.write_bytes(b"this is not a sqlite database, just plain text")

    with pytest.raises(sqlite3.DatabaseError):
        MemoryManager(str(bad_path))


# ── Corrupt / malformed data in the DB ────────────────────────────────
# GraphDB does no defensive parsing of stored rows — these tests document
# (via a real temp DB with hand-inserted bad rows) what actually happens
# when data doesn't match the expected shape.

def test_get_stats_raises_on_malformed_node_json(tmp_db_path):
    """A malformed JSON blob in a node's ui_metadata column crashes
    get_all_nodes() (and therefore get_stats()) with json.JSONDecodeError —
    there is no try/except around the json.loads() in GraphDB._row_to_node."""
    mem = MemoryManager(tmp_db_path)
    try:
        conn = mem.get_db()._conn
        with conn:
            conn.execute(
                "INSERT INTO nodes (id, app_id, type, label, ui_metadata) "
                "VALUES (?, ?, ?, ?, ?)",
                ("bad.node", "app1", "APP", "Bad Node", "{not valid json"),
            )

        with pytest.raises(json.JSONDecodeError):
            mem.get_stats()
    finally:
        mem.close()


def test_search_edges_raises_on_null_triggers_json(tmp_db_path):
    """Storing JSON 'null' in the triggers column (instead of a JSON list)
    deserializes to None. search_edges() iterates `for trigger in
    edge.triggers` with no None-guard, so it crashes with TypeError instead
    of skipping the malformed edge. (get_relevant_context, by contrast, does
    guard with `if not edge.triggers: continue` — this is an inconsistency
    in how the two methods handle the same bad data.)"""
    mem = MemoryManager(tmp_db_path)
    try:
        conn = mem.get_db()._conn
        with conn:
            conn.execute(
                "INSERT INTO edges (id, from_id, to_id, triggers) VALUES (?, ?, ?, ?)",
                ("bad.edge", "n1", "n2", "null"),
            )

        with pytest.raises(TypeError):
            mem.search_edges("anything")
    finally:
        mem.close()


def test_get_stats_raises_on_non_numeric_confidence(tmp_db_path):
    """SQLite's dynamic typing allows a non-numeric string to be stored in
    the 'confidence' REAL column. GraphDB._row_to_edge does float(row[...])
    with no error handling, so a bad value crashes get_all_edges() (and
    therefore get_stats()) with ValueError."""
    mem = MemoryManager(tmp_db_path)
    try:
        conn = mem.get_db()._conn
        with conn:
            conn.execute(
                "INSERT INTO edges (id, from_id, to_id, confidence) VALUES (?, ?, ?, ?)",
                ("bad.edge2", "n1", "n2", "not-a-number"),
            )

        with pytest.raises(ValueError):
            mem.get_stats()
    finally:
        mem.close()


# ── Empty result sets ──────────────────────────────────────────────────
# Uses the `mock_memory` fixture: a real MemoryManager backed by a fresh
# temp SQLite DB (empty), with SemanticEncoder.embed patched so results are
# deterministic regardless of whether Ollama happens to be running.

def test_search_edges_empty_db_returns_empty_list(mock_memory):
    assert mock_memory.search_edges("open browser") == []


def test_recall_empty_db_returns_none(mock_memory):
    assert mock_memory.recall("open settings") is None


def test_analyze_health_empty_db(mock_memory):
    health = mock_memory.analyze_health()
    assert health["low_confidence_count"] == 0
    assert health["high_failure_count"] == 0
    assert health["orphan_nodes_count"] == 0
    # Note: suggestions is always length-3, with None placeholders rather
    # than being filtered down to only the active ones.
    assert health["suggestions"] == [None, None, None]


def test_get_relevant_context_empty_db_returns_placeholder(mock_memory):
    assert mock_memory.get_relevant_context("open settings") == "(no relevant memory)"


def test_get_stats_empty_db_has_zero_success_rate(mock_memory):
    stats = mock_memory.get_stats()
    assert stats["nodes"] == 0
    assert stats["edges"] == 0
    assert stats["apps"] == 0
    assert stats["total_runs"] == 0
    assert stats["success_rate"] == 0


def test_remove_edge_nonexistent_returns_false(mock_memory):
    assert mock_memory.remove_edge("does-not-exist") is False


def test_prune_edges_empty_db_returns_zero(mock_memory):
    assert mock_memory.prune_edges(0.5) == 0
