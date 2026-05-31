"""
Execution Authority Safety Layer
================================
Validates all actions and plans before execution, categorizing their risk levels
and gating high-risk operations behind user confirmations unless full autonomy is enabled.
"""

import logging
from typing import List, Any, Optional
from jarvis.skills.skill_bus import SkillCall
from jarvis.brain.user_interaction_manager import UserInteractionManager

logger = logging.getLogger(__name__)

class ExecutionAuthority:
    """
    Safety gateway that validates plans before execution, enforcing safety policies.
    """

    def __init__(self, full_autonomy: bool = False):
        self.full_autonomy = full_autonomy
        
        # Risk levels: SAFE, MODERATE, HIGH
        self.safe_skills = {
            "chat_reply", "open_app", "type_text", "switch_browser_tab",
            "extract_browser_dom_tree", "click_browser_node", "fill_browser_node",
            "get_focused_element", "get_element_tree", "find_element", "find_all_elements",
            "get_element_parent", "get_element_children", "get_element_siblings",
            "get_element_properties", "get_element_patterns", "get_element_rect",
            "get_window_info", "wait_for_element", "get_grid_data", "get_text_range",
            "get_selection", "get_annotation"
        }
        
        self.moderate_skills = {
            "close_app", "navigate_location", "press_key", "close_page",
            "set_window_state", "move_window", "resize_window", "set_foreground_window",
            "scroll_element", "set_slider_value", "expand_element", "collapse_element",
            "set_scroll_position", "toggle_element", "click_element"
        }
        
        self.high_skills = {
            "run_shell", "delete_file", "system_power", "drag_element", "invoke_element"
        }

    def evaluate_risk(self, plan: List[SkillCall]) -> str:
        """
        Computes the maximum risk level of a plan.
        Returns "SAFE", "MODERATE", or "HIGH".
        """
        max_risk = "SAFE"
        
        for call in plan:
            skill = call.skill
            
            # Context-sensitive risk checks
            if skill in self.high_skills:
                return "HIGH"
            
            if skill == "press_key":
                key = str(call.params.get("key", "")).lower()
                if "delete" in key or "backspace" in key or "enter" in key:
                    return "HIGH" # Treat destructive key presses as HIGH risk
                max_risk = "MODERATE"
            elif skill in self.moderate_skills:
                if max_risk == "SAFE":
                    max_risk = "MODERATE"
            elif skill not in self.safe_skills:
                # Any unknown skill is treated as MODERATE by default for safety
                if max_risk == "SAFE":
                    max_risk = "MODERATE"
                    
        return max_risk

    def validate(
        self, 
        plan: List[SkillCall], 
        interaction_manager: Optional[UserInteractionManager] = None, 
        session_id: Optional[str] = None
    ) -> bool:
        """
        Validates the proposed execution plan.
        Returns True if approved (or if full_autonomy is enabled), False if denied.
        """
        if self.full_autonomy:
            logger.info("[ExecutionAuthority] Full autonomy enabled. Plan auto-approved.")
            return True

        risk = self.evaluate_risk(plan)
        logger.info(f"[ExecutionAuthority] Evaluated plan risk: {risk}")

        if risk == "HIGH":
            if not interaction_manager or not session_id:
                logger.warning("[ExecutionAuthority] Risk is HIGH, but no interaction manager/session provided. Defaulting to DENY.")
                return False
            
            # Build detailed action description
            descriptions = []
            for call in plan:
                descriptions.append(f"• `{call.skill}` with parameters {call.params}")
            action_desc = "\n".join(descriptions)
            
            approved = interaction_manager.request_confirmation(session_id, action_desc)
            if approved:
                logger.info("[ExecutionAuthority] Plan approved by user.")
                return True
            else:
                logger.info("[ExecutionAuthority] Plan denied by user.")
                return False
                
        return True
