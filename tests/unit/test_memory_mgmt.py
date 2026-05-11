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
