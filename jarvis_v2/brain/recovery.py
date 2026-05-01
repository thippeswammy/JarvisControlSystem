"""
Recovery Strategies
===================
Used by VerificationLoop when a skill execution fails state verification.

Three recovery tiers:
    1. RETRY       — re-run the same SkillCall (up to max_retries)
    2. ALTERNATIVE — try a different path/strategy via A* re-route
    3. ASK_USER    — surface the failure to the user with diff details

Each tier returns a SkillResult. VerificationLoop calls them in order.
"""

import logging
import time
from typing import Optional

from jarvis_v2.skills.skill_bus import SkillBus, SkillCall, SkillResult

logger = logging.getLogger(__name__)


class RecoveryStrategies:
    """
    Collection of recovery actions called when verification fails.

    Usage (internal, called by VerificationLoop):
        r = RecoveryStrategies(bus, max_retries=2)
        result = r.retry(call, attempt=1)
        if not result.success:
            result = r.ask_user(call, diff={"CheckBox:WiFi": {...}})
    """

    def __init__(self, bus: SkillBus, max_retries: int = 2):
        self._bus = bus
        self._max_retries = max_retries

    def retry(self, call: SkillCall, attempt: int) -> Optional[SkillResult]:
        """
        Re-dispatch the same SkillCall after a short back-off.
        Returns None if max_retries exceeded.
        """
        if attempt > self._max_retries:
            logger.warning(f"[Recovery] Max retries ({self._max_retries}) exceeded for {call.skill}")
            return None

        backoff = 0.5 * attempt
        logger.info(f"[Recovery] Retry #{attempt} for {call.skill!r} (backoff={backoff}s)")
        time.sleep(backoff)
        return self._bus.dispatch(call)

    def try_alternative(
        self,
        call: SkillCall,
        pathfinder=None,
        app_id: str = "",
        target_node: str = "",
    ) -> Optional[SkillResult]:
        """
        Try an alternative route via the pathfinder, using a lower-confidence
        fallback path if a higher-confidence path already failed.
        """
        if not pathfinder or not app_id or not target_node:
            return None

        logger.info(f"[Recovery] Trying alternative path to {target_node!r}")
        result = pathfinder.find(
            app_id=app_id,
            target_node_id=target_node,
        )
        if not result.path:
            return None

        # Execute each edge of the alternative path
        for edge in result.path.edges:
            params = {"steps": edge.steps, "target": edge.to_id}
            if edge.fast_path == "uri":
                params = {"uri": edge.fast_path_value, "target": edge.to_id}
            r = self._bus.dispatch(SkillCall(
                skill="navigate_location",
                params=params,
                source="recovery",
            ))
            if not r.success:
                return r
        return SkillResult(success=True, action_taken="Alternative path executed")

    def ask_user(self, call: SkillCall, diff: dict = None) -> SkillResult:
        """
        Surface failure to the user with details about what didn't match.
        """
        reason = f"I tried '{call.skill}' but the screen didn't change as expected."
        if diff:
            keys = list(diff.keys())[:3]
            reason += f" Mismatched elements: {', '.join(keys)}."

        logger.info(f"[Recovery] Escalating to user: {reason}")
        return self._bus.dispatch(SkillCall(
            skill="ask_user",
            params={
                "reason": reason,
                "question": "Could you guide me, or would you like me to try a different approach?",
            },
        ))
