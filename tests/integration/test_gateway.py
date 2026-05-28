import pytest
import time
import os
import sys
from unittest.mock import MagicMock

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from jarvis.gateway.gateway import GatewayDaemon
from jarvis.input.adapters import MockTelegramAdapter

def test_gateway_end_to_end():
    """
    Integration test: Start gateway with mock telegram,
    send message, check reply.
    """
    # 1. Setup gateway
    gateway = GatewayDaemon()
    gateway.bootstrap()
    
    # Force enable mock telegram and disable others for clean test
    mock_adapter = MockTelegramAdapter()
    gateway.channel_mgr._channels = {"telegram-test": mock_adapter}

    try:
        # 2. Start gateway (starts threads)
        gateway.start()
        time.sleep(1) # Wait for thread to spin up

        # 3. Simulate a message
        mock_adapter.simulate_message("how are you")

        # 4. Wait for processing (LLM might take a second)
        reply_received = False
        for _ in range(40):
            replies = mock_adapter.get_replies()
            if len(replies) >= 2:
                reply_received = True
                break
            time.sleep(0.5)

        assert reply_received, f"No final reply received from Jarvis in mock channel. Got replies: {mock_adapter.get_replies()}"

    finally:
        gateway.stop()

def test_gateway_slash_command():
    """
    Test that slash commands (e.g. /status) are intercepted and handled.
    """
    gateway = GatewayDaemon()
    gateway.bootstrap()
    
    # Mock SemanticEncoder and LLM
    gateway.memory._encoder.embed = MagicMock(return_value=None)
    
    mock_adapter = MockTelegramAdapter()
    gateway.channel_mgr._channels = {"telegram-test": mock_adapter}
    
    try:
        gateway.start()
        time.sleep(1)
        
        # Simulate slash command
        mock_adapter.simulate_message("/status")
        
        # Wait for reply
        reply_received = False
        for _ in range(20):
            replies = mock_adapter.get_replies()
            if replies:
                text = replies[0]["text"]
                assert "JARVIS Status" in text
                assert "telegram-test (running)" in text
                reply_received = True
                break
            time.sleep(0.5)
            
        assert reply_received, "No reply received for slash command"
        
    finally:
        gateway.stop()
