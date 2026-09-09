import contextlib
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


@pytest.mark.timeout(5)
def test_tui_sequential_slash_commands_carry_state():
    """Multiple slash commands run one after another via the same SlashHandler
    should each see the up-to-date session/gateway state, and side effects
    from an earlier command (e.g. /reset clearing episodic memory) must be
    visible without leaking stale results into later commands."""
    from jarvis.gateway.slash_handler import SlashHandler

    mock_gateway = MagicMock()
    mock_session = MagicMock()
    mock_session.id = "tui:tui_user"
    mock_session.channel = "tui"
    mock_session.user_id = "tui_user"

    handler = SlashHandler(mock_session, mock_gateway)

    # 1. /whoami reflects the session identity.
    reply_whoami = handler.handle("/whoami")
    assert "tui:tui_user" in reply_whoami

    # 2. /reset clears episodic memory on the SAME session object used above.
    reply_reset = handler.handle("/reset")
    assert "Session reset" in reply_reset
    mock_session.episodic.clear.assert_called_once()

    # 3. /status reflects the gateway's current state.
    mock_gateway.status.return_value = {
        "running": True,
        "channels": [{"name": "tui", "status": "running"}],
        "sessions": 1,
        "memory": "test.db",
    }
    reply_running = handler.handle("/status")
    assert "✅" in reply_running

    # 4. Running /status again after the gateway's state changes (simulating
    #    time passing between sequential commands) must reflect the NEW
    #    state -- proving the handler doesn't cache/carry a stale result
    #    across calls.
    mock_gateway.status.return_value = {
        "running": False,
        "channels": [],
        "sessions": 0,
        "memory": "test.db",
    }
    reply_stopped = handler.handle("/status")
    assert "❌" in reply_stopped
    assert reply_running != reply_stopped

    # /reset must only have fired once across the whole sequence.
    mock_session.episodic.clear.assert_called_once()


@pytest.mark.timeout(5)
def test_tui_slash_command_exception_is_caught_and_reported():
    """A registry-dispatched slash command that raises must not crash the
    TUI: SlashRegistry.handle() wraps handler execution in try/except and
    turns the exception into a user-facing error string."""
    from jarvis.gateway.slash_handler import SlashHandler
    from jarvis.gateway.slash_registry import SlashRegistry

    mock_gateway = MagicMock()
    mock_session = MagicMock()
    mock_session.id = "tui:tui_user"

    def broken_handler(args, session, gateway):
        raise ValueError("simulated command failure")

    SlashRegistry.register("/tui_broken_test", broken_handler, "Broken test command")
    try:
        handler = SlashHandler(mock_session, mock_gateway)
        reply = handler.handle("/tui_broken_test")
        assert reply is not None
        assert "Error executing command" in reply
        assert "simulated command failure" in reply
    finally:
        SlashRegistry.unregister("/tui_broken_test")


@pytest.mark.timeout(5)
def test_tui_slash_agent_shorthand_exception_propagates_uncaught():
    """Documents a real inconsistency: registry-dispatched commands are
    protected by SlashRegistry.handle()'s try/except, but the "/<agent_name>
    <task>" shorthand branch in SlashHandler.handle() calls _cmd_spin
    directly with no exception guard. A crashing agent therefore propagates
    all the way out of handle() instead of degrading to an error string like
    the registry path does."""
    from jarvis.gateway.slash_handler import SlashHandler

    mock_gateway = MagicMock()
    mock_gateway.agent_bus._registry = {"crashyagent": MagicMock()}
    mock_gateway.agent_bus.run_single.side_effect = RuntimeError("agent blew up")

    mock_session = MagicMock()
    mock_session.id = "tui:tui_user"

    handler = SlashHandler(mock_session, mock_gateway)

    with pytest.raises(RuntimeError, match="agent blew up"):
        handler.handle("/crashyagent do something")


@pytest.mark.timeout(5)
def test_tui_output_loop_silently_swallows_processing_exceptions():
    """_output_loop's bare `except:` is used both to poll past queue.Empty
    timeouts AND to catch any exception raised while processing a message
    (e.g. inside history.add()). Verify the real behavior: such an error is
    silently discarded -- no crash, no re-raise -- and the loop just keeps
    polling."""
    app = TUIApp(profile="default")
    app._running = True

    seen = []

    def fake_add(sender, message, style="#00d7ff"):
        seen.append(message)
        raise RuntimeError("boom while processing message")

    app.history.add = fake_add

    out_queue = app.adapter.get_output_queue()
    out_queue.put("first message")
    out_queue.put(None)  # sentinel: causes _output_loop to break and return

    # Runs synchronously (not in a thread) -- if the bare except didn't
    # swallow the RuntimeError, this call itself would raise.
    initial_count = len(app.history.messages)  # __init__ already added a "boot" message

    app._output_loop()

    assert seen == ["first message"]
    # The message was never actually recorded since fake_add raised before
    # doing anything -- confirming the failure is silent and lossy, and no
    # new message was appended beyond what __init__ had already added.
    assert len(app.history.messages) == initial_count


def test_tui_app_stop_sets_running_false_and_stops_gateway():
    """Direct shutdown/teardown path: stop() must flip the running flag and
    delegate teardown to the gateway."""
    app = TUIApp(profile="default")
    app._running = True
    app.gateway = MagicMock()

    app.stop()

    assert app._running is False
    app.gateway.stop.assert_called_once()


class _FakeLive:
    """Stand-in for rich.live.Live that behaves as a real context manager
    (does not swallow exceptions) without touching the terminal."""

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeConsoleSize:
    rows = 25
    columns = 80


class _FakeConsole:
    """Stand-in for rich.console.Console used only to sidestep the
    `console.size.rows` production bug (see
    test_tui_update_layout_crashes_on_console_size_rows_bug below) so other
    run()-level behaviors (exit handling, exception propagation) can be
    exercised in isolation."""

    def __init__(self):
        self.size = _FakeConsoleSize()

    def print(self, *args, **kwargs):
        pass


def test_tui_update_layout_crashes_on_console_size_rows_bug():
    """PRODUCTION BUG: rich's Console.size returns a ConsoleDimensions
    namedtuple with fields `width` and `height` -- there is no `.rows`
    attribute. jarvis/tui/tui_app.py's _update_layout() reads
    `self.console.size.rows`, so every single call raises AttributeError.
    Because _update_layout() runs on every iteration of run()'s main loop
    (before the prompt is even shown), the real TUI cannot render at all:
    it crashes immediately after gateway.start(). This test pins that real,
    currently-broken behavior."""
    app = TUIApp(profile="default")
    app._setup_layout()
    app.gateway = MagicMock()
    app.gateway.status.return_value = {
        "running": True,
        "channels": [],
        "sessions": 0,
        "memory": "test.db",
    }

    with pytest.raises(AttributeError, match="rows"):
        app._update_layout()


@pytest.mark.timeout(5)
def test_tui_app_run_exit_command_triggers_clean_shutdown(monkeypatch):
    """Full run()-level shutdown/teardown path: typing /exit breaks the main
    loop cleanly and the `finally` block tears the gateway down.

    Note: app.console is replaced with a stub because of the
    console.size.rows production bug documented above -- this test is about
    the /exit + shutdown control flow, not rendering."""
    app = TUIApp(profile="default")
    app.gateway = MagicMock()
    app.gateway.channel_mgr = MagicMock()
    app.gateway.status.return_value = {
        "running": True,
        "channels": [],
        "sessions": 0,
        "memory": "test.db",
    }
    app.console = _FakeConsole()

    mock_prompt_session = MagicMock()
    mock_prompt_session.prompt.return_value = "/exit"

    monkeypatch.setattr("jarvis.tui.tui_app.PromptSession", lambda *a, **kw: mock_prompt_session)
    monkeypatch.setattr("jarvis.tui.tui_app.FileHistory", lambda *a, **kw: MagicMock())
    monkeypatch.setattr("jarvis.tui.tui_app.Live", _FakeLive)
    monkeypatch.setattr("jarvis.tui.tui_app.patch_stdout", lambda: contextlib.nullcontext())

    app.run()  # should return normally, no exception

    app.gateway.bootstrap.assert_called_once()
    app.gateway.start.assert_called_once()
    app.gateway.stop.assert_called_once()  # invoked via the `finally` -> stop()
    assert app._running is False


@pytest.mark.timeout(5)
def test_tui_app_run_unexpected_exception_propagates_after_cleanup(monkeypatch):
    """The main loop in TUIApp.run() only catches (KeyboardInterrupt,
    EOFError) around session.prompt(). Any other exception is NOT handled at
    that level -- it is left to propagate straight out of run(), even though
    the `finally` block still runs stop() first. This documents that the TUI
    does not "log and continue" or "show an error to the user" for arbitrary
    errors in its input loop: it terminates the process.

    Note: app.console is replaced with a stub because of the
    console.size.rows production bug documented above -- this test targets
    exception propagation from session.prompt(), not rendering."""
    app = TUIApp(profile="default")
    app.gateway = MagicMock()
    app.gateway.channel_mgr = MagicMock()
    app.gateway.status.return_value = {
        "running": True,
        "channels": [],
        "sessions": 0,
        "memory": "test.db",
    }
    app.console = _FakeConsole()

    mock_prompt_session = MagicMock()
    mock_prompt_session.prompt.side_effect = RuntimeError("unexpected failure")

    monkeypatch.setattr("jarvis.tui.tui_app.PromptSession", lambda *a, **kw: mock_prompt_session)
    monkeypatch.setattr("jarvis.tui.tui_app.FileHistory", lambda *a, **kw: MagicMock())
    monkeypatch.setattr("jarvis.tui.tui_app.Live", _FakeLive)
    monkeypatch.setattr("jarvis.tui.tui_app.patch_stdout", lambda: contextlib.nullcontext())

    with pytest.raises(RuntimeError, match="unexpected failure"):
        app.run()

    # Cleanup still ran despite the crash.
    app.gateway.stop.assert_called_once()
    assert app._running is False
