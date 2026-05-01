"""Session Skill — Jarvis session lifecycle management."""
import logging
from jarvis_v2.skills.skill_decorator import skill
from jarvis_v2.skills.skill_bus import SkillResult

logger = logging.getLogger(__name__)


@skill(triggers=["activate session", "hi jarvis", "hello jarvis", "hey jarvis", "wake up"],
       name="session_activate", category="session")
def session_activate(params: dict) -> SkillResult:
    logger.info("[session_skill] Session activated")
    return SkillResult(
        success=True,
        message="Hello! I'm Jarvis. How can I help you?",
        action_taken="Session activated",
    )


@skill(triggers=["deactivate session", "bye jarvis", "goodbye jarvis", "stop listening",
                 "close jarvis", "sleep jarvis"],
       name="session_deactivate", category="session")
def session_deactivate(params: dict) -> SkillResult:
    logger.info("[session_skill] Session deactivated")
    return SkillResult(
        success=True,
        message="Goodbye! Call me anytime.",
        action_taken="Session deactivated",
    )


@skill(triggers=["ask user", "clarify", "i don't understand", "need clarification"],
       name="ask_user", category="session")
def ask_user(params: dict) -> SkillResult:
    """Called when Jarvis needs user input to proceed."""
    reason = params.get("reason", "I need more information to proceed.")
    question = params.get("question", "Could you clarify what you mean?")
    logger.info(f"[session_skill] Asking user: {reason}")
    return SkillResult(
        success=True,
        message=f"{reason} {question}",
        action_taken="Asked user for clarification",
        data={"needs_input": True, "reason": reason},
    )


@skill(triggers=["system status", "jarvis status", "health check"],
       name="system_status", category="session")
def system_status(params: dict) -> SkillResult:
    import platform, psutil
    cpu = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory()
    msg = (
        f"System: {platform.node()} | "
        f"CPU: {cpu}% | "
        f"RAM: {ram.used // (1024**2)}MB / {ram.total // (1024**2)}MB"
    )
    return SkillResult(success=True, message=msg, action_taken="Status reported")
