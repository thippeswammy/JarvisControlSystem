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
from jarvis.brain.closed_loop_engine import ClosedLoopEngine
from jarvis.llm.llm_router import LLMRouter
from jarvis.memory.layers.episodic import EpisodicMemory
from jarvis.memory.layers.temporal import TemporalMemory
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
        temporal: Optional[TemporalMemory] = None,
        verification_loop=None,
        learning_enabled: bool = False,
        agent_bus=None,
        mcp_bus=None,
    ):
        self._memory = memory
        self._router = router
        self._bus = bus
        self._episodic = episodic or EpisodicMemory()
        self._temporal = temporal or getattr(self._episodic, "_temporal", None) or TemporalMemory()
        self._verification_loop = verification_loop
        self._learning_enabled = learning_enabled


        from jarvis.agents.agent_bus import AgentBus
        from jarvis.mcp.mcp_bus import MCPBus
        self.agent_bus = agent_bus or AgentBus(self._memory)
        self.mcp_bus = mcp_bus or MCPBus()

        self._nlu = NLU(router=self._router)
        from jarvis.perception.context_fusion import ContextFusionLayer
        self._context_fusion = ContextFusionLayer()
        from jarvis.brain.safety_layer import IntentSafetyLayer
        self._safety_layer = IntentSafetyLayer()
        self._context = ContextHarvester(episodic=self._episodic)
        self._planner = Planner(memory, router, bus, agent_bus=self.agent_bus, mcp_bus=self.mcp_bus)
        self._learner = ReactiveLearner(memory)
        self._pathfinder: Optional[GraphPathfinder] = None

        
        from jarvis.perception.goal_understanding import GoalUnderstandingLayer
        from jarvis.perception.grounding_layer import GroundingLayer
        from jarvis.perception.knowledge_gap_engine import KnowledgeGapEngine

        self._goal_understanding = GoalUnderstandingLayer(router=self._router)
        self._grounding = GroundingLayer(episodic=self._episodic)
        self._knowledge_gap = KnowledgeGapEngine()

        
        from jarvis.brain.capability_planner import CapabilityPlanner
        from jarvis.brain.execution_authority import ExecutionAuthority
        from jarvis.brain.user_interaction_manager import UserInteractionManager
        from jarvis.brain.interaction_adapter import AdapterRegistry

        self._capability_planner = CapabilityPlanner()
        self._execution_authority = ExecutionAuthority()
        self.interaction_registry = AdapterRegistry()
        self._interaction_manager = UserInteractionManager(registry=self.interaction_registry)


    def boot(self) -> None:
        """
        Initialize all subsystems. Call once before processing commands.
        """
        # Discover skills
        self._bus.discover()
        logger.info(f"[Orchestrator] Skills: {self._bus.list_skills()}")

        # Discover agents and MCP tools
        self.agent_bus.discover()
        self.mcp_bus.discover()

        # Wire pathfinder into memory
        db = self._memory.get_db()
        self._pathfinder = GraphPathfinder(db)
        self._memory.set_pathfinder(self._pathfinder)

        logger.info("[Orchestrator] Boot complete")

    def process(
        self,
        text: str,
        source: str = "text",
        confidence: float = 1.0,
        metadata: Optional[dict] = None,
        typing_callback: Optional[Callable] = None,
        async_run: bool = False,
        session = None,
        adapter = None
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
        
        # Intent Safety Layer
        packet = self._safety_layer.check_safety(packet)
        
        # Coreference and context fusion
        packet = self._context_fusion.fuse(packet, snapshot=snapshot)
        packet.context_snapshot = snapshot # Store for planner

        # Dynamically wrap and register interaction adapter
        session_id = session.id if session else f"{source}:default"
        if adapter and session:
            from jarvis.brain.interaction_adapter import TelegramInteractionAdapter, TUIInteractionAdapter, WebUIInteractionAdapter
            channel = getattr(session, "channel", source)
            
            interaction_adapter = self.interaction_registry.get_adapter(channel)
            if not interaction_adapter:
                if channel in ("telegram", "telegram-test"):
                    interaction_adapter = TelegramInteractionAdapter(channel_adapter=adapter)
                elif channel in ("tui", "cli"):
                    interaction_adapter = TUIInteractionAdapter(channel_adapter=adapter)
                else:
                    interaction_adapter = WebUIInteractionAdapter(channel_adapter=adapter)
                self.interaction_registry.register(interaction_adapter)
            
            if hasattr(interaction_adapter, "register_session"):
                interaction_adapter.register_session(session)

        # Goal-centric perception layers (Phase 1)
        goal_model = self._goal_understanding.understand(text, app_context=snapshot.active_app)
        goal_model = self._grounding.ground(goal_model, snapshot=snapshot)
        
        # Knowledge Gap Check & Clarification
        gap_result = self._knowledge_gap.check(goal_model)
        if gap_result.clarification_needed:
            for gap in gap_result.gaps:
                if gap.severity == "critical":
                    clarified_value = self._interaction_manager.prompt_clarification(
                        session_id=session_id,
                        question=f"I need more information: {gap.message}. Please clarify:",
                    )
                    if clarified_value:
                        goal_model = self._knowledge_gap.fill_gap(goal_model, gap.parameter, clarified_value)
            # Re-check gaps
            gap_result = self._knowledge_gap.check(goal_model)
            
        packet.goal_model = goal_model

        # Capability Planner (Phase 2 thinker)
        capabilities = self._capability_planner.resolve_capabilities(packet.goal_model)
        providers = self._capability_planner.select_providers(capabilities, self._bus)
        logger.info(f"[Orchestrator] Resolved capabilities: {capabilities} -> Providers: {providers}")

        
        procedural_ctx = self._memory.get_relevant_context(
            text, 
            app_id=snapshot.active_app or None,
            state_sig=snapshot.state_sig
        )
        episodic_ctx = self._episodic.as_llm_context()
        
        packet.memory_context = f"{episodic_ctx}\n\n{procedural_ctx}"

        # Single commands: try memory recall first (fast path), then fall to LLM.
        mem_path = None
        if not packet.compound:
            mem_path = self._memory.recall(
                text, 
                app_id=snapshot.active_app or None,
                state_sig=snapshot.state_sig
            )

        # Plan & Execute via Closed-Loop ReAct Engine
        results = []
        all_success = True
        has_llm_source = False
        has_unsafe_skill = False
        plan = []

        is_conversational = not packet.compound and packet.intent_category in ("EDUCATIONAL", "HYPOTHETICAL", "CAPABILITY", "TEXT_ANALYSIS")

        if is_conversational and packet.intent_category == "TEXT_ANALYSIS":
            packet.safe_mode = True

        # is_fast_path = (
        #     mem_path is not None 
        #     or (not packet.compound and self._bus.is_fast_path_eligible(packet.intent) and (packet.intent_category == "EXECUTION" or packet.intent == "chat_reply"))
        #     or getattr(packet, "safe_mode", False)
        #     or is_conversational
        # )
        # Force all command execution through Closed-Loop LLM reasoning (fast-path disabled)
        is_fast_path = False

        if is_fast_path:
            if mem_path:
                logger.info(f"[Orchestrator] Memory HIT (state-aware) for '{text}'")
                plan = self._planner._path_to_skill_calls(mem_path)
            else:
                logger.info(f"[Orchestrator] Direct-map fast path for intent: {packet.intent}")
                plan = self._planner.plan(packet)

            # Safety gate: ExecutionAuthority
            if not self._execution_authority.validate(plan, self._interaction_manager, session_id):
                logger.warning(f"[Orchestrator] Plan rejected by ExecutionAuthority: {plan}")
                return [SkillResult(success=False, action_taken="Plan aborted due to safety/user rejection.")]

            # Execute the plan sequentially
            for call in plan:
                call.params["_interface"] = snapshot.interface
                call.params["_agent_bus"] = self.agent_bus
                call.params["_mcp_bus"] = self.mcp_bus
                call.params["_router"] = self._router
                
                import time
                start_time = time.perf_counter()
                if self._verification_loop:
                    result = self._verification_loop.execute_and_verify(
                        call=call,
                        bus=self._bus,
                        packet=packet,
                        snapshot=snapshot,
                        learner=self._learner,
                    )
                else:
                    result = self._bus.dispatch(call)
                duration_ms = int((time.perf_counter() - start_time) * 1000)
                results.append(result)
                
                self._temporal.log_event(app_context=snapshot.active_app or "system", action=f"executed {call.skill}", status="SUCCESS" if result.success else "FAILED", duration_ms=duration_ms)
                
                if not result.success:
                    logger.warning(f"[Orchestrator] Fast path plan halted at skill: {call.skill}")
                    all_success = False
                    break

        else:
            # ═══ Closed-Loop Engine (replaces old inline ReAct loop) ═══
            # The engine autonomously cycles System ↔ LLM with:
            #   - Clean empty ExecutionLedger at start (no stale data)
            #   - World-state diffs injected per iteration
            #   - Explicit DONE/BLOCKED signals from LLM
            #   - Adaptive iteration limits
            #   - Integrated RecoveryEngine for self-healing
            
            if async_run and session and adapter:
                import threading
                
                def _async_worker():
                    try:
                        # Let the user know we started
                        adapter.send(session.id, "🚀 *Starting autonomous task execution...*")
                        
                        from jarvis.brain.preference_router import PreferenceRouter
                        try:
                            preference_router = PreferenceRouter()
                        except Exception:
                            preference_router = None

                        engine = ClosedLoopEngine(
                            router=self._router,
                            bus=self._bus,
                            context_harvester=self._context,
                            episodic=self._episodic,
                            temporal=self._temporal,
                            verification_loop=self._verification_loop,
                            learner=self._learner,
                            agent_bus=self.agent_bus,
                            mcp_bus=self.mcp_bus,
                            preference_router=preference_router,
                            max_iterations=10,
                        )

                        loop_result = engine.run(
                            goal=text,
                            packet=packet,
                            initial_snapshot=snapshot,
                            session=session,
                            adapter=adapter
                        )
                        
                        # Map results back for logging / macro learning
                        plan_inner = loop_result.plan
                        results_inner = loop_result.results
                        all_success_inner = loop_result.completed or all(r.success for r in results_inner)
                        
                        # Log command execution exactly once per turn in episodic memory
                        last_app_inner = ""
                        last_skill_inner = ""
                        if plan_inner:
                            last_skill_inner = plan_inner[-1].skill
                        try:
                            last_app_inner = self._context.capture().active_app or ""
                        except Exception:
                            pass
                        self._episodic.log_command(
                            command=text,
                            success=all_success_inner,
                            app=last_app_inner,
                            skill=last_skill_inner,
                            from_memory=False
                        )
                    except Exception as e:
                        logger.error(f"[Orchestrator] Error in background task thread: {e}", exc_info=True)
                        try:
                            adapter.send(session.id, f"❌ *System Error in dynamic execution:* {e}")
                        except: pass
                    finally:
                        # Guarantee that session.active_task is cleared when done
                        session.active_task = None
                        # Stop typing
                        try:
                            adapter.stop_typing(session.id)
                        except: pass
                
                t = threading.Thread(target=_async_worker, name=f"JarvisTask-{session.id}", daemon=True)
                session.active_task = t
                t.start()
                
                # Return lightweight acknowledgment immediately
                return [SkillResult(success=True, action_taken="Dispatched background task.")]

            else:
                from jarvis.brain.preference_router import PreferenceRouter
                try:
                    preference_router = PreferenceRouter()
                except Exception:
                    preference_router = None

                engine = ClosedLoopEngine(
                    router=self._router,
                    bus=self._bus,
                    context_harvester=self._context,
                    episodic=self._episodic,
                    temporal=self._temporal,
                    verification_loop=self._verification_loop,
                    learner=self._learner,
                    agent_bus=self.agent_bus,
                    mcp_bus=self.mcp_bus,
                    preference_router=preference_router,
                    max_iterations=10,
                )

                loop_result = engine.run(
                    goal=text,
                    packet=packet,
                    initial_snapshot=snapshot,
                )

                # Map engine results back to orchestrator variables
                results = loop_result.results
                plan = loop_result.plan
                has_llm_source = loop_result.has_llm_source
                has_unsafe_skill = loop_result.has_unsafe_skill
                all_success = loop_result.completed or all(r.success for r in results)

        # Auto-Learn Semantic Macro (The Reflex)
        # Only runs when --learn-macros flag is active AND plan wasn't from mock backend
        is_mock_plan = any(call.params.get("_source") == "mock" for call in plan)
        if (self._learning_enabled 
            and all_success 
            and has_llm_source 
            and plan 
            and not is_mock_plan
            and packet.intent not in ("chat_reply", "unknown")
            and utterance.confidence >= 0.85):
            # Heuristic: Check for dynamic payloads in physical skills
            is_dynamic_payload = False
            for call in plan:
                if call.skill == "type_text":
                    text_val = str(call.params.get("text", ""))
                    # If text is long (>60 chars) or looks like multiple sentences, treat as dynamic
                    if len(text_val) > 60 or (text_val.count(" ") > 10):
                        is_dynamic_payload = True
                        break

            # Explicitly blacklist dynamic cognitive skills from automatic memorization
            MACRO_BLACKLIST = {
                "type_text", "press_key", "click_browser_node", "fill_browser_node", 
                "click_web_element", "search_web", "run_agent", "run_agent_pipeline", 
                "call_mcp_tool", "extract_browser_dom_tree", "click_element", "scroll_page"
            }
            has_blacklisted_skill = any(call.skill in MACRO_BLACKLIST for call in plan)

            if has_unsafe_skill or is_dynamic_payload or has_blacklisted_skill:
                reason = "dynamic/cognitive blacklisted skill" if has_blacklisted_skill else ("dynamic cognitive skill" if has_unsafe_skill else "dynamic payload content")
                logger.info(f"[Orchestrator] Skipping macro learning: plan contains {reason}")
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

        # Log command execution exactly once per turn in episodic memory
        last_app = ""
        last_skill = ""
        if plan:
            last_skill = plan[-1].skill
        try:
            last_app = self._context.capture().active_app or ""
        except Exception:
            pass
        self._episodic.log_command(
            command=text,
            success=all_success,
            app=last_app,
            skill=last_skill,
            from_memory=bool(mem_path)
        )

        return results

    def set_verification_loop(self, vloop) -> None:
        """Inject verification loop (Phase 6)."""
        self._verification_loop = vloop
