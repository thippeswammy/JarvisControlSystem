"""
Jarvis Engine
=============
Main orchestrator — replaces CommandProcessor.py.

Pipeline:
    process(text)
      1. Guard: Jarvis not active + not an activation phrase → reject
      2. Typing mode guard: if in typing mode, send ALL text to keyboard
      3. IntentEngine.parse(text, context) → Intent
      4. ActionRegistry.dispatch(intent, context) → ActionResult
      5. ContextManager.update(intent, success)
      6. FeedbackSystem.speak(result.message)

All command handlers are registered via @registry.register() in
the handlers sub-modules. JarvisEngine imports them to trigger registration.
"""

import logging
import os
from typing import Optional

from Jarvis.core.intent_engine import IntentEngine, Intent, ActionType
from Jarvis.core.action_registry import ActionRegistry, ActionResult, registry
from Jarvis.core.context_manager import ContextManager, Context

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  Jarvis Engine
# ─────────────────────────────────────────────
class JarvisEngine:
    """
    The single entry point for all Jarvis commands.

    Usage:
        engine = JarvisEngine()
        engine.process("hi jarvis")
        engine.process("open chrome")
        engine.process("set volume to 80")
    """

    def __init__(self, feedback_fn=None, enable_window_tracking: bool = True):
        """
        Args:
            feedback_fn: callable(message: str) for TTS/print output.
                         Defaults to print().
            enable_window_tracking: Whether to auto-track the active window.
        """
        self._intent_engine = IntentEngine()
        self._registry = registry
        self._context_mgr = ContextManager()
        self._feedback_fn = feedback_fn or self._default_feedback

        # Register all built-in handlers
        self._register_handlers()

        # Start window tracking
        if enable_window_tracking:
            self._context_mgr.start()

        logger.info("JarvisEngine initialized.")

    # ── Main entry point ────────────────────────
    def process(self, text: str) -> ActionResult:
        """
        Process a user command (text input).
        Returns an ActionResult indicating success/failure.
        """
        if not text or not text.strip():
            return ActionResult.fail("Empty input.")

        ctx = self._context_mgr.context

        # ── Guard 1: Typing mode — pass all text directly to keyboard ──
        if ctx.is_typing_mode and ctx.is_active:
            # Only allow "stop typing" to exit typing mode
            text_lower = text.lower().strip()
            stop_phrases = ["stop typing", "typing stop", "deactivate typing",
                           "typing deactivate", "end typing", "disable typing"]
            if text_lower not in stop_phrases:
                from Jarvis.KeyboardAutomationController import type_text
                type_text(text, addr="JarvisEngine.typing_mode ->")
                self._feedback(f"Typed: {text}")
                return ActionResult.ok(f"Typed: {text}")

        # ── Parse intent ────────────────────────
        intent = self._intent_engine.parse(text, ctx)
        logger.debug(f"Parsed: {intent}")

        # ── Guard 2: Jarvis not active (except for activation commands) ──
        if not ctx.is_active and intent.action != ActionType.ACTIVATE_JARVIS:
            msg = "Say 'Hi Jarvis' to activate."
            logger.info(f"Not active, rejected: {text!r}")
            self._feedback(msg)
            return ActionResult.fail(msg)

        # ── Guard 3: Unknown intent ─────────────
        if intent.action == ActionType.UNKNOWN:
            msg = f"I didn't understand: '{text}'"
            self._feedback(msg)
            return ActionResult.fail(msg)

        # ── Dispatch to handler ─────────────────
        result = self._registry.dispatch(intent, ctx)

        # ── Update context ──────────────────────
        self._context_mgr.update(intent, result.success)

        # ── Feedback ─────────────────────────────
        if result.message:
            self._feedback(result.message)

        return result

    # ── Convenience properties ──────────────────
    @property
    def context(self) -> Context:
        return self._context_mgr.context

    @property
    def is_active(self) -> bool:
        return self._context_mgr.context.is_active

    def shutdown(self):
        """Clean up background threads."""
        self._context_mgr.stop()
        logger.info("JarvisEngine shut down.")

    # ── Private ─────────────────────────────────
    def _feedback(self, message: str):
        if message:
            self._feedback_fn(message)

    @staticmethod
    def _default_feedback(message: str):
        print(f"[Jarvis] {message}")

    def _register_handlers(self):
        """
        Import all handler modules so their @registry.register() decorators run.
        This is the ONLY place you add a new handler module.
        """
        import importlib
        handler_modules = [
            "Jarvis.core.handlers.session_handler",
            "Jarvis.core.handlers.app_handler",
            "Jarvis.core.handlers.system_handler",
            "Jarvis.core.handlers.keyboard_handler",
            "Jarvis.core.handlers.window_handler",
            "Jarvis.core.handlers.settings_handler",
            "Jarvis.core.handlers.navigator_handler",
            "Jarvis.core.handlers.search_handler",
        ]
        for module_path in handler_modules:
            try:
                importlib.import_module(module_path)
                logger.debug(f"Loaded handler module: {module_path}")
            except ImportError as e:
                logger.warning(f"Could not load handler {module_path}: {e}")


# ─────────────────────────────────────────────
#  Quick smoke test
# ─────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    engine = JarvisEngine(enable_window_tracking=False)

    test_commands = [
        "hi jarvis",
        "set brightness to 100",
        "increase volume by 40",
        "open notepad",
        "press enter",
        "start typing",
        "hello world",          # Should be typed
        "stop typing",
        "minimize window",
        "close jarvis",
    ]

    for cmd in test_commands:
        print(f"\n>>> {cmd}")
        result = engine.process(cmd)
        print(f"    Result: {'OK' if result else 'FAIL'} — {result.message}")

    engine.shutdown()
