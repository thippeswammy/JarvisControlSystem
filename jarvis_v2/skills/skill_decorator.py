"""
Skill Decorator
===============
@skill decorator for auto-discovery by SkillBus.

Usage:
    from jarvis_v2.skills.skill_decorator import skill

    @skill(triggers=["open notepad", "launch notepad"], priority=0)
    def open_notepad(params: dict) -> SkillResult:
        ...

The decorator attaches metadata to the function without changing behavior.
SkillBus.discover() reads this metadata during pkgutil walk.
"""

import functools
from typing import Callable, Optional


def skill(
    triggers: list[str],
    name: Optional[str] = None,
    priority: int = 0,
    category: str = "general",
    requires: Optional[list[str]] = None,
):
    """
    Decorator to register a function as a Jarvis skill.

    Args:
        triggers:   List of command patterns this skill handles.
                    Used for SkillBus routing and LLM system prompt.
        name:       Canonical skill name (defaults to function name).
        priority:   Higher = tried first. External skills default to 10.
        category:   Grouping label: "system", "app", "window", "keyboard",
                    "navigation", "media", "session", "search".
        requires:   Optional list of Python packages required at runtime.
                    SkillBus warns (but doesn't crash) if missing.
    """
    def decorator(fn: Callable) -> Callable:
        fn.__skill__ = True
        fn.__skill_name__ = name or fn.__name__
        fn.__skill_triggers__ = triggers
        fn.__skill_priority__ = priority
        fn.__skill_category__ = category
        fn.__skill_requires__ = requires or []

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)

        # Copy metadata onto wrapper so it survives decoration
        wrapper.__skill__ = True
        wrapper.__skill_name__ = fn.__skill_name__
        wrapper.__skill_triggers__ = fn.__skill_triggers__
        wrapper.__skill_priority__ = fn.__skill_priority__
        wrapper.__skill_category__ = fn.__skill_category__
        wrapper.__skill_requires__ = fn.__skill_requires__

        return wrapper
    return decorator
