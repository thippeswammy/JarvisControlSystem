"""
Dynamic Recovery Engine
=======================
Diagnoses, categorizes, and executes dynamic self-healing procedures when skill calls
encounter exceptions (e.g., PyAutoGUI fail-safes, missing elements, or lost focus).
"""

import logging
from typing import List, Optional, Any
from jarvis.skills.skill_bus import SkillCall

logger = logging.getLogger(__name__)

class FailureCategory:
    FAIL_SAFE = "FAIL_SAFE"
    ELEMENT_MISSING = "ELEMENT_MISSING"
    FOCUS_LOST = "FOCUS_LOST"
    TIMEOUT = "TIMEOUT"
    UNKNOWN = "UNKNOWN"

class RecoveryEngine:
    """Diagnoses failures during action execution and dynamically computes corrective remedies."""

    @staticmethod
    def diagnose_and_heal(error_msg: str, failed_call: SkillCall, active_app: str) -> List[SkillCall]:
        """
        Diagnoses the specific failure type from error text and generates
        a curative sequence of corrective SkillCalls.
        """
        err_lower = error_msg.lower()
        category = FailureCategory.UNKNOWN
        
        # 1. Diagnose Failure Category
        if "fail-safe" in err_lower or "failsafe" in err_lower:
            category = FailureCategory.FAIL_SAFE
        elif "element" in err_lower or "selector" in err_lower or "locator" in err_lower:
            category = FailureCategory.ELEMENT_MISSING
        elif "focus" in err_lower or "foreground" in err_lower or "hwnd" in err_lower:
            category = FailureCategory.FOCUS_LOST
        elif "timeout" in err_lower or "expired" in err_lower:
            category = FailureCategory.TIMEOUT

        logger.warning(f"[RecoveryEngine] Diagnosed failure category: {category} for action: {failed_call.skill}")

        # 2. Compute Healing Remedy plan
        corrective_plan: List[SkillCall] = []

        if category == FailureCategory.FAIL_SAFE:
            # Mitigation: Recenter pointer, restore focus via UIA clicks directly to target window
            logger.info("[RecoveryEngine] Recovery: Resetting mouse coordinates and setting window focus via UIA...")
            corrective_plan.append(SkillCall(
                skill="activate_window",
                params={"target": active_app}
            ))

        elif category == FailureCategory.ELEMENT_MISSING:
            # Mitigation: Re-extract accessibility DOM or scroll browser window to refresh layouts
            logger.info("[RecoveryEngine] Recovery: Refreshing active layouts & DOM hierarchy...")
            if failed_call.skill in ["click_browser_node", "fill_browser_node", "click_web_element"]:
                corrective_plan.append(SkillCall(skill="extract_browser_dom_tree", params={}))
            else:
                # Standard desktop window: try minimizing and maximizing to force layout updates
                corrective_plan.extend([
                    SkillCall(skill="minimize_window", params={}),
                    SkillCall(skill="maximize_window", params={})
                ])

        elif category == FailureCategory.FOCUS_LOST:
            # Mitigation: Explicitly lookup and re-focus active app
            logger.info(f"[RecoveryEngine] Recovery: Refocusing missing window for {active_app!r}...")
            corrective_plan.append(SkillCall(
                skill="open_app",
                params={"target": active_app}
            ))

        elif category == FailureCategory.TIMEOUT:
            # Mitigation: Increase wait latency or retry layout settling
            logger.info("[RecoveryEngine] Recovery: Issuing longer settle time and re-initiating UIA search...")
            corrective_plan.append(SkillCall(
                skill="activate_window",
                params={"target": active_app}
            ))

        # Default fallback
        if not corrective_plan:
            logger.info("[RecoveryEngine] No precise programmatic remedy found. Requesting help.")
            corrective_plan.append(SkillCall(
                skill="chat_reply",
                params={"message": f"I hit an unexpected error while executing {failed_call.skill}: '{error_msg}'. Can you help verify if the application is open?"}
            ))

        return corrective_plan
