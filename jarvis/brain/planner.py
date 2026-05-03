"""
Planner
=======
Converts a PerceptionPacket into an executable Plan (list of SkillCalls).

Decision priority:
    1. Memory recall (A* path or fuzzy trigger match)
    2. Rule-based fast-map (session, volume, brightness — no LLM needed)
    3. LLM Router (Ollama → tunneled → mock)

For compound commands, each sub-command is planned independently.
"""

import logging
from typing import Optional

from jarvis.llm.llm_router import LLMRouter
from jarvis.llm.llm_interface import SkillCallSpec, Plan
from jarvis.memory.memory_manager import MemoryManager, MemoryPath
from jarvis.perception.perception_packet import PerceptionPacket, Utterance
from jarvis.skills.skill_bus import SkillCall

logger = logging.getLogger(__name__)

# Intent → skill_name direct mapping (no LLM needed for these)
_DIRECT_MAP: dict[str, str] = {
    "set_volume":       "set_volume",
    "set_brightness":   "set_brightness",
    "power_action":     "power_action",
    "minimize_window":  "minimize_window",
    "maximize_window":  "maximize_window",
    "snap_window":      "snap_window",
    "switch_window":    "switch_window",
    "press_key":        "press_key",
    "type_text":        "type_text",
    "session_activate": "session_activate",
    "session_deactivate":"session_deactivate",
    "system_status":    "system_status",
    "search_web":       "search_web",
    "search_windows":   "search_windows",
    "click_element":    "click_element",
    "scroll_page":      "scroll_page",
    "ask_user":         "ask_user",
}


class Planner:
    """
    Converts PerceptionPacket → list[SkillCall] (the Plan).

    Usage:
        planner = Planner(memory, router)
        plan = planner.plan(packet)
        for call in plan:
            bus.dispatch(call)
    """

    def __init__(self, memory: MemoryManager, router: LLMRouter):
        self._memory = memory
        self._router = router

    def plan(self, packet: PerceptionPacket) -> list[SkillCall]:
        """Convert PerceptionPacket → ordered list of SkillCalls."""

        # Compound command: plan each sub-command, flatten
        if packet.compound and packet.sub_commands:
            result = []
            for sub in packet.sub_commands:
                sub_packet = PerceptionPacket(
                    utterance=packet.utterance,
                    intent=sub["intent"],
                    entities=sub["entities"],
                    app_context=packet.app_context,
                    memory_context=packet.memory_context,
                )
                result.extend(self._plan_single(sub_packet))
            return result

        return self._plan_single(packet)

    def _plan_single(self, packet: PerceptionPacket) -> list[SkillCall]:
        # 1. Pre-built plan from memory recall (pathfinder result)
        if packet.raw_plan_override:
            logger.info("[Planner] Using memory recall plan")
            return packet.raw_plan_override

        # 2. Direct intent → skill (no LLM needed)
        skill_name = _DIRECT_MAP.get(packet.intent)
        if skill_name:
            logger.info(f"[Planner] Direct map: {packet.intent} → {skill_name}")
            return [SkillCall(skill=skill_name, params=packet.entities)]

        # 3. App opening with optional sub-location
        if packet.intent == "open_app":
            return self._plan_open_app(packet)

        # 4. Navigation
        if packet.intent == "navigate_location":
            return self._plan_navigate(packet)

        # 5. Close app
        if packet.intent == "close_app":
            return [SkillCall(skill="close_app", params=packet.entities)]

        # 6. Unknown intent → LLM
        logger.info(f"[Planner] LLM routing for intent: {packet.intent!r}")
        return self._plan_via_llm(packet)

    def _plan_open_app(self, packet: PerceptionPacket) -> list[SkillCall]:
        target = packet.entities.get("target", "")
        sub = packet.sub_location or packet.entities.get("sub_location", "")

        calls = [SkillCall(skill="open_app", params={"target": target})]

        if sub:
            # Try memory recall for sub-location navigation
            mem_path = self._memory.recall(
                f"navigate {sub}",
                app_id=target if target != "settings" else "settings",
            )
            if mem_path:
                calls.extend(self._path_to_skill_calls(mem_path))
            else:
                # Fallback: Use LLM to figure out the navigation steps
                logger.info(f"[Planner] Sub-location {sub!r} unknown — routing to LLM")
                sub_packet = PerceptionPacket(
                    utterance=Utterance(
                        text=f"navigate to {sub} in {target}",
                        source=packet.utterance.source
                    ),
                    intent="navigate_location",
                    entities={"target": sub, "app": target},
                    app_context=target,
                    memory_context=packet.memory_context,
                )
                calls.extend(self._plan_via_llm(sub_packet))

        return calls

    def _plan_navigate(self, packet: PerceptionPacket) -> list[SkillCall]:
        target = packet.entities.get("target", "")
        app_id = packet.app_context or "settings"

        # Try memory recall
        mem_path = self._memory.recall(
            f"navigate {target}",
            app_id=app_id,
        )
        if mem_path:
            return self._path_to_skill_calls(mem_path)

        # Fallback skill call
        return [SkillCall(skill="navigate_location", params={"target": target})]

    def _plan_via_llm(self, packet: PerceptionPacket) -> list[SkillCall]:
        # Context enrichment for LLM
        enriched_prompt = packet.text
        if packet.app_context and packet.intent != "unknown":
            enriched_prompt = (
                f"Active App Context: {packet.app_context}\n"
                f"Semantic Intent: {packet.intent}\n"
                f"User Utterance: {packet.text}\n\n"
                f"Task: Generate a plan to achieve the semantic intent inside the given active app."
            )

        llm_plan: Plan = self._router.route(
            prompt=enriched_prompt,
            memory_context=packet.memory_context,
        )
        return [
            SkillCall(skill=s.skill, params=s.params, source="llm")
            for s in llm_plan
        ]

    @staticmethod
    def _path_to_skill_calls(path: MemoryPath) -> list[SkillCall]:
        """Convert a MemoryPath into executable SkillCalls."""
        calls = []
        for edge in path.edges:
            if getattr(edge, "action_type", "") == "macro":
                import json
                try:
                    # Generic macros store serialized SkillCalls in action_params["calls"]
                    serialized_calls = edge.action_params.get("calls", [])
                    if isinstance(serialized_calls, str):
                        serialized_calls = json.loads(serialized_calls)
                    
                    for call_dict in serialized_calls:
                        calls.append(SkillCall(
                            skill=call_dict.get("skill", "unknown"),
                            params=call_dict.get("params", {}),
                            source="memory"
                        ))
                except Exception as e:
                    logger.error(f"[Planner] Failed to deserialize macro edge {edge.id}: {e}")
            elif edge.fast_path == "uri":
                calls.append(SkillCall(
                    skill="navigate_location",
                    params={"uri": edge.fast_path_value, "target": edge.to_id},
                    source="memory",
                ))
            elif edge.steps:
                calls.append(SkillCall(
                    skill="navigate_location",
                    params={"steps": edge.steps, "target": edge.to_id},
                    source="memory",
                ))
        return calls
