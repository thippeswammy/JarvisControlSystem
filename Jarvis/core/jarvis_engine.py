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
from Jarvis.navigator.app_navigator import AppNavigator
from Jarvis.core.ui_spider import UISpider

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
        self._navigator = AppNavigator()
        self._ui_spider = UISpider(memory_manager=self._memory, navigator=self._navigator)
        self._feedback_fn = feedback_fn or self._default_feedback
        self._ask_user_fn = ask_user_fn or self._default_ask_user

        # Tracks recent successful commands for context history
        self._recent_commands: list[str] = []
        self._pending_confirmation_intent: Optional[Intent] = None
        # Steps tracked during a fallback sequence for memory saving
        self._fallback_steps_taken: list[str] = []
        self._fallback_original_command: str = ""
        self._fallback_snapshot: Optional[ContextSnapshot] = None

        # Register all built-in handlers
        self._register_handlers()

        # Start tracking and spidering
        if enable_window_tracking:
            self._context_mgr.start()
            self._ui_spider.start()

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

        # ── Guard 3: Intercept Learn Action ─────────────
        if not (intent.action == ActionType.UNKNOWN):
            if intent.action == ActionType.LEARN:
                return self._handle_learn_action(intent, text)
                
        # ── Guard 4: Memory Recall Intercept ────────────
        # Before falling back to potentially slow hardcoded handlers (like Windows Search),
        # check if we've learned a faster cached path, sequence, or typo-fix in Memory!
        snapshot = self._context_collector.collect(recent_commands=self._recent_commands)
        memory_recipe = self._memory.recall(text, snapshot)
        
        if memory_recipe:
            logger.info(f"[Memory] Replaying recipe for: '{text}' → {memory_recipe.steps}")
            self._feedback(f"I remember how to do that — replaying {len(memory_recipe.steps)} steps.")
            last_result = ActionResult.ok("Replayed from memory.")
            for i, step_cmd in enumerate(memory_recipe.steps):
                logger.info(f"[Memory] Replaying step {i+1}: {step_cmd}")
                step_intent = self._intent_engine.parse(step_cmd, ctx)
                last_result = self._registry.dispatch(step_intent, ctx)
                self._context_mgr.update(step_intent, last_result.success)
                if not last_result.success:
                    logger.warning(f"[Memory] Step {i+1} failed: {last_result.message}")
                    break
                import time; time.sleep(0.4) 
            
            # Message summarizing replay
            replay_msg = f"Replayed {len(memory_recipe.steps)} steps successfully."
            if not last_result.success:
                replay_msg = f"Replay stopped at step {len(memory_recipe.steps)}: {last_result.message}"
            
            self._feedback(replay_msg)
            self._memory.save(text, memory_recipe.steps, snapshot)
            self._recent_commands.append(text)
            self._recent_commands = self._recent_commands[-20:]

            # If we were tracking a fallback sequence, add this replayed command to the buffer
            if self._fallback_original_command:
                self._fallback_steps_taken.append(text)

            return last_result

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
                    
                # ── Generic Reactive Learning ──────────────────────────────
                # Every successful action is a learning opportunity.
                # No special-casing needed — _reactive_learn() handles all intent types.
                self._reactive_learn(intent, text, snapshot)

                return result
            else:
                # If a regular command fails, start tracking a new potential recipe
                self._fallback_original_command = text
                self._fallback_steps_taken = []
                self._fallback_snapshot = snapshot

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
                return self._handle_learn_action(corrected_intent, text)

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
            else:
                # The LLM correction failed too, start tracking manual steps
                self._fallback_original_command = text
                self._fallback_steps_taken = []
                self._fallback_snapshot = snapshot
                
            if result.message:
                self._feedback(result.message)
            return result

        elif user_prompt:
            self._fallback_original_command = text
            self._fallback_steps_taken = []
            self._fallback_snapshot = snapshot
            self._feedback(user_prompt)
            return ActionResult.fail("Awaiting clarification.")

        msg = f"I didn't understand: '{text}'"
        self._fallback_original_command = text
        self._fallback_steps_taken = []
        self._fallback_snapshot = snapshot
        self._feedback(msg)
        return ActionResult.fail(msg)

    def _handle_learn_action(self, intent: Intent, raw_text: str) -> ActionResult:
        """Logic for recording a sequence of steps into memory."""
        goal = intent.target or self._fallback_original_command
        
        steps_to_learn = self._fallback_steps_taken
        if not steps_to_learn and goal:
            # If tracking was swallowed by a false success (like Windows search), 
            # retroactively extract the sequence from recent commands.
            try:
                safe_goal = goal.lower()
                # Find the LAST occurrence of the goal in the history
                idx = -1
                for i, cmd in enumerate(self._recent_commands):
                    if cmd.lower() == safe_goal:
                        idx = i
                
                if idx != -1:
                    steps_to_learn = self._recent_commands[idx+1:]
            except Exception:
                pass

        if not steps_to_learn:
            self._feedback("I don't have any recent steps to remember.")
            return ActionResult.fail("No steps to learn.")
        
        # Capture snapshot from when the sequence started if available,
        # otherwise capture current snapshot.
        snapshot = self._fallback_snapshot
        if snapshot is None:
            snapshot = self._context_collector.collect(recent_commands=self._recent_commands)
        
        # Save to memory (category is dynamic from LLM if available)
        self._memory.save(
            command=goal,
            steps=steps_to_learn,
            snapshot=snapshot,
            category=intent.category
        )
        
        self._feedback(f"I've learned '{goal}' — it now takes {len(steps_to_learn)} steps.")
        
        # Reset tracking
        self._fallback_original_command = ""
        self._fallback_steps_taken = []
        self._fallback_snapshot = None
        
        return ActionResult.ok(f"Learned recipe for {goal}.")

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
        if hasattr(self, '_ui_spider'):
            self._ui_spider.stop()
        logger.info("JarvisEngine shut down.")

    # ── Private ─────────────────────────────────

    # Intent types that open a new app/process — triggers path learning
    _OPEN_INTENT_TYPES = {
        ActionType.OPEN_APP,
        ActionType.OPEN_SETTINGS,
    }

    # Intent types that represent multi-step navigation — triggers sequence learning
    _NAV_INTENT_TYPES = {
        ActionType.CLICK_ELEMENT,
        ActionType.NAVIGATE_LOCATION,
    }

    def _reactive_learn(self, intent: "Intent", raw_text: str, snapshot) -> None:
        """
        Generic reactive learning hook called after EVERY successful action.

        Rules (no special-casing):
        - Open-type intents  → background thread resolves & saves the real exe/URI.
        - Nav-type intents   → save the recent command sequence as a navigation recipe.
        - Any other intent   → save a single-step recipe so the LLM can recall it later.

        The category is derived automatically from the intent type — no hardcoding.
        """
        action = intent.action
        target = intent.target or ""

        if action in self._OPEN_INTENT_TYPES:
            # For any app-opening event, resolve the actual launch path in the background.
            # The worker is completely generic — it detects exe vs UWP automatically.
            self._learn_app_path_async(target)
            return

        if action in self._NAV_INTENT_TYPES and snapshot.current_location:
            # Record the navigation sequence that led to this click/navigate.
            goal = target if target.lower().startswith("open") else f"open {target}"
            steps = self._recent_commands[-5:] + [raw_text]
            self._memory.save(
                command=goal,
                steps=steps,
                snapshot=snapshot,
                category="navigation",
            )
            logger.info(f"[ReactiveLearn] Nav sequence saved for '{goal}'")
            return

        # All other action types: save a minimal single-step recipe.
        # This builds an ever-growing vocabulary the LLM can recall for novel commands.
        _ATOMIC_ACTIONS = {
            ActionType.PRESS_KEY, ActionType.HOLD_KEY, ActionType.RELEASE_KEY,
            ActionType.TYPE_TEXT, ActionType.TYPE_IN_FIELD, ActionType.SET_VALUE,
            ActionType.INCREASE, ActionType.DECREASE
        }

        if target and action not in _ATOMIC_ACTIONS:
            category = self._intent_to_category(action)
            self._memory.save(
                command=raw_text,
                steps=[raw_text],
                snapshot=snapshot,
                category=category,
            )
            logger.debug(f"[ReactiveLearn] Single-step recipe saved: '{raw_text}' → {category}")

    @staticmethod
    def _intent_to_category(action: "ActionType") -> str:
        """Map an ActionType to a memory category without any hardcoding."""
        _MAP = {
            ActionType.OPEN_APP:           "apps",
            ActionType.OPEN_SETTINGS:      "settings",
            ActionType.NAVIGATE_LOCATION:  "navigation",
            ActionType.CLICK_ELEMENT:      "navigation",
            ActionType.SEARCH:             "navigation",
            ActionType.PRESS_KEY:          "shortcuts",
            ActionType.TYPE_TEXT:          "shortcuts",
            ActionType.SET_VALUE:          "system",
            ActionType.INCREASE:           "system",
            ActionType.DECREASE:           "system",
            ActionType.MINIMIZE:           "system",
            ActionType.MAXIMIZE:           "system",
            ActionType.CLOSE_APP:          "apps",
        }
        return _MAP.get(action, "navigation")

    def _learn_app_path_async(self, target_name: str) -> None:
        """
        Reactively learn the launch path of any app that just opened.

        Fully generic — no special-casing for any particular app:
        - Regular Win32 exe  → stores the absolute exe path.
        - UWP / Store apps   → tries to get the AppUserModelID (AUMID) via shell;
                               falls back to the process executable name.
        The resulting recipe uses `execute_process <path/AUMID>` as its single step,
        which the app_handler already knows how to execute.
        """
        import threading
        def worker():
            import time
            time.sleep(2)  # Give the app time to appear in the foreground
            try:
                import psutil
                import win32gui
                import win32process

                hwnd = win32gui.GetForegroundWindow()
                if not hwnd:
                    return

                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                proc = psutil.Process(pid)
                exe_path = proc.exe()

                # Skip shell/explorer — not a real app process
                if not exe_path or "explorer.exe" in exe_path.lower():
                    return

                # Detect UWP / ApplicationFrameHost-hosted apps generically.
                # These cannot be re-launched by exe path; we need the AUMID or shell URI.
                _UWP_HOSTS = {"applicationframehost.exe", "wwahost.exe", "systemsettings.exe"}
                exe_name = os.path.basename(exe_path).lower()
                is_uwp = exe_name in _UWP_HOSTS or "windowsapps" in exe_path.lower()

                if is_uwp:
                    launch_key = self._get_uwp_launch_key(hwnd, proc, target_name)
                else:
                    launch_key = exe_path

                if launch_key:
                    self._memory.batch_save_apps({target_name: launch_key})
                    logger.info(f"[ReactiveLearn] Saved app path: '{target_name}' → '{launch_key}'")
                    self._feedback(f"Learned how to open '{target_name}'")

            except Exception as e:
                logger.debug(f"[ReactiveLearn] Could not resolve path for '{target_name}': {e}")

        threading.Thread(target=worker, daemon=True).start()

    @staticmethod
    def _get_uwp_launch_key(hwnd: int, proc, target_name: str) -> Optional[str]:
        """
        For UWP / store apps, attempt to retrieve the AppUserModelID (AUMID).
        The AUMID is the unique identifier Windows uses to launch packaged apps
        (e.g. 'windows.immersivecontrolpanel_...' for Settings).

        Falls back gracefully:
          1. Try IPropertyStore / PKEY_AppUserModel_ID via pywin32
          2. Try querying the running package via psutil cmdline
          3. Last resort: use the process name as the identifier if not a known generic host
        """
        try:
            import win32com.shell.shell as shell
            import win32com.shell.shellcon as shellcon
            import pywintypes
            # Get the IPropertyStore for the window
            store = shell.SHGetPropertyStoreForWindow(hwnd, shell.IID_IPropertyStore)
            # PKEY_AppUserModel_ID = {9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3}, 5
            PKEY_AUMID = pywintypes.IID("{9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3}")
            aumid = store.GetValue((PKEY_AUMID, 5))
            if aumid:
                return f"shell:appsfolder\\{str(aumid)}"
        except Exception:
            pass  # pywin32 shell API not available or window doesn't expose AUMID

        # Last resort: return None since target_name might not be an executable
        return None

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
            "Jarvis.core.handlers.crawler_handler",
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
