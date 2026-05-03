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
from jarvis.brain.preference_router import PreferenceRouter
from jarvis.memory.memory_manager import MemoryManager, MemoryPath
from jarvis.perception.perception_packet import PerceptionPacket, Utterance
from jarvis.skills.skill_bus import SkillCall, SkillBus

logger = logging.getLogger(__name__)

# Intent → skill_name direct mapping (only safety/session intents bypass LLM)
_DIRECT_MAP: dict[str, str] = {
    "power_action":     "power_action",
    "session_activate": "session_activate",
    "session_deactivate":"session_deactivate",
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

    def __init__(self, memory: MemoryManager, router: LLMRouter, bus: SkillBus):
        self._memory = memory
        self._router = router
        self._bus = bus
        self._preference_router = PreferenceRouter()

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
                result.extend(self._plan_single(sub_packet, snapshot=packet.context_snapshot))
            return result

        return self._plan_single(packet, snapshot=packet.context_snapshot)

    def _plan_single(self, packet: PerceptionPacket, snapshot=None) -> list[SkillCall]:
        # 1. Pre-built plan from memory recall (pathfinder result)
        if packet.raw_plan_override:
            logger.info("[Planner] Using memory recall plan")
            return packet.raw_plan_override

        # 2. Unknown intent / all others → LLM Unified Router
        logger.info(f"[Planner] Unified LLM routing for intent: {packet.intent!r}")
        return self._plan_via_unified_llm(packet, snapshot=snapshot)

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

    def _plan_via_unified_llm(self, packet: PerceptionPacket, snapshot=None) -> list[SkillCall]:
        # Context enrichment for LLM
        system_ctx = self._preference_router.get_system_context()
        ui_ctx = "UI State: Unknown"
        lineage_ctx = "State reached by: UNKNOWN"

        if snapshot:
            if snapshot.ui_snapshot:
                ui_ctx = snapshot.ui_snapshot.to_llm_context()
            if snapshot.state_origin:
                lineage_ctx = f"State reached by: {snapshot.state_origin} — '{snapshot.prior_action}'"

        skill_catalog = self._bus.get_skill_catalog()
        episodic_context = packet.memory_context or "No recent memory."

        enriched_context = (
            f"[System Preferences]\n{system_ctx}\n\n"
            f"[Current UI State]\n{ui_ctx}\n\n"
            f"[State Provenance]\n{lineage_ctx}\n\n"
            f"[Episodic Memory]\n{episodic_context}\n\n"
            f"[Available Skills]\n{skill_catalog}\n"
        )

        decision = self._router.decide(
            prompt=packet.text,
            context=enriched_context,
        )

        if not decision:
            logger.error("[Planner] LLM returned no decision.")
            return [SkillCall(skill="chat_reply", params={"message": "I'm sorry, I failed to generate a response."})]

        calls = []
        
        # 1. Chat
        if decision.type == "chat":
            if decision.message:
                calls.append(SkillCall(skill="chat_reply", params={"message": decision.message}))
                
        # 2. Plan
        elif decision.type == "plan":
            if decision.steps:
                for s in decision.steps:
                    calls.append(SkillCall(skill=s.skill, params=s.params, source="llm"))
                    
        # 3. Mixed
        elif decision.type == "mixed":
            if decision.message:
                calls.append(SkillCall(skill="chat_reply", params={"message": decision.message}))
            if decision.steps:
                for s in decision.steps:
                    calls.append(SkillCall(skill=s.skill, params=s.params, source="llm"))
                    
        # 4. Clarify
        elif decision.type == "clarify":
            if decision.question:
                calls.append(SkillCall(skill="ask_user", params={"question": decision.question}))

        # Safety fallback
        if not calls:
            logger.warning(f"[Planner] Decision generated no calls: {decision}")
            calls.append(SkillCall(skill="chat_reply", params={"message": "I'm not quite sure how to do that."}))
            
        return calls

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
