import logging
from jarvis.skills.skill_decorator import skill
from jarvis.skills.skill_bus import SkillResult

logger = logging.getLogger(__name__)


@skill(
    triggers=["greet the user", "say hello to", "hi to", "send greetings"],
    name="greet_user",
    category="social",
    is_cognitive=False,
)
def greet_user(params: dict) -> SkillResult:
    """
    Greets the user warmly by name.
    Params:
      name (str, optional): Name of the user to greet.
    """
    name = params.get("name") or params.get("target") or "User"
    message = f"Hello, {name}! I am Jarvis. How can I assist you today?"
    
    return SkillResult(
        success=True,
        message=message,
        action_taken=f"Greeted {name!r}"
    )


def handle_greet_slash(args, session, gateway) -> str:
    """Slash command handler for /greet."""
    name = " ".join(args) if args else "User"
    # Dispatch to the greet_user skill using the SkillBus
    if gateway and gateway.bus:
        res = gateway.bus.dispatch_name("greet_user", {"name": name})
        return f"🟢 [greet_user skill] {res.message}"
    return f"👋 [greet fallback] Hello, {name}!"


# Automatically self-register slash command
try:
    from jarvis.gateway.slash_registry import SlashRegistry
    SlashRegistry.register(
        cmd="/greet",
        handler=handle_greet_slash,
        description="Greet the user or a target name warmly",
        category="social"
    )
except Exception as e:
    logger.warning(f"Failed to auto-register /greet slash command: {e}")
