import pytest
from unittest.mock import MagicMock
from jarvis.tui.tui_app import TUIApp
from jarvis.input.adapters import TUIAdapter

def test_tui_adapter_queues():
    adapter = TUIAdapter()
    adapter.simulate_input("hello")
    
    # Test stream
    stream = adapter.stream()
    utterance = next(stream)
    assert utterance.text == "hello"
    assert utterance.source == "tui"
    
    # Test send
    adapter.send("session_1", "reply")
    msg = adapter.get_output_queue().get()
    assert msg == "reply"

def test_tui_app_init():
    app = TUIApp(profile="default")
    assert app.gateway is not None
    assert app.adapter.name == "tui"
    assert app._running is False

@pytest.mark.timeout(5)
def test_tui_slash_logic():
    # Mock gateway and session
    mock_gateway = MagicMock()
    mock_session = MagicMock()
    mock_session.id = "tui:tui_user"
    
    from jarvis.gateway.slash_handler import SlashHandler
    handler = SlashHandler(mock_session, mock_gateway)
    
    # Test /status
    mock_gateway.status.return_value = {
        "running": True,
        "channels": [{"name": "tui", "status": "running"}],
        "sessions": 1,
        "memory": "test.db"
    }
    reply = handler.handle("/status")
    assert "JARVIS Status" in reply
    assert "tui (running)" in reply
