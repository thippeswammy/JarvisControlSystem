"""
SkillBus
========
Auto-discovers and dispatches @skill-decorated functions.

Discovery order (highest priority wins):
    1. skills_external/   (user-added skills, priority 10 default)
    2. jarvis/skills/builtins/   (built-in skills, priority 0)

Usage:
    bus = SkillBus()
    bus.discover()
    result = bus.dispatch(SkillCall(skill="open_app", params={"target": "notepad"}))
"""

import importlib
import logging
import pkgutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

_BUILTINS_PKG = "jarvis.skills.builtins"
_EXTERNAL_DIR = Path(__file__).parent.parent.parent / "skills_external"


@dataclass
class SkillCall:
    skill: str
    params: dict = field(default_factory=dict)
    category: str = ""
    source: str = "llm"  # llm | memory | user | test


@dataclass
class SkillResult:
    success: bool
    message: str = ""
    data: Any = None
    action_taken: str = ""
    skill_name: str = ""


@dataclass
class _SkillEntry:
    name: str
    fn: Callable
    triggers: list[str]
    priority: int
    category: str
    requires: list[str]
    is_cognitive: bool = False
    settle_ms: int = 0


class SkillBus:
    """
    Auto-discovers @skill-decorated functions via pkgutil.walk_packages.
    Dispatches SkillCall → SkillResult.
    """

    def __init__(self):
        self._registry: dict[str, _SkillEntry] = {}  # name → entry
        self._discovered = False

    def discover(
        self,
        extra_paths: Optional[list[str]] = None,
        include_external: bool = True,
    ) -> int:
        """
        Walk builtins + external directories for @skill-decorated functions.
        Returns number of skills registered.
        """
        # 1. Builtins (priority 0)
        self._walk_package(_BUILTINS_PKG)

        # 2. External (priority 10 default)
        if include_external and _EXTERNAL_DIR.exists():
            import sys
            ext_str = str(_EXTERNAL_DIR.parent)
            if ext_str not in sys.path:
                sys.path.insert(0, ext_str)
            self._walk_package("skills_external")

        # 3. Any caller-supplied extra paths
        if extra_paths:
            for path in extra_paths:
                self._walk_package(path)

        self._discovered = True
        logger.info(f"[SkillBus] Discovered {len(self._registry)} skills: "
                    f"{sorted(self._registry.keys())}")
        return len(self._registry)

    def dispatch(self, call: SkillCall) -> SkillResult:
        """
        Find the best-matching skill and execute it.
        Falls back to a not-found result if no skill matches.
        """
        if not self._discovered:
            self.discover()

        entry = self._find(call.skill)
        if not entry:
            logger.warning(f"[SkillBus] No skill found for: {call.skill!r}")
            return SkillResult(
                success=False,
                message=f"Unknown skill: {call.skill!r}",
                skill_name=call.skill,
            )

        # Check requirements
        missing = self._check_requires(entry)
        if missing:
            logger.error(f"[SkillBus] Skill '{entry.name}' missing deps: {missing}")
            return SkillResult(
                success=False,
                message=f"Skill '{entry.name}' requires: {missing}",
                skill_name=entry.name,
            )

        logger.info(f"[SkillBus] Dispatching: {entry.name}({call.params})")
        try:
            result = entry.fn(call.params)
            if isinstance(result, SkillResult):
                result.skill_name = entry.name
                return result
            # If the skill returned a plain bool/string — wrap it
            if isinstance(result, bool):
                return SkillResult(success=result, skill_name=entry.name)
            return SkillResult(success=True, data=result, skill_name=entry.name)
        except Exception as e:
            logger.error(f"[SkillBus] Skill '{entry.name}' raised: {e}", exc_info=True)
            return SkillResult(
                success=False,
                message=str(e),
                skill_name=entry.name,
            )

    def list_skills(self) -> list[str]:
        return sorted(self._registry.keys())

    def is_cognitive(self, skill_name: str) -> bool:
        """Returns True if the skill is marked as cognitive/dynamic."""
        entry = self._find(skill_name)
        if not entry:
            return False
        return entry.is_cognitive

    def get_settle_ms(self, skill_name: str) -> int:
        """Returns the settle_ms wait time for a skill (Phase 6)."""
        entry = self._find(skill_name)
        if not entry:
            return 0
        return entry.settle_ms

    def get_trigger_map(self) -> dict[str, str]:
        """Returns {trigger_phrase: skill_name} for LLM system prompt injection."""
        result = {}
        for entry in self._registry.values():
            for t in entry.triggers:
                result[t] = entry.name
        return result

    def get_skill_catalog(self) -> str:
        """Returns a formatted string of all skills, their descriptions, and parameters for the LLM."""
        lines = []
        for name in sorted(self._registry.keys()):
            entry = self._registry[name]
            doc = entry.fn.__doc__ or "No description."
            doc = doc.strip().split("\n")[0]  # Just the first line
            # Instead of full signature (which is always params: dict), we could look at the docstring
            # Or just list the name and doc
            lines.append(f"- {name}: {doc}")
        return "\n".join(lines)

    def register(self, fn: Callable, override: bool = False) -> None:
        """Manually register a skill function (for tests / dynamic loading)."""
        if not getattr(fn, "__skill__", False):
            raise ValueError(f"Function {fn.__name__} is not decorated with @skill")
        entry = _SkillEntry(
            name=fn.__skill_name__,
            fn=fn,
            triggers=fn.__skill_triggers__,
            priority=fn.__skill_priority__,
            category=fn.__skill_category__,
            requires=fn.__skill_requires__,
            is_cognitive=fn.__skill_cognitive__,
            settle_ms=getattr(fn, "__skill_settle_ms__", 0),
        )
        if entry.name in self._registry and not override:
            existing = self._registry[entry.name]
            if entry.priority > existing.priority:
                self._registry[entry.name] = entry
                logger.info(f"[SkillBus] Overrode '{entry.name}' with higher-priority skill")
        else:
            self._registry[entry.name] = entry

    # ── Private ──────────────────────────────────────

    def _walk_package(self, pkg_name: str) -> None:
        try:
            pkg = importlib.import_module(pkg_name)
        except ImportError as e:
            logger.debug(f"[SkillBus] Cannot import '{pkg_name}': {e}")
            return

        pkg_path = getattr(pkg, "__path__", [])
        for _finder, mod_name, _ispkg in pkgutil.walk_packages(
            path=pkg_path, prefix=f"{pkg_name}."
        ):
            try:
                mod = importlib.import_module(mod_name)
                for attr_name in dir(mod):
                    fn = getattr(mod, attr_name)
                    if callable(fn) and getattr(fn, "__skill__", False):
                        self.register(fn)
            except Exception as e:
                logger.warning(f"[SkillBus] Failed to load '{mod_name}': {e}")

    def _find(self, skill_name: str) -> Optional[_SkillEntry]:
        """Find by exact name or partial trigger match."""
        # Exact name match
        if skill_name in self._registry:
            return self._registry[skill_name]
        # Normalized name match (underscores, case)
        normalized = skill_name.lower().replace("-", "_").replace(" ", "_")
        if normalized in self._registry:
            return self._registry[normalized]
        # Trigger-based fuzzy match
        for entry in sorted(
            self._registry.values(), key=lambda e: e.priority, reverse=True
        ):
            for trigger in entry.triggers:
                if skill_name.lower() in trigger.lower() or trigger.lower() in skill_name.lower():
                    return entry
        return None

    @staticmethod
    def _check_requires(entry: _SkillEntry) -> list[str]:
        missing = []
        for pkg in entry.requires:
            try:
                importlib.import_module(pkg)
            except ImportError:
                missing.append(pkg)
        return missing
