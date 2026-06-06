"""
Verification Loop (Phase 6)
===========================
Wraps every SkillCall execution with before/after UIState comparison.

Execute → Verify → Learn (or recover):
    1. Capture state BEFORE  (StateHarvester)
    2. Execute SkillCall     (SkillBus)
    3. Wait settle_ms
    4. Capture state AFTER   (StateHarvester)
    5. Compare hashes
        a. Hash changed  → success → ReactiveLearner.learn()
        b. Hash same     → state unchanged
              → retry / alternative / ask_user (RecoveryStrategies)
        c. No expected state → trust skill result (pass-through)

Skills that don't change UI state (e.g. type_text, search_web)
are excluded from verification via SKIP_VERIFY_SKILLS set.
"""

import logging
import os
import time
from typing import Optional

from jarvis.brain.reactive_learner import ReactiveLearner
from jarvis.brain.recovery import RecoveryStrategies
from jarvis.memory.state_harvester import StateHarvester
from jarvis.memory.state_comparator import StateComparator
from jarvis.perception.perception_packet import PerceptionPacket, ContextSnapshot
from jarvis.skills.skill_bus import SkillBus, SkillCall, SkillResult

logger = logging.getLogger(__name__)

# Skills that don't produce a verifiable UI state change
SKIP_VERIFY_SKILLS = {
    "type_text", "press_key", "search_web", "search_windows",
    "session_activate", "session_deactivate", "system_status",
    "ask_user", "set_volume", "set_brightness", "power_action",
    "scroll_page", "chat_reply",
    # Add new read-only / non-mutating skills
    "get_active_window_title", "verify_element_exists", "extract_browser_dom_tree",
    "log_analysis", "greet_user"
}

_DEFAULT_SETTLE_MS = 600   # ms to wait after action before re-harvesting


class VerificationLoop:
    """
    Wraps SkillBus dispatch with UIState before/after comparison.

    Wiring:
        vloop = VerificationLoop(harvester, comparator, recovery)
        orchestrator.set_verification_loop(vloop)

    The orchestrator then calls:
        vloop.execute_and_verify(call, bus, packet, snapshot, learner)
    """

    def __init__(self, harvester: StateHarvester, comparator: StateComparator, recovery: RecoveryStrategies, settle_ms: int = _DEFAULT_SETTLE_MS):
        self._harvester = harvester
        self._comparator = comparator
        self._recovery = recovery
        self._settle_ms = settle_ms

    def execute_and_verify(
        self,
        call: SkillCall,
        bus: SkillBus,
        packet: PerceptionPacket,
        snapshot: ContextSnapshot,
        learner: ReactiveLearner,
        pathfinder=None,
    ) -> SkillResult:
        """
        Execute call → verify state change → learn or recover.
        """
        # Pass-through for non-verifiable skills
        if call.skill in SKIP_VERIFY_SKILLS:
            return bus.dispatch(call)

        # 0. Let UI settle from previous commands
        time.sleep(0.3)

        # 1. Capture BEFORE state
        # Use foreground window (app_title=None) to ensure we get real UI state
        before_state, before_hash = self._harvester.harvest_and_hash(app_title=None)

        # Custom explicit verification logic
        if call.skill == "open_app":
            target = call.params.get("target", "")
            result = bus.dispatch(call)
            if not before_hash:
                logger.debug("[VerificationLoop] No UI state (UIA unavailable), trusting open_app result")
                return result
            time.sleep(1.0) # Settle for app launch
            if result.success and (self.verify_window_exists(target) or self.verify_focus(target)):
                logger.info(f"[VerificationLoop] [OK] open_app verified successfully: {target}")
                result.action_taken = f"[Verified] {result.action_taken}"
                return result
            else:
                logger.warning(f"[VerificationLoop] [FAIL] open_app failed verification: {target}")
                result.success = False
                return result

        elif call.skill == "close_app":
            target = call.params.get("target", "")
            result = bus.dispatch(call)
            if not before_hash:
                logger.debug("[VerificationLoop] No UI state (UIA unavailable), trusting close_app result")
                return result
            time.sleep(0.8) # Settle for app close
            if result.success and not self.verify_window_exists(target):
                logger.info(f"[VerificationLoop] [OK] close_app verified successfully: {target}")
                result.action_taken = f"[Verified] {result.action_taken}"
                return result
            else:
                logger.warning(f"[VerificationLoop] [FAIL] close_app failed verification: {target}")
                result.success = False
                return result


        for attempt in range(0, 3):
            if attempt > 0:
                result = self._recovery.retry(call, attempt)
            else:
                result = bus.dispatch(call)

            if not result or not result.success:
                if attempt == 0:
                    logger.info(f"[VerificationLoop] Skill failed pre-verification: {call.skill}")
                continue # Try next attempt

            # 3. Wait for UI to settle (use skill-specific or default)
            skill_settle = bus.get_settle_ms(call.skill)
            wait_ms = max(self._settle_ms, skill_settle)
            if wait_ms > 0:
                time.sleep(wait_ms / 1000.0)

            # 4. Capture AFTER state
            after_state, after_hash = self._harvester.harvest_and_hash(app_title=None)

            # Custom navigation check fallback
            if call.skill == "navigate_location":
                target = call.params.get("target", "")
                if self.verify_navigation(target):
                    logger.info(f"[VerificationLoop] [OK] navigate_location verified successfully: {target}")
                    self._maybe_learn(call, packet, learner, success=True)
                    result.action_taken = f"[Verified] {result.action_taken}"
                    return result

            # 5. Compare
            if not before_hash and not after_hash:
                logger.debug("[VerificationLoop] No UI state (UIA unavailable), trusting skill result")
                self._maybe_learn(call, packet, learner, success=True)
                return result

            state_changed = before_hash != after_hash

            if state_changed:
                # [OK] State changed — verified success
                logger.info(f"[VerificationLoop] [OK] State changed: {call.skill} ({before_hash} -> {after_hash})")
                self._maybe_learn(call, packet, learner, success=True)
                result.action_taken = f"[Verified] {result.action_taken}"
                return result

            # [FAIL] No state change — unexpected
            logger.warning(f"[VerificationLoop] [FAIL] No state change after: {call.skill} (Hash: {before_hash})")

        # If we exhausted retries and still no state change, try alternative/ask user
        return self._handle_failure_post_retry(call, bus, packet, snapshot, pathfinder)

    # ── Explicit Verification Helpers ────────────────

    def verify_window_exists(self, app_id: str) -> bool:
        if os.environ.get("JARVIS_ALLOW_MOCK") == "true":
            return False
        try:
            from pywinauto import Desktop
            windows = Desktop(backend="uia").windows()
            app_id_lower = app_id.lower()
            for win in windows:
                title = win.window_text().lower()
                if app_id_lower in title or (app_id_lower == "settings" and "systemsettings" in title):
                    return True
            return False
        except Exception:
            return False

    def verify_focus(self, app_id: str) -> bool:
        if os.environ.get("JARVIS_ALLOW_MOCK") == "true":
            return False
        try:
            import win32gui
            from jarvis.perception.context_harvester import ContextHarvester
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd)
            inferred = ContextHarvester._infer_app_id(title)
            return inferred.lower() == app_id.lower()
        except Exception:
            return False

    def verify_navigation(self, target_label: str) -> bool:
        if os.environ.get("JARVIS_ALLOW_MOCK") == "true":
            return False
        try:
            import win32gui
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd).lower()
            return target_label.lower() in title
        except Exception:
            return False

    # ── Private ──────────────────────────────────────

    def _handle_failure_post_retry(self, call: SkillCall, bus: SkillBus, packet: PerceptionPacket, snapshot: ContextSnapshot, pathfinder) -> SkillResult:
        """Try alternative → ask_user in order after retries failed."""
        # Tier 2: Alternative path (only for navigation)
        if call.skill == "navigate_location":
            alt_result = self._recovery.try_alternative(
                call=call,
                pathfinder=pathfinder,
                app_id=snapshot.active_app,
                target_node=call.params.get("target", ""),
            )
            if alt_result and alt_result.success:
                return alt_result

        # Tier 3: Ask user
        return self._recovery.ask_user(call)

    def _maybe_learn(self, call: SkillCall, packet: PerceptionPacket, learner: ReactiveLearner, success: bool) -> None:
        """Store the path if it was a navigation action with a known target."""
        if call.skill != "navigate_location":
            return
        steps = call.params.get("steps", [])
        uri = call.params.get("uri", "")
        target = call.params.get("target", "")
        if not (steps or uri) or not target:
            return

        app_id = packet.app_context or "unknown"
        from_node = f"app.{app_id}"

        if success:
            learner.learn(
                command=packet.text,
                app_id=app_id,
                from_node_id=from_node,
                to_node_id=target,
                steps=steps,
                result=SkillResult(success=True),
                fast_path="uri" if uri else "",
                fast_path_value=uri,
            )
