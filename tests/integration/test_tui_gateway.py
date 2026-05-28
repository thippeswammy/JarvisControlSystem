import pytest
import time
from unittest.mock import MagicMock
from jarvis.gateway.gateway import GatewayDaemon
from jarvis.input.adapters import TUIAdapter

def test_tui_gateway_flow():
    """Verify that a message from the TUI reaches the orchestrator and returns a reply."""
    gateway = GatewayDaemon()
    gateway.bootstrap()
    
    adapter = TUIAdapter()
    gateway.channel_mgr.add_channel(adapter)
    
    try:
        gateway.start()
        time.sleep(1) # Let threads start
        
        # 1. Send message from TUI
        adapter.simulate_input("test message")
        
        # 2. Wait for reply in output queue
        replies = []
        for _ in range(20):
            try:
                msg = adapter.get_output_queue().get(timeout=2.0)
                replies.append(msg)
                if any("hello" in r.lower() or "jarvis" in r.lower() or "how" in r.lower() or "test" in r.lower() for r in replies):
                    break
            except:
                continue
                
        assert len(replies) > 0, "No replies received from TUI"
        assert any("hello" in r.lower() or "jarvis" in r.lower() or "how" in r.lower() or "test" in r.lower() for r in replies), f"Expected response in replies, got: {replies}"
        
    finally:
        gateway.stop()
