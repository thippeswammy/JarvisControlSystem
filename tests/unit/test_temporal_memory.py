import pytest
from datetime import datetime, timedelta
from jarvis.memory.layers.temporal import TemporalMemory
from jarvis.memory.layers.episodic import EpisodicMemory

def test_temporal_memory_init():
    # Test initialization with in-memory database
    tm = TemporalMemory(":memory:")
    assert tm._db_path == ":memory:"
    
    # Check that query succeeds on the initialized table
    timeline = tm.get_timeline()
    assert isinstance(timeline, list)
    assert len(timeline) == 0
    tm.close()

def test_temporal_memory_log_and_fetch():
    tm = TemporalMemory(":memory:")
    
    # Log some events
    tm.log_event(app_context="notepad", action="executed type_text", status="SUCCESS", duration_ms=150)
    tm.log_event(app_context="settings", action="executed click", status="FAILED", duration_ms=500)
    
    timeline = tm.get_timeline()
    assert len(timeline) == 2
    
    # Most recent first
    assert timeline[0]["app_context"] == "settings"
    assert timeline[0]["status"] == "FAILED"
    assert timeline[0]["duration_ms"] == 500
    
    assert timeline[1]["app_context"] == "notepad"
    assert timeline[1]["status"] == "SUCCESS"
    assert timeline[1]["duration_ms"] == 150
    
    tm.close()

def test_temporal_memory_since_filter():
    tm = TemporalMemory(":memory:")
    
    t1 = (datetime.now() - timedelta(minutes=10)).isoformat(timespec="seconds")
    t2 = datetime.now().isoformat(timespec="seconds")
    
    tm.log_event(app_context="notepad", action="first action", status="SUCCESS", duration_ms=100, timestamp=t1)
    tm.log_event(app_context="settings", action="second action", status="SUCCESS", duration_ms=200, timestamp=t2)
    
    # Filter since t2
    timeline = tm.get_timeline(since_iso=t2)
    assert len(timeline) == 1
    assert timeline[0]["action"] == "second action"
    
    tm.close()

def test_temporal_memory_clear():
    tm = TemporalMemory(":memory:")
    tm.log_event(app_context="notepad", action="first action", status="SUCCESS", duration_ms=100)
    
    assert len(tm.get_timeline()) == 1
    tm.clear()
    assert len(tm.get_timeline()) == 0
    
    tm.close()

def test_temporal_memory_as_llm_context():
    tm = TemporalMemory(":memory:")
    tm.log_event(app_context="notepad", action="type text", status="SUCCESS", duration_ms=150)
    
    ctx = tm.as_llm_context()
    assert "Recent timeline:" in ctx
    assert "notepad" in ctx
    assert "SUCCESS" in ctx
    assert "150ms" in ctx
    
    tm.close()

def test_episodic_temporal_integration():
    # Test that EpisodicMemory integrates TemporalMemory correctly
    tm = TemporalMemory(":memory:")
    tm.log_event(app_context="notepad", action="type text", status="SUCCESS", duration_ms=150)
    
    ep = EpisodicMemory(temporal_memory=tm)
    assert ep._temporal == tm
    
    ctx = ep.as_llm_context(include_current=False)
    assert "Recent timeline:" in ctx
    assert "notepad" in ctx
    assert "SUCCESS" in ctx
    assert "150ms" in ctx
    
    tm.close()
