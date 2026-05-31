"""
Capability Planner
==================
Resolves abstract capabilities required by user goals and binds them to the
best concrete providers (skills, agents, or MCP tools) dynamically.
"""

import logging
from typing import List, Dict, Any, Optional
from jarvis.perception.perception_packet import GoalModel
from jarvis.skills.capability_graph import CapabilityGraph

logger = logging.getLogger(__name__)

class CapabilityPlanner:
    """
    Resolves abstract capability requirements based on intents in the GoalModel
    and binds them to the best provider.
    """

    def __init__(self, capability_graph: Optional[CapabilityGraph] = None):
        self.capability_graph = capability_graph or CapabilityGraph()
        # Keep track of provider health scores for dynamic selection
        self.provider_health: Dict[str, float] = {}

    def resolve_capabilities(self, goal_model: GoalModel) -> List[str]:
        """
        Translates GoalModel intents into abstract capability requirements.
        """
        capabilities = []
        for intent in goal_model.intents:
            if intent == "web_search":
                capabilities.append("web_access")
            elif intent == "content_generation":
                capabilities.append("text_generation")
            elif intent == "app_interaction":
                capabilities.append("app_control")
            elif intent == "system_control":
                capabilities.append("system_control")
            elif intent in ("text_edit", "code_generation"):
                capabilities.append("text_edit")

        # Fallback to general OS capability if none identified but primary goal is present
        if not capabilities and goal_model.primary_goal:
            capabilities.append("app_control")

        # Deduplicate while preserving order
        seen = set()
        return [c for c in capabilities if not (c in seen or seen.add(c))]

    def select_providers(self, capabilities: List[str], registry: Optional[Any] = None) -> List[Dict[str, Any]]:
        """
        Binds abstract capability requirements to concrete providers based on health and availability.
        
        Returns:
            List[Dict[str, Any]]: A list of dicts with:
                - capability: The abstract capability
                - provider_type: 'skill' | 'agent' | 'mcp'
                - provider_name: The concrete name of the tool/skill/agent
                - health_score: Provider health score
        """
        providers = []
        for cap in capabilities:
            p_type = "skill"
            p_name = "unknown"

            if cap == "web_access":
                p_type = "agent"
                p_name = "browser_agent"
            elif cap == "text_generation":
                p_type = "skill"
                p_name = "chat_reply"
            elif cap == "app_control":
                p_type = "skill"
                p_name = "open_app"
            elif cap == "system_control":
                p_type = "skill"
                p_name = "press_key"
            elif cap == "text_edit":
                p_type = "skill"
                p_name = "type_text"

            health = self.provider_health.get(p_name, 1.0)
            providers.append({
                "capability": cap,
                "provider_type": p_type,
                "provider_name": p_name,
                "health_score": health
            })

        return providers

    def update_provider_health(self, name: str, success: bool) -> None:
        """
        Updates dynamic health scores for providers based on execution outcomes.
        """
        current = self.provider_health.get(name, 1.0)
        if success:
            new_health = min(1.0, current + 0.05)
        else:
            new_health = max(0.0, current - 0.20)
        self.provider_health[name] = round(new_health, 2)
        logger.debug(f"[CapabilityPlanner] Updated health for '{name}': {new_health}")
