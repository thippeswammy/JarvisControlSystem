"""
Preference Memory Layer — Full Implementation
=============================================
Tracks what THIS USER does most. Personalizes Jarvis over time.

Design spec (Part 4, Layer 4):
  - Track command frequency, app frequency, time-of-day patterns
  - PreferenceAnalyzer runs every 10 sessions (reads episodic → updates)
  - Output is a compact context string injected into the LLM prompt

Persistence:
  - memory/preference/habits.md  ← per-command counts
  - memory/preference/style.md   ← inferred style flags (verbose, fast, etc.)

Usage:
    pref = PreferenceMemory()
    pref.record("open display settings", app="settings", skill="navigator")
    ctx = pref.as_llm_context()   # inject into LLM prompt

    # After 10 sessions, run the analyzer
    PreferenceAnalyzer(pref).analyze_from_episodic()
"""
import json
import logging
from collections import Counter
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_MEMORY_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "memory"
_PREF_DIR    = _MEMORY_ROOT / "preference"
_HABITS_FILE = _PREF_DIR / "habits.md"
_STYLE_FILE  = _PREF_DIR / "style.md"


class PreferenceMemory:
    """
    Tracks user behavior patterns and stores them on disk.

    All counters are persisted in habits.md so they survive restarts.
    """

    def __init__(self):
        _PREF_DIR.mkdir(parents=True, exist_ok=True)
        self._command_counts: Counter = Counter()
        self._app_counts: Counter = Counter()
        self._skill_counts: Counter = Counter()
        self._style: dict[str, str] = {
            "confirmation_preference": "ask",       # ask | auto
            "execution_speed": "normal",            # fast | normal
            "verbosity": "normal",                  # quiet | normal | verbose
        }
        self._load()

    # ── Recording ────────────────────────────────────────────────────────────

    def record(self, command: str, app: str = "", skill: str = "") -> None:
        """Record one successful command execution."""
        if command:
            self._command_counts[command.lower().strip()] += 1
        if app:
            self._app_counts[app.lower().strip()] += 1
        if skill:
            self._skill_counts[skill.lower().strip()] += 1

    # ── Queries ──────────────────────────────────────────────────────────────

    def top_commands(self, n: int = 5) -> list[str]:
        return [cmd for cmd, _ in self._command_counts.most_common(n)]

    def top_apps(self, n: int = 3) -> list[str]:
        return [app for app, _ in self._app_counts.most_common(n)]

    def top_skills(self, n: int = 3) -> list[str]:
        return [sk for sk, _, in self._skill_counts.most_common(n)]

    def get_style(self, key: str) -> Optional[str]:
        return self._style.get(key)

    # ── Style inference ──────────────────────────────────────────────────────

    def infer_style_from_patterns(self) -> None:
        """
        Infer user style from accumulated data.
        Called by PreferenceAnalyzer after reading episodic history.

        Heuristics:
          - If top commands are very short (< 3 words avg) → fast user
          - If any "yes yes" / "just do it" pattern appears → auto confirm
        """
        cmds = self.top_commands(10)
        if cmds:
            avg_words = sum(len(c.split()) for c in cmds) / len(cmds)
            if avg_words < 2.5:
                self._style["execution_speed"] = "fast"
            else:
                self._style["execution_speed"] = "normal"

        # Check for impatient patterns
        impatient_patterns = ["yes", "do it", "just", "quick", "fast"]
        all_cmds_lower = " ".join(self.top_commands(20))
        if any(p in all_cmds_lower for p in impatient_patterns):
            self._style["confirmation_preference"] = "auto"

    # ── LLM Context (RAG) ────────────────────────────────────────────────────

    def as_llm_context(self) -> str:
        """
        Compact preference context for LLM injection.
        Token budget: ~50 tokens.
        """
        cmds = self.top_commands(3)
        apps = self.top_apps(3)
        parts: list[str] = []

        if cmds:
            parts.append(f"User's top commands: {', '.join(cmds)}")
        if apps:
            parts.append(f"User's top apps: {', '.join(apps)}")
        style_parts = [
            f"speed={self._style.get('execution_speed', 'normal')}",
            f"confirm={self._style.get('confirmation_preference', 'ask')}",
        ]
        parts.append(f"Style: {', '.join(style_parts)}")

        return "\n".join(parts) if parts else "(no preference data yet)"

    # ── Persistence ──────────────────────────────────────────────────────────

    def save(self) -> None:
        """Persist counters and style to disk."""
        # habits.md
        lines = [
            "# Preference Memory — Habits",
            "",
            "## Command Frequency",
        ]
        for cmd, count in self._command_counts.most_common(20):
            lines.append(f"- `{cmd}` × {count}")
        lines += ["", "## App Frequency"]
        for app, count in self._app_counts.most_common(10):
            lines.append(f"- {app} × {count}")
        lines += ["", "## Skill Frequency"]
        for sk, count in self._skill_counts.most_common(10):
            lines.append(f"- {sk} × {count}")
        _HABITS_FILE.write_text("\n".join(lines), encoding="utf-8")

        # style.md
        style_lines = ["# Preference Memory — Style", ""]
        for k, v in self._style.items():
            style_lines.append(f"- {k}: {v}")
        _STYLE_FILE.write_text("\n".join(style_lines), encoding="utf-8")

        logger.info("[PreferenceMemory] Preferences saved to disk.")

    def _load(self) -> None:
        """Load persisted preferences from habits.md and style.md."""
        if _HABITS_FILE.exists():
            try:
                for line in _HABITS_FILE.read_text(encoding="utf-8").splitlines():
                    if line.startswith("- `") and "× " in line:
                        # e.g. "- `open display settings` × 7"
                        parts = line.split("`")
                        if len(parts) >= 3:
                            cmd = parts[1]
                            count_str = line.split("× ")[-1].strip()
                            if count_str.isdigit():
                                self._command_counts[cmd] = int(count_str)
            except Exception as exc:
                logger.debug(f"[PreferenceMemory] Could not load habits: {exc}")

        if _STYLE_FILE.exists():
            try:
                for line in _STYLE_FILE.read_text(encoding="utf-8").splitlines():
                    if line.startswith("- ") and ": " in line:
                        k, v = line[2:].split(": ", 1)
                        self._style[k.strip()] = v.strip()
            except Exception as exc:
                logger.debug(f"[PreferenceMemory] Could not load style: {exc}")


class PreferenceAnalyzer:
    """
    Reads episodic memory and updates PreferenceMemory.
    Should be called after every 10 sessions (called by main.py session counter).

    Design spec: 'After every 10 sessions, a background thread runs frequency
    analysis on episodic memory → updates preference nodes.'
    """

    def __init__(self, pref: PreferenceMemory):
        self._pref = pref

    def analyze_from_episodic(self, session_dir: Optional[Path] = None) -> None:
        """
        Read all available session logs and update preference counters.
        Idempotent: re-running rebuilds from scratch.
        """
        target_dir = session_dir or (
            _MEMORY_ROOT / "episodic" / "sessions"
        )
        if not target_dir.exists():
            logger.debug("[PreferenceAnalyzer] No episodic sessions to analyze.")
            return

        # Reset counters before rebuild
        self._pref._command_counts.clear()
        self._pref._app_counts.clear()
        self._pref._skill_counts.clear()

        for log_path in sorted(target_dir.glob("*.md")):
            for line in log_path.read_text(encoding="utf-8").splitlines():
                if not line.startswith("- ") or "✅" not in line:
                    continue
                # Parse: "- TIMESTAMP ✅ `CMD` (app=APP, skill=SKILL)"
                parts = line.split("`")
                if len(parts) < 3:
                    continue
                cmd = parts[1]
                app = ""
                skill = ""
                if "app=" in line:
                    try:
                        app = line.split("app=")[1].split(",")[0].split(")")[0].strip()
                    except IndexError:
                        pass
                if "skill=" in line:
                    try:
                        skill = line.split("skill=")[1].split(",")[0].split(")")[0].strip()
                    except IndexError:
                        pass
                self._pref.record(cmd, app=app, skill=skill)

        self._pref.infer_style_from_patterns()
        self._pref.save()
        logger.info(
            f"[PreferenceAnalyzer] Analyzed {len(list(target_dir.glob('*.md')))} sessions. "
            f"Top commands: {self._pref.top_commands(3)}"
        )
