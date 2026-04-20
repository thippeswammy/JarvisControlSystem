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
from Jarvis.core.jarvis_llm import LLMFallbackModule
from Jarvis.core.context_collector import ContextCollector
from Jarvis.core.jarvis_memory import MemoryManager

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

    def __init__(self, feedback_fn=None, ask_user_fn=None, enable_window_tracking: bool = True):
        """
        Args:
            feedback_fn: callable(message: str) for TTS/print output.
                         Defaults to print().
            ask_user_fn: callable(prompt: str) -> str to ask user interactively.
            enable_window_tracking: Whether to auto-track the active window.
        """
        self._intent_engine = IntentEngine()
        self._registry = registry
        self._context_mgr = ContextManager()
        self._llm_fallback = LLMFallbackModule(use_mock=True)  # set use_mock=False + model_id to use real LLM
        self._context_collector = ContextCollector()
        self._memory = MemoryManager()
        self._feedback_fn = feedback_fn or self._default_feedback
        self._ask_user_fn = ask_user_fn or self._default_ask_user

        # Tracks recent successful commands for context history
        self._recent_commands: list[str] = []
        self._pending_confirmation_intent: Optional[Intent] = None
        # Steps tracked during a fallback sequence for memory saving
        self._fallback_steps_taken: list[str] = []
        self._fallback_original_command: str = ""

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

        # ── Guard 0: Pending Confirmation ──
        if self._pending_confirmation_intent:
            response = text.lower().strip()
            if response in ["yes", "y", "yeah", "yep"]:
                self._feedback("Executing confirmed command...")
                result = self._registry.dispatch(self._pending_confirmation_intent, ctx)
                self._pending_confirmation_intent = None
                self._context_mgr.update(self._pending_confirmation_intent, result.success)
                return result
            else:
                self._pending_confirmation_intent = None
                self._feedback("Action cancelled.")
                return ActionResult.ok("Cancelled by user.")

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

        # ── Guard 3: Unknown intent / try normal dispatch ────────────
        is_unknown = (intent.action == ActionType.UNKNOWN)

        if not is_unknown:
            result = self._registry.dispatch(intent, ctx)
            if result.success:
                self._context_mgr.update(intent, result.success)
                self._recent_commands.append(text)
                self._recent_commands = self._recent_commands[-20:]  # keep last 20
                
                # If we were tracking a fallback sequence, add this step
                if self._fallback_original_command:
                    self._fallback_steps_taken.append(text)

                if result.message:
                    self._feedback(result.message)
                return result
            else:
                # If a regular command fails, start tracking a new potential recipe
                self._fallback_original_command = text
                self._fallback_steps_taken = []

        # ── Flow fell through → try Memory recall first ──────────────
        snapshot = self._context_collector.collect(recent_commands=self._recent_commands)

        memory_recipe = self._memory.recall(text, snapshot)
        if memory_recipe:
            logger.info(f"[Memory] Replaying recipe for: '{text}' → {memory_recipe.steps}")
            self._feedback(f"I remember how to do that — replaying {len(memory_recipe.steps)} steps.")
            last_result = ActionResult.ok("Replayed from memory.")
            for step_cmd in memory_recipe.steps:
                step_intent = self._intent_engine.parse(step_cmd, ctx)
                last_result = self._registry.dispatch(step_intent, ctx)
                self._context_mgr.update(step_intent, last_result.success)
                import time; time.sleep(0.8)  # small pause between replayed steps
            self._memory.save(text, memory_recipe.steps, snapshot)  # increment success count
            return last_result

        # ── Memory miss → LLM Fallback ───────────────────────────────
        memory_context = self._memory.get_relevant_context(text, snapshot)
        corrected_intent, user_prompt = self._llm_fallback.analyze(
            raw_input=text,
            failed_action=intent.action if not is_unknown else None,
            snapshot=snapshot,
            memory_context=memory_context,
        )

        if corrected_intent:
            if corrected_intent.action == ActionType.LEARN:
                # User says "remember that as X"
                goal = corrected_intent.target or self._fallback_original_command
                if not self._fallback_steps_taken:
                    self._feedback("I don't have any recent steps to remember.")
                    return ActionResult.fail("No steps to learn.")
                
                # Use the snapshot from the START of the sequence if possible, 
                # but for now we use current snapshot.
                self._memory.save(goal, self._fallback_steps_taken, snapshot)
                self._feedback(f"I've learned '{goal}' — it now takes {len(self._fallback_steps_taken)} steps.")
                self._fallback_original_command = ""
                self._fallback_steps_taken = []
                return ActionResult.ok(f"Learned recipe for {goal}.")

            self._feedback(f"LLM corrected: '{corrected_intent.target}'")
            result = self._registry.dispatch(corrected_intent, ctx)
            self._context_mgr.update(corrected_intent, result.success)
            if result.success:
                # Save to memory so next time we skip the LLM entirely
                self._memory.save(
                    command=text,
                    steps=[corrected_intent.raw or text],  # single-step correction
                    snapshot=snapshot,
                )
            if result.message:
                self._feedback(result.message)
            return result

        elif user_prompt:
            self._feedback(user_prompt)
            return ActionResult.fail("Awaiting clarification.")

        msg = f"I didn't understand: '{text}'"
        self._feedback(msg)
        return ActionResult.fail(msg)

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
        
    @staticmethod
    def _default_ask_user(prompt: str) -> str:
        return input(f"[Jarvis] {prompt} [Y/N]: ")

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
