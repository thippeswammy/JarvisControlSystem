# Custom External Skills for Jarvis AI OS

Jarvis supports dynamic external skills. You can add new capability skills by simply dropping a Python file into this directory (`skills_external/`). Jarvis's `SkillBus` discovers and registers them automatically at boot.

## How to implement a Custom Skill

You implement a custom skill by defining a Python function and decorating it with the `@skill` decorator:

```python
from jarvis.skills.skill_decorator import skill
from jarvis.skills.skill_bus import SkillResult

@skill(
    triggers=["greet the user", "say hello to", "hi to"],
    name="greet_user",
    category="social",
    is_cognitive=False
)
def greet_user(params: dict) -> SkillResult:
    """
    Greets the user.
    Optional params: 'name'
    """
    name = params.get("name", "User")
    message = f"Hello, {name}! I am Jarvis, at your service."
    
    return SkillResult(
        success=True,
        message=message,
        action_taken=f"Greeted user {name!r}"
    )
```

## Adding Custom Slash Commands

You can register a slash command for your skill, allowing the user to type `/command args` directly in Telegram, CLI, or TUI:

```python
import logging
from jarvis.gateway.slash_registry import SlashRegistry

logger = logging.getLogger(__name__)

def handle_greet_slash(args, session, gateway) -> str:
    name = " ".join(args) if args else "User"
    return f"👋 Hello, {name}!"

try:
    SlashRegistry.register(
        cmd="/greet",
        handler=handle_greet_slash,
        description="Greet someone by name",
        category="social"
    )
except Exception as e:
    logger.warning(f"Failed to register slash command: {e}")
```

## Hot-Reloading

Type `/reload` in Telegram or the Jarvis CLI to instantly pick up any changes or new skill files without restarting the daemon process!
