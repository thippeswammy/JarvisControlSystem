import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict

from jarvis.brain.orchestrator import Orchestrator
from jarvis.memory.layers.episodic import EpisodicMemory
from jarvis.memory.memory_manager import MemoryManager
from jarvis.llm.llm_router import LLMRouter
from jarvis.skills.skill_bus import SkillBus
from jarvis.gateway.slash_handler import SlashHandler

logger = logging.getLogger(__name__)

@dataclass
class Session:
    id: str                        # "{channel}:{user_id}"
    channel: str                   # "cli" | "telegram" | "telegram-test"
    user_id: str
    created_at: datetime
    last_active: datetime
    orchestrator: Orchestrator     # isolated per session
    episodic: EpisodicMemory       # isolated per channel/session
    slash_handler: SlashHandler    # shared command logic

class SessionManager:
    """
    Manages isolated Jarvis sessions.
    Each session has its own Orchestrator and EpisodicMemory,
    but shares the procedural MemoryManager, LLMRouter, and SkillBus.
    """
    def __init__(self, memory: MemoryManager, router: LLMRouter, bus: SkillBus, gateway, vloop=None):
        self._memory = memory
        self._router = router
        self._bus = bus
        self._gateway = gateway
        self._vloop = vloop
        self._sessions: Dict[str, Session] = {}

    def get_or_create(self, channel: str, user_id: str) -> Session:
        session_id = f"{channel}:{user_id}"
        
        if session_id in self._sessions:
            session = self._sessions[session_id]
            session.last_active = datetime.now()
            return session

        logger.info(f"[SessionManager] Creating new session: {session_id}")
        
        # Per your decision: share procedural memory, isolate episodic.
        # Note: We might want to isolate episodic per channel, or per user.
        # For now, let's do it per session_id (which is channel:user).
        episodic = EpisodicMemory() 
        
        orch = Orchestrator(
            memory=self._memory,
            router=self._router,
            bus=self._bus,
            episodic=episodic,
            verification_loop=self._vloop,
            agent_bus=getattr(self._gateway, "agent_bus", None),
            mcp_bus=getattr(self._gateway, "mcp_bus", None)
        )
        orch.boot() # Ensure orchestrator is ready

        session = Session(
            id=session_id,
            channel=channel,
            user_id=user_id,
            created_at=datetime.now(),
            last_active=datetime.now(),
            orchestrator=orch,
            episodic=episodic,
            slash_handler=SlashHandler(None, self._gateway) # Will set session below
        )
        session.slash_handler._session = session # circular ref fix
        
        self._sessions[session_id] = session
        return session

    def list_sessions(self) -> list[Session]:
        return list(self._sessions.values())

    def get(self, session_id: str) -> Optional[Session]:
        return self._sessions.get(session_id)

    def kill(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"[SessionManager] Killed session: {session_id}")
            return True
        return False

    def cleanup_idle(self, max_age_minutes: int = 60):
        now = datetime.now()
        to_kill = []
        for sid, sess in self._sessions.items():
            age = (now - sess.last_active).total_seconds() / 60
            if age > max_age_minutes:
                to_kill.append(sid)
        
        for sid in to_kill:
            self.kill(sid)
        
        if to_kill:
            logger.info(f"[SessionManager] Cleaned up {len(to_kill)} idle sessions")
