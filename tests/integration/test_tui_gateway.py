import pytest
import time
from unittest.mock import MagicMock
from jarvis.gateway.gateway import GatewayDaemon
from jarvis.input.adapters import TUIAdapter

def test_tui_gateway_flow():
    """Verify that a message from the TUI reaches the orchestrator and returns a reply."""
    gateway = GatewayDaemon()
    gateway.bootstrap()
    
    # Mock LLM and SemanticEncoder
    gateway.memory._encoder.embed = MagicMock(return_value=None)
    
    from jarvis.llm.llm_interface import LLMDecision
    mock_decision = LLMDecision(
        type="chat",
        message="Hello from TUI integration test!",
        steps=[]
    )
    gateway.router.decide = MagicMock(return_value=mock_decision)
    
    adapter = TUIAdapter()
    gateway.channel_mgr.add_channel(adapter)
    
    try:
        gateway.start()
        time.sleep(1) # Let threads start
        
        # 1. Send message from TUI
        adapter.simulate_input("test message")
        
        # 2. Wait for reply in output queue
        reply = None
        for _ in range(10):
            try:
                reply = adapter.get_output_queue().get(timeout=1.0)
                break
            except:
                continue
                
        assert reply is not None
        assert "Hello" in reply
        
    finally:
        gateway.stop()
