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
from typing import Optional

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
        self._context = ContextHarvester()
        self._planner = Planner(memory, router)
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

    def process(self, text: str, source: str = "text", confidence: float = 1.0) -> SkillResult:
        """
        Full pipeline: text → NLU → Plan → Execute → (Verify) → Learn.

        Returns the SkillResult of the last executed skill.
        """
        utterance = Utterance(text=text, source=source, confidence=confidence)

        # Low-confidence voice input → ask to confirm
        if utterance.source == "voice" and utterance.confidence < 0.70:
            return self._bus.dispatch(SkillCall(
                skill="ask_user",
                params={"reason": f"I heard: '{text}'. Is that correct?"}
            ))

        # Capture context
        snapshot = self._context.capture()

        # NLU
        packet = self._nlu.parse(utterance, app_context=snapshot.active_app)
        
        procedural_ctx = self._memory.get_relevant_context(
            text, app_id=snapshot.active_app or None
        )
        episodic_ctx = self._episodic.as_llm_context()
        
        packet.memory_context = f"{episodic_ctx}\n\n{procedural_ctx}"

        logger.info(
            f"[Orchestrator] '{text}' → intent={packet.intent}, "
            f"app={snapshot.active_app}"
        )

        # Plan
        plan = self._planner.plan(packet)

        # Execute each skill call in the plan
        last_result = SkillResult(success=True, message="No skills executed")
        for call in plan:
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

            last_result = result
            
            # Log to episodic memory
            self._episodic.log_command(
                command=text,
                success=result.success,
                app=snapshot.active_app or "",
                skill=call.skill,
            )

            # Stop plan on failure
            if not result.success:
                logger.warning(f"[Orchestrator] Plan halted at skill: {call.skill}")
                break

        return last_result

    def set_verification_loop(self, vloop) -> None:
        """Inject verification loop (Phase 6)."""
        self._verification_loop = vloop
