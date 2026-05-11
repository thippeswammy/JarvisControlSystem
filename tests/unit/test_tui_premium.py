import pytest
from rich.text import Text
from jarvis.tui.tui_app import TUIMessageHistory
from jarvis.gateway.slash_handler import SlashHandler
from unittest.mock import MagicMock

def test_tui_message_history_ansi():
    history = TUIMessageHistory(max_messages=10)
    
    # Test raw ANSI conversion
    ansi_msg = "\x1b[1;36m🛰 Systems Online\x1b[0m"
    history.add("JARVIS", ansi_msg)
    
    # Check if the message is stored as Text and not raw string
    rendered = history.messages[0]
    assert isinstance(rendered, Text)
    # The rendered text should contain the content but not the literal escape sequences as characters
    assert "🛰 Systems Online" in rendered.plain
    assert "\x1b" not in rendered.plain

def test_tui_message_history_markup():
    history = TUIMessageHistory(max_messages=5)
    
    # Test Rich markup
    markup_msg = "[bold red]DANGER[/bold red]"
    history.add("SYSTEM", markup_msg)
    
    rendered = history.messages[0]
    assert "DANGER" in rendered.plain
    # Check that the markup brackets were parsed (not present in the plain text of the content)
    # The plain text of the entire message starts with [HH:MM:SS], so we check after that.
    content_part = rendered.plain.split(" › ")[1]
    assert "[" not in content_part 


def test_tui_message_history_overflow():
    history = TUIMessageHistory(max_messages=2)
    history.add("USER", "msg1")
    history.add("USER", "msg2")
    history.add("USER", "msg3")
    
    assert len(history.messages) == 2
    assert "msg2" in history.messages[0].plain
    assert "msg3" in history.messages[1].plain

def test_slash_handler_status_formatting():
    mock_gateway = MagicMock()
    mock_session = MagicMock()
    mock_session.id = "test_session"
    
    mock_gateway.status.return_value = {
        "running": True,
        "channels": [{"name": "tui", "status": "running"}],
        "sessions": 5,
        "memory": "jarvis.db"
    }
    
    handler = SlashHandler(mock_session, mock_gateway)
    reply = handler.handle("/status")
    
    assert "✅" in reply
    assert "tui (running)" in reply
    assert "Total Sessions: 5" in reply

def test_slash_handler_help():
    handler = SlashHandler(MagicMock(), MagicMock())
    reply = handler.handle("/help")
    assert "/status" in reply
    assert "/reset" in reply
