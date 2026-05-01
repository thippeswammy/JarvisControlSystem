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
import time
from typing import Optional

from jarvis_v2.brain.reactive_learner import ReactiveLearner
from jarvis_v2.brain.recovery import RecoveryStrategies
from jarvis_v2.memory.state_harvester import StateHarvester
from jarvis_v2.memory.state_comparator import StateComparator
from jarvis_v2.perception.perception_packet import PerceptionPacket, ContextSnapshot
from jarvis_v2.skills.skill_bus import SkillBus, SkillCall, SkillResult

logger = logging.getLogger(__name__)

# Skills that don't produce a verifiable UI state change
SKIP_VERIFY_SKILLS = {
    "type_text", "press_key", "search_web", "search_windows",
    "session_activate", "session_deactivate", "system_status",
    "ask_user", "set_volume", "set_brightness", "power_action",
    "scroll_page",
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

    def __init__(
        self,
        harvester: StateHarvester,
        comparator: StateComparator,
        recovery: RecoveryStrategies,
        settle_ms: int = _DEFAULT_SETTLE_MS,
    ):
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

        # 1. Capture BEFORE state
        before_state, before_hash = self._harvester.harvest_and_hash(
            app_title=snapshot.active_app or None
        )

        # 2. Execute
        result = bus.dispatch(call)
        if not result.success:
            logger.info(f"[VerificationLoop] Skill failed pre-verification: {call.skill}")
            return self._handle_failure(call, bus, result, packet, snapshot, pathfinder)

        # 3. Wait for UI to settle
        time.sleep(self._settle_ms / 1000.0)

        # 4. Capture AFTER state
        after_state, after_hash = self._harvester.harvest_and_hash(
            app_title=snapshot.active_app or None
        )

        # 5. Compare
        # No UIA = both hashes are empty strings (StateHarvester unavailable)
        if not before_hash and not after_hash:
            logger.debug("[VerificationLoop] No UI state (UIA unavailable), trusting skill result")
            self._maybe_learn(call, packet, learner, success=result.success)
            return result

        state_changed = before_hash != after_hash

        if state_changed:
            # ✅ State changed — verified success
            logger.info(f"[VerificationLoop] ✅ State changed: {call.skill} ({before_hash} -> {after_hash})")
            self._maybe_learn(call, packet, learner, success=True)
            result.action_taken = f"[Verified] {result.action_taken}"
            return result

        # ❌ No state change — unexpected
        logger.warning(f"[VerificationLoop] ❌ No state change after: {call.skill} (Hash: {before_hash})")
        return self._handle_failure(call, bus, result, packet, snapshot, pathfinder)

    # ── Private ──────────────────────────────────────

    def _handle_failure(
        self,
        call: SkillCall,
        bus: SkillBus,
        result: SkillResult,
        packet: PerceptionPacket,
        snapshot: ContextSnapshot,
        pathfinder,
    ) -> SkillResult:
        """Try retry → alternative → ask_user in order."""
        # Tier 1: Retry (back-off without re-harvesting — harvester is expensive)
        for attempt in range(1, 3):
            retry_result = self._recovery.retry(call, attempt)
            if retry_result and retry_result.success:
                return retry_result

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

    def _maybe_learn(
        self,
        call: SkillCall,
        packet: PerceptionPacket,
        learner: ReactiveLearner,
        success: bool,
    ) -> None:
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
