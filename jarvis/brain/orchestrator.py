"""
Orchestrator (Brain)
====================
Central decision loop. Routes each PerceptionPacket through:

    Memory hit?  → execute plan from memory
    Known intent? → direct map via Planner
    LLM?         → plan via router
    Unknown?     → ask_user

Every SkillCall is wrapped by the VerificationLoop before storing.
"""

import logging
from typing import Optional, Callable

from jarvis.brain.planner import Planner
from jarvis.brain.reactive_learner import ReactiveLearner
from jarvis.llm.llm_router import LLMRouter
from jarvis.memory.layers.episodic import EpisodicMemory
from jarvis.memory.memory_manager import MemoryManager
from jarvis.pathfinding.graph_pathfinder import GraphPathfinder
from jarvis.perception.context_harvester import ContextHarvester
from jarvis.perception.nlu import NLU
from jarvis.perception.perception_packet import PerceptionPacket, Utterance
from jarvis.skills.skill_bus import SkillBus, SkillCall, SkillResult

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Main v2 pipeline entry point.

    Wiring (set up once on startup):
        orch = Orchestrator(memory, router, bus)
        orch.boot()
        result = orch.process("open display settings")
    """

    def __init__(
        self,
        memory: MemoryManager,
        router: LLMRouter,
        bus: SkillBus,
        episodic: Optional[EpisodicMemory] = None,
        verification_loop=None,
    ):
        self._memory = memory
        self._router = router
        self._bus = bus
        self._episodic = episodic or EpisodicMemory()
        self._verification_loop = verification_loop

        self._nlu = NLU()
        self._context = ContextHarvester(episodic=self._episodic)
        self._planner = Planner(memory, router, bus)
        self._learner = ReactiveLearner(memory)
        self._pathfinder: Optional[GraphPathfinder] = None

    def boot(self) -> None:
        """
        Initialize all subsystems. Call once before processing commands.
        """
        # Discover skills
        self._bus.discover()
        logger.info(f"[Orchestrator] Skills: {self._bus.list_skills()}")

        # Wire pathfinder into memory
        db = self._memory.get_db()
        self._pathfinder = GraphPathfinder(db)
        self._memory.set_pathfinder(self._pathfinder)

        logger.info("[Orchestrator] Boot complete ✅")

    def process(
        self,
        text: str,
        source: str = "text",
        confidence: float = 1.0,
        metadata: Optional[dict] = None,
        typing_callback: Optional[Callable] = None
    ) -> list[SkillResult]:
        """
        Full pipeline: text → NLU → Plan → Execute → (Verify) → Learn.

        Returns a list of SkillResult objects for each executed step in the plan.
        """
        if typing_callback:
            typing_callback()
            
        utterance = Utterance(text=text, source=source, confidence=confidence, metadata=metadata)


        # Low-confidence voice input → ask to confirm
        if utterance.source == "voice" and utterance.confidence < 0.70:
            return [self._bus.dispatch(SkillCall(
                skill="ask_user",
                params={"reason": f"I heard: '{text}'. Is that correct?"}
            ))]

        # Capture context
        snapshot = self._context.capture()
        snapshot.interface = source # Track the source (telegram, text, etc.)

        # NLU
        packet = self._nlu.parse(utterance, app_context=snapshot.active_app)
        packet.context_snapshot = snapshot # Store for planner
        
        procedural_ctx = self._memory.get_relevant_context(
            text, 
            app_id=snapshot.active_app or None,
            state_sig=snapshot.state_sig
        )
        episodic_ctx = self._episodic.as_llm_context()
        
        packet.memory_context = f"{episodic_ctx}\n\n{procedural_ctx}"

        logger.info(
            f"[Orchestrator] '{text}' → intent={packet.intent}, "
            f"app={snapshot.active_app}"
        )

        # Plan
        # Compound commands go directly to the LLM (full sentence, one call).
        # Single commands: try memory recall first (fast path), then fall to LLM.
        mem_path = None
        if not packet.compound:
            mem_path = self._memory.recall(
                text, 
                app_id=snapshot.active_app or None,
                state_sig=snapshot.state_sig
            )
        
        if mem_path:
            logger.info(f"[Orchestrator] Memory HIT (state-aware) for '{text}'")
            plan = self._planner._path_to_skill_calls(mem_path)
        else:
            if packet.compound:
                logger.info("[Orchestrator] Compound command → single LLM call")
            plan = self._planner.plan(packet)

        # Execute each skill call in the plan
        results = []
        all_success = True
        has_llm_source = False
        has_unsafe_skill = False
        
        for call in plan:
            call.params["_interface"] = snapshot.interface
            if getattr(call, "source", "") == "llm":
                has_llm_source = True
            if self._bus.is_cognitive(call.skill):
                has_unsafe_skill = True

            if self._verification_loop:
                result = self._verification_loop.execute_and_verify(
                    call=call,
                    bus=self._bus,
                    packet=packet,
                    snapshot=snapshot,
                    learner=self._learner,
                )
            else:
                # Phase 5 mode: execute without verification
                result = self._bus.dispatch(call)

            results.append(result)
            
            # Log to episodic memory
            self._episodic.log_command(
                command=text,
                success=result.success,
                app=snapshot.active_app or "",
                skill=call.skill,
            )

            # Record state transition for lineage tracking
            if result.success:
                self._episodic.record_state_transition(
                    state_sig="", # post-execution state (unknown until next cycle)
                    cause="JARVIS",
                    action=f"executed {call.skill}",
                    skill_used=call.skill,
                    app_context=snapshot.active_app or ""
                )

            # Stop plan on failure
            if not result.success:
                logger.warning(f"[Orchestrator] Plan halted at skill: {call.skill}")
                all_success = False
                break

        # Auto-Learn Semantic Macro (The Reflex)
        if all_success and has_llm_source and plan:
            if has_unsafe_skill:
                logger.info("[Orchestrator] Skipping macro learning: plan contains dynamic cognitive skill")
            else:
                import json
                import hashlib
                from datetime import date
                from jarvis.memory.graph_db import GraphNode, GraphEdge
                
                db = self._memory.get_db()
                if not db.get_node("app.global"):
                    db.save_node(GraphNode(id="app.global", app_id="global", type="APP", label="Global System"))

                serialized_calls = [{"skill": c.skill, "params": c.params} for c in plan]
                plan_json = json.dumps(serialized_calls)
                plan_hash = hashlib.md5(plan_json.encode()).hexdigest()[:8]
                
                target_node_id = f"global.macro_{plan_hash}"
                if not db.get_node(target_node_id):
                    db.save_node(GraphNode(id=target_node_id, app_id="global", type="PAGE", label=f"Macro {plan_hash}"))

                edge_id = f"edge.macro_{plan_hash}"
                existing_edge = db.get_edge(edge_id)

                if existing_edge:
                    trigger_clean = text.lower().strip()
                    existing_triggers = [t.lower().strip() for t in existing_edge.triggers]
                    if trigger_clean not in existing_triggers:
                        existing_edge.triggers.append(text)
                        self._memory.add_learned_macro(existing_edge)
                        logger.info(f"[Orchestrator] Added new trigger {text!r} to existing macro {edge_id}")
                else:
                    new_edge = GraphEdge(
                        id=edge_id,
                        from_id="app.global",
                        to_id=target_node_id,
                        edge_type="FORWARD",
                        action_type="macro",
                        action_params={"calls": plan_json},
                        triggers=[text],
                        confidence=0.85,
                        success_count=1,
                        last_used=date.today().isoformat(),
                        starting_state_sig=snapshot.state_sig,
                        state_origin=snapshot.state_origin,
                        prior_action=snapshot.prior_action
                    )
                    self._memory.add_learned_macro(new_edge)
                    logger.info(f"[Orchestrator] Learned new state-aware macro for trigger: {text!r}")

        return results

    def set_verification_loop(self, vloop) -> None:
        """Inject verification loop (Phase 6)."""
        self._verification_loop = vloop
