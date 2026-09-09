import pytest
import time
import os
import sys
from unittest.mock import MagicMock

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from jarvis.gateway.gateway import GatewayDaemon
from jarvis.input.adapters import MockTelegramAdapter
from jarvis.llm.llm_interface import LLMDecision

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


def test_gateway_channel_stream_crash_does_not_kill_gateway():
    """
    A fatal exception raised directly out of an adapter's stream() simulates a
    channel/transport-level crash (e.g. a Telegram polling failure). Per
    ChannelManager._run_channel_loop, this is only caught by the OUTER
    try/except (the per-message guard cannot help since the crash happens in
    the `for utterance in adapter.stream():` line itself) — the channel's own
    thread should exit and be reported as "stopped", but that must not affect
    other channels or the gateway process as a whole.
    """
    gateway = GatewayDaemon()
    gateway.bootstrap()

    class CrashingTelegramAdapter(MockTelegramAdapter):
        name = "telegram-crash"

        def stream(self):
            raise RuntimeError("simulated adapter/channel crash")

    healthy_adapter = MockTelegramAdapter()
    crashing_adapter = CrashingTelegramAdapter()
    gateway.channel_mgr._channels = {
        "telegram-test": healthy_adapter,
        "telegram-crash": crashing_adapter,
    }

    try:
        gateway.start()

        # Deterministic wait: poll for the crashing channel's thread to exit
        # instead of a blind sleep.
        crash_thread = None
        for _ in range(50):
            crash_thread = gateway.channel_mgr._threads.get("telegram-crash")
            if crash_thread is not None and not crash_thread.is_alive():
                break
            time.sleep(0.1)

        assert crash_thread is not None, "Crashing channel's thread was never started"
        assert not crash_thread.is_alive(), (
            "Channel thread should exit once adapter.stream() raises a fatal error"
        )

        statuses = {c["name"]: c["status"] for c in gateway.channel_mgr.list_channels()}
        assert statuses["telegram-crash"] == "stopped"
        assert statuses["telegram-test"] == "running"

        # The gateway itself, and the sibling channel, must still be fully
        # operational after the crash.
        assert gateway.status()["running"] is True

        healthy_adapter.simulate_message("/status")
        reply_received = False
        for _ in range(20):
            if healthy_adapter.get_replies():
                reply_received = True
                break
            time.sleep(0.5)
        assert reply_received, "Healthy channel stopped responding after the sibling channel crashed"

    finally:
        gateway.stop()


def test_gateway_garbage_message_does_not_crash_channel():
    """
    Control-character / binary-ish / oversized garbage input must not crash
    the channel loop. The LLM boundary is fully mocked (LLMRouter.decide,
    decide_closed_loop_for_task, call_raw_for_task) so this exercises real
    NLU/goal-understanding/closed-loop string handling of the garbage text
    without ever touching a real local LLM backend.
    """
    gateway = GatewayDaemon()
    gateway.bootstrap()

    # NLU and GoalUnderstandingLayer both call call_raw_for_task() and treat a
    # falsy/None result as "couldn't classify" (they fall back gracefully).
    gateway.router.call_raw_for_task = MagicMock(return_value=None)
    # ClosedLoopEngine._think() tries decide_closed_loop_for_task() first; on
    # failure it falls back to calling decide() directly when decide is a Mock
    # (this is an intentional test-mode fallback baked into the engine).
    gateway.router.decide_closed_loop_for_task = MagicMock(
        side_effect=RuntimeError("no closed-loop backend in test")
    )
    gateway.router.decide = MagicMock(return_value=LLMDecision(
        type="chat", message="Handled the garbage input fine.", steps=[]
    ))

    mock_adapter = MockTelegramAdapter()
    gateway.channel_mgr._channels = {"telegram-test": mock_adapter}

    garbage = "\x00\x01\x1b[31m'; DROP TABLE users; --﻿" + ("\U0001F4A5" * 200)

    try:
        gateway.start()
        time.sleep(1)  # Let thread spin up (matches existing tests in this file)

        mock_adapter.simulate_message(garbage)

        replies = []
        for _ in range(30):
            replies = mock_adapter.get_replies()
            if len(replies) >= 2:
                break
            time.sleep(0.3)

        assert len(replies) >= 2, f"Garbage input broke the reply flow. Got: {replies}"
        assert any("Handled the garbage input fine." in r["text"] for r in replies), replies

        # Channel must still be alive/functional after processing the garbage input.
        thread = gateway.channel_mgr._threads.get("telegram-test")
        assert thread is not None and thread.is_alive()

    finally:
        gateway.stop()


def test_gateway_llm_timeout_does_not_hang_channel():
    """
    If every LLM router entry point times out (e.g. Ollama is up but the
    model is wedged, or a configured cloud backend never responds), the
    gateway must degrade to a bounded "stuck / recovery" message instead of
    hanging on the request. This mocks the router boundary with a
    TimeoutError side_effect (mock_router-style) rather than making a real
    network call — an un-mocked call against a down local backend is known to
    hang for 60s+.
    """
    gateway = GatewayDaemon()
    gateway.bootstrap()

    timeout_error = TimeoutError("Simulated LLM backend timeout")
    gateway.router.call_raw_for_task = MagicMock(side_effect=timeout_error)
    gateway.router.decide = MagicMock(side_effect=timeout_error)
    gateway.router.decide_for_task = MagicMock(side_effect=timeout_error)
    gateway.router.decide_closed_loop = MagicMock(side_effect=timeout_error)
    gateway.router.decide_closed_loop_for_task = MagicMock(side_effect=timeout_error)
    gateway.router.route = MagicMock(side_effect=timeout_error)
    gateway.router.route_for_task = MagicMock(side_effect=timeout_error)

    mock_adapter = MockTelegramAdapter()
    gateway.channel_mgr._channels = {"telegram-test": mock_adapter}

    try:
        gateway.start()
        time.sleep(1)

        start = time.monotonic()
        mock_adapter.simulate_message("do something complicated across multiple apps")

        # Deterministic bounded poll (short interval, hard 15s ceiling) —
        # a real un-mocked hang would blow well past this before the 60s+
        # an actually-down local backend would take.
        replies = []
        deadline = start + 15.0
        while time.monotonic() < deadline:
            replies = mock_adapter.get_replies()
            if len(replies) >= 2:
                break
            time.sleep(0.2)
        elapsed = time.monotonic() - start

        assert len(replies) >= 2, (
            f"Simulated LLM timeout left the request hanging — only got {replies} "
            f"after {elapsed:.1f}s (bounded wait was 15s)."
        )
        assert elapsed < 15.0

        final_text = "\n".join(r["text"] for r in replies).lower()
        # decide()/decide_closed_loop_for_task() both raising drives the
        # ClosedLoopEngine to a "blocked" decision, which RecoveryEngine
        # turns into a generic recovery/chat_reply message (see
        # RecoveryEngine.diagnose_and_heal's "Default fallback").
        assert "recovery" in final_text or "unexpected error" in final_text, replies

        thread = gateway.channel_mgr._threads.get("telegram-test")
        assert thread is not None and thread.is_alive(), "Channel thread should survive an LLM timeout"

    finally:
        gateway.stop()
