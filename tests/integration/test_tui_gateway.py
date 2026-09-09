import pytest
import time
from unittest.mock import MagicMock, patch
from jarvis.gateway.gateway import GatewayDaemon
from jarvis.input.adapters import TUIAdapter
from jarvis.llm.llm_interface import LLMDecision


def _poll_tui_output(adapter, timeout=0.5):
    """Non-blocking-ish single poll of the TUI output queue. Returns None on empty."""
    try:
        return adapter.get_output_queue().get(timeout=timeout)
    except Exception:
        return None


def _mock_llm_boundary(gateway, reply_text):
    """
    Mock every LLMRouter entry point reachable from Orchestrator.process() so
    a test never makes a real network call to a local LLM backend.
    NLU / GoalUnderstandingLayer call call_raw_for_task() and gracefully
    fall back on a falsy result; ClosedLoopEngine._think() tries
    decide_closed_loop_for_task() first and — per its own test-mode
    fallback — calls decide() directly once it sees decide() is a Mock.
    """
    gateway.router.call_raw_for_task = MagicMock(return_value=None)
    gateway.router.decide_closed_loop_for_task = MagicMock(
        side_effect=RuntimeError("no closed-loop backend in test")
    )
    gateway.router.decide = MagicMock(return_value=LLMDecision(
        type="chat", message=reply_text, steps=[]
    ))

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


def test_tui_gateway_empty_input_does_not_crash():
    """
    Unlike CLIAdapter.stream() (which explicitly does `if not text: continue`),
    TUIAdapter.stream() yields an Utterance for ANY queued string, including
    an empty one — there is no empty-text guard. Verify that an empty message
    flows all the way through Orchestrator.process() without crashing the
    channel, and that the channel is still usable afterwards.
    """
    gateway = GatewayDaemon()
    gateway.bootstrap()
    _mock_llm_boundary(gateway, "(empty input handled)")

    adapter = TUIAdapter()
    gateway.channel_mgr.add_channel(adapter)

    try:
        gateway.start()
        time.sleep(1)

        adapter.simulate_input("")

        # GoalUnderstandingLayer short-circuits empty text without calling the
        # router, but the ClosedLoopEngine's "Starting..." + "Goal Complete"
        # messages still both go out — poll deterministically for both.
        replies = []
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline and len(replies) < 2:
            msg = _poll_tui_output(adapter, timeout=0.5)
            if msg is not None:
                replies.append(msg)

        assert len(replies) >= 2, f"Empty input did not produce the expected reply flow: {replies}"
        assert any("(empty input handled)" in r for r in replies), replies

        thread = gateway.channel_mgr._threads.get("tui")
        assert thread is not None and thread.is_alive(), "TUI channel died after empty input"

    finally:
        gateway.stop()


def test_tui_gateway_processing_error_recovers_on_next_message():
    """
    Failure path: force an exception synchronously inside
    Orchestrator.process() (context capture, which runs before NLU/LLM and
    before the async background worker is dispatched). ChannelManager's
    per-message try/except (see _run_channel_loop) must catch it, send a
    friendly error back over the SAME channel, and keep the channel thread
    alive so the next message is processed normally.
    """
    gateway = GatewayDaemon()
    gateway.bootstrap()
    _mock_llm_boundary(gateway, "recovered")

    adapter = TUIAdapter()
    gateway.channel_mgr.add_channel(adapter)

    try:
        gateway.start()
        time.sleep(1)

        with patch(
            "jarvis.perception.context_harvester.ContextHarvester.capture",
            side_effect=RuntimeError("simulated context capture failure"),
        ):
            adapter.simulate_input("test message")

            error_reply = None
            deadline = time.monotonic() + 10.0
            while time.monotonic() < deadline and error_reply is None:
                error_reply = _poll_tui_output(adapter, timeout=0.5)

            assert error_reply is not None, "No error reply received after a processing failure"
            assert "sorry" in error_reply.lower() or "error" in error_reply.lower(), error_reply

        thread = gateway.channel_mgr._threads.get("tui")
        assert thread is not None and thread.is_alive(), "TUI channel died after a processing error"

        # The patch is lifted — the channel must process a normal message again.
        adapter.simulate_input("test message")
        replies = []
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline and len(replies) < 2:
            msg = _poll_tui_output(adapter, timeout=0.5)
            if msg is not None:
                replies.append(msg)

        assert len(replies) >= 2, f"TUI channel did not recover after the processing error: {replies}"
        assert any("recovered" in r for r in replies), replies

    finally:
        gateway.stop()
