"""
Jarvis Intent Engine
====================
Parses natural language text into a structured Intent object.

Design principles:
- No hardcoded if/elif chains — uses vocabulary dicts
- Extensible: add new ActionType + phrases in ACTION_VOCABULARY only
- Fuzzy matching: "launch chrome", "get chrome", "open chrome" all work
- Context-aware: knows active app to resolve pronouns ("close it", "go back")
"""

import re
import logging
from enum import Enum, auto
from dataclasses import dataclass, field
from difflib import get_close_matches
from typing import Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  Action Types
# ─────────────────────────────────────────────
class ActionType(Enum):
    # Session control
    ACTIVATE_JARVIS   = auto()   # "hi jarvis"
    DEACTIVATE_JARVIS = auto()   # "close jarvis"

    # App lifecycle
    OPEN_APP          = auto()   # "open chrome"
    CLOSE_APP         = auto()   # "close notepad"
    SWITCH_APP        = auto()   # "switch to chrome"

    # Typing & keyboard
    TYPING_MODE_ON    = auto()   # "start typing"
    TYPING_MODE_OFF   = auto()   # "stop typing"
    TYPE_TEXT         = auto()   # "type hello world"
    PRESS_KEY         = auto()   # "press enter"
    HOLD_KEY          = auto()   # "hold ctrl"
    RELEASE_KEY       = auto()   # "release ctrl"

    # System controls
    SET_VALUE         = auto()   # "set volume to 80"
    INCREASE          = auto()   # "increase brightness"
    DECREASE          = auto()   # "decrease volume"

    # Window management
    MINIMIZE          = auto()   # "minimize window"
    MAXIMIZE          = auto()   # "maximize window"
    CLOSE_WINDOW      = auto()   # "close window"
    SNAP_LEFT         = auto()   # "snap window left"
    SNAP_RIGHT        = auto()   # "snap window right"
    SWITCH_WINDOW     = auto()   # "next window"

    # UI Navigation (in-app / Explorer)
    CLICK_ELEMENT     = auto()   # "click save button"
    NAVIGATE_MENU     = auto()   # "go to file then save as"
    NAVIGATE_LOCATION = auto()   # "go to documents" / "open c drive"
    SCROLL            = auto()   # "scroll down"
    TYPE_IN_FIELD     = auto()   # "type in search box hello"

    # Windows Search
    SEARCH            = auto()   # "search for python"

    # Settings
    OPEN_SETTINGS     = auto()   # "open settings" / "open wifi settings"
    CLOSE_SETTINGS    = auto()   # "close settings"

    # App scanner
    SCAN_APPS         = auto()   # "rescan apps"

    # Fallback
    UNKNOWN           = auto()


# ─────────────────────────────────────────────
#  Intent Dataclass
# ─────────────────────────────────────────────
@dataclass
class Intent:
    action: ActionType
    target: str = ""               # Primary target: app name, element name, setting, path
    target_extra: str = ""         # Secondary target: e.g. field name in "type in <field> <text>"
    params: dict = field(default_factory=dict)   # Numeric values, directions, flags
    confidence: float = 1.0        # Matching confidence 0.0 – 1.0
    raw: str = ""                  # Original unmodified input

    def __repr__(self):
        return (f"Intent(action={self.action.name}, target={self.target!r}, "
                f"params={self.params}, confidence={self.confidence:.2f})")


# ─────────────────────────────────────────────
#  Action Vocabulary — ONLY EDIT THIS to add phrases
# ─────────────────────────────────────────────
class _Vocab:
    """
    Maps ActionType → list of trigger phrases (lowercase).
    Multi-word phrases are matched first (longest match wins).
    """
    MAP: dict[ActionType, list[str]] = {
        ActionType.ACTIVATE_JARVIS: [
            "hi jarvis", "hey jarvis", "jarvis", "hello jarvis",
            "start jarvis", "wake up jarvis", "activate jarvis",
        ],
        ActionType.DEACTIVATE_JARVIS: [
            "close jarvis", "stop jarvis", "jarvis stop", "jarvis close",
            "deactivate jarvis", "goodbye jarvis", "sleep jarvis",
        ],
        ActionType.OPEN_APP: [
            "open", "launch", "start", "run", "load", "get", "bring up",
            "execute", "fire up",
        ],
        ActionType.CLOSE_APP: [
            "close", "exit", "quit", "kill", "terminate", "shut down",
            "force close", "force quit",
        ],
        ActionType.SWITCH_APP: [
            "switch to", "switch app to", "go to app", "bring",
        ],
        ActionType.TYPING_MODE_ON: [
            "start typing", "typing start", "activate typing",
            "typing activate", "begin typing", "enable typing",
        ],
        ActionType.TYPING_MODE_OFF: [
            "stop typing", "typing stop", "deactivate typing",
            "typing deactivate", "end typing", "disable typing",
        ],
        ActionType.TYPE_TEXT: [
            "type", "write", "input", "enter text",
        ],
        ActionType.PRESS_KEY: [
            "press", "hit key", "key press", "push",
        ],
        ActionType.HOLD_KEY: [
            "hold", "hold down", "hold key", "keydown", "keep pressed",
        ],
        ActionType.RELEASE_KEY: [
            "release", "release key", "let go", "key up",
        ],
        ActionType.SET_VALUE: [
            "set", "change to", "put to", "make it",
        ],
        ActionType.INCREASE: [
            "increase", "raise", "turn up", "boost", "higher",
            "more", "louder", "brighter",
        ],
        ActionType.DECREASE: [
            "decrease", "lower", "turn down", "reduce", "less",
            "quieter", "dimmer",
        ],
        ActionType.MINIMIZE: [
            "minimize", "minimise", "hide window", "make small",
        ],
        ActionType.MAXIMIZE: [
            "maximize", "maximise", "fullscreen", "full screen",
            "make full", "make big",
        ],
        ActionType.CLOSE_WINDOW: [
            "close window", "close this window", "close active window",
        ],
        ActionType.SNAP_LEFT: [
            "snap left", "move left", "window left", "snap window left",
            "move window left",
        ],
        ActionType.SNAP_RIGHT: [
            "snap right", "move right", "window right", "snap window right",
            "move window right",
        ],
        ActionType.SWITCH_WINDOW: [
            "next window", "switch window", "switch windows",
            "alt tab", "shift window",
        ],
        ActionType.CLICK_ELEMENT: [
            "click", "tap", "select", "choose", "click on", "press on",
            "click the", "click button",
        ],
        ActionType.NAVIGATE_MENU: [
            "go to menu", "navigate menu", "open menu",
        ],
        ActionType.NAVIGATE_LOCATION: [
            "navigate to", "go to", "open folder", "open drive",
            "open location", "go to folder", "open path",
        ],
        ActionType.SCROLL: [
            "scroll down", "scroll up", "scroll", "page down", "page up",
            "scroll left", "scroll right",
        ],
        ActionType.TYPE_IN_FIELD: [
            "type in", "write in", "enter in", "input in", "fill in",
            "put in",
        ],
        ActionType.SEARCH: [
            "search for", "search", "find", "look for", "windows search",
        ],
        ActionType.OPEN_SETTINGS: [
            "open settings", "open setting", "go to settings",
            "settings", "setting",
        ],
        ActionType.CLOSE_SETTINGS: [
            "close settings", "close setting",
        ],
        ActionType.SCAN_APPS: [
            "rescan apps", "refresh apps", "scan for programs", "find new apps",
            "update app list", "refresh application list", "rescan applications",
        ],
    }

    # Sorted: longest phrases first so "switch to" beats "switch"
    @classmethod
    def get_sorted(cls) -> list[tuple[ActionType, str]]:
        pairs = []
        for action, phrases in cls.MAP.items():
            for phrase in phrases:
                pairs.append((action, phrase))
        return sorted(pairs, key=lambda x: len(x[1]), reverse=True)


# Pre-build sorted vocab at import time
_SORTED_VOCAB: list[tuple[ActionType, str]] = _Vocab.get_sorted()

# Targets that map to system properties (not apps)
_SYSTEM_TARGETS = {
    "volume", "brightness", "screen", "display", "audio", "sound", "wifi",
    "bluetooth", "battery", "network",
}

# Direction words extracted into params
_DIRECTION_MAP = {
    "up": "up", "down": "down", "left": "left", "right": "right",
}

# Scroll direction normalization
_SCROLL_DIRECTION = {
    "scroll down": "down", "scroll up": "up", "page down": "down",
    "page up": "up", "scroll left": "left", "scroll right": "right",
    "scroll": "down",   # default
}


# ─────────────────────────────────────────────
#  Helper: extract numbers from text
# ─────────────────────────────────────────────
def _extract_numbers(text: str) -> list[int]:
    return [int(n) for n in re.findall(r"\d+", text)]


# ─────────────────────────────────────────────
#  Intent Engine
# ─────────────────────────────────────────────
class IntentEngine:
    """
    Parses a text string into a structured Intent.

    Usage:
        engine = IntentEngine()
        intent = engine.parse("open chrome", context)
        # Intent(action=OPEN_APP, target='chrome', ...)
    """

    def parse(self, text: str, context=None) -> Intent:
        raw = text
        text = text.lower().strip()

        if not text:
            return Intent(action=ActionType.UNKNOWN, raw=raw)

        # ── 1. Try all vocabulary phrases (longest-first match) ──
        matched_action: Optional[ActionType] = None
        matched_phrase: str = ""

        for action, phrase in _SORTED_VOCAB:
            if text.startswith(phrase):
                matched_action = action
                matched_phrase = phrase
                break
            # Also check if phrase is contained anywhere in text (for mid-sentence)
            if f" {phrase} " in f" {text} ":
                matched_action = action
                matched_phrase = phrase
                # Don't break — keep looking for longer match at start

        # If nothing matched at start, look for best embedded phrase
        if not matched_action:
            for action, phrase in _SORTED_VOCAB:
                if phrase in text:
                    matched_action = action
                    matched_phrase = phrase
                    break

        if not matched_action:
            logger.debug(f"No action matched for: {text!r}")
            return Intent(action=ActionType.UNKNOWN, raw=raw, confidence=0.0)

        # ── 2. Extract the target (what comes after the action phrase) ──
        remainder = text[text.find(matched_phrase) + len(matched_phrase):].strip()

        # Remove filler words
        for filler in ["the ", "a ", "an ", "some ", "please ", "now "]:
            if remainder.startswith(filler):
                remainder = remainder[len(filler):].strip()

        target = remainder
        params: dict = {}
        target_extra = ""

        # ── 3. Action-specific parameter extraction ──

        if matched_action in (ActionType.INCREASE, ActionType.DECREASE):
            nums = _extract_numbers(target)
            if nums:
                params["amount"] = nums[0]
            # Remove numbers from target string
            target = re.sub(r"\d+", "", target).strip()
            # Detect subject: "volume" or "brightness"
            for sys_tgt in _SYSTEM_TARGETS:
                if sys_tgt in target:
                    target = sys_tgt
                    break

        elif matched_action == ActionType.SET_VALUE:
            nums = _extract_numbers(target)
            if nums:
                params["value"] = nums[0]
            # Detect "to <N>" pattern
            to_match = re.search(r"\bto\s+(\d+)", target)
            if to_match:
                params["value"] = int(to_match.group(1))
            # Detect system subject
            for sys_tgt in _SYSTEM_TARGETS:
                if sys_tgt in target:
                    target = sys_tgt
                    break

        elif matched_action == ActionType.SCROLL:
            for phrase, direction in _SCROLL_DIRECTION.items():
                if phrase in text:
                    params["direction"] = direction
                    break
            nums = _extract_numbers(target)
            params["amount"] = nums[0] if nums else 3

        elif matched_action == ActionType.TYPE_IN_FIELD:
            # "type in search box hello world" → field="search box", text="hello world"
            # Split on known field indicators
            parts = target.split(None, 2)
            if len(parts) >= 2:
                target_extra = parts[0] + (" " + parts[1] if len(parts) > 1 else "")
                # heuristic: first 1-2 words = field name, rest = text
                target = parts[0] if len(parts) > 1 else target
                if len(parts) > 2:
                    params["text"] = parts[2]
                elif len(parts) == 2:
                    params["text"] = parts[1]

        elif matched_action == ActionType.NAVIGATE_LOCATION:
            # Expand common shorthand locations
            _QUICK = {
                "documents": "~/Documents", "downloads": "~/Downloads",
                "desktop": "~/Desktop", "pictures": "~/Pictures",
                "videos": "~/Videos", "music": "~/Music",
                "this pc": "shell:MyComputerFolder",
                "c drive": "C:\\", "c:": "C:\\",
                "d drive": "D:\\", "d:": "D:\\",
                "e drive": "E:\\", "e:": "E:\\",
            }
            for key, path in _QUICK.items():
                if key in target:
                    params["resolved_path"] = path
                    break

        elif matched_action == ActionType.PRESS_KEY:
            # Remove "key" suffix noise: "press enter key" → target="enter"
            target = re.sub(r"\bkey\b|\bkeys\b", "", target).strip()

        elif matched_action == ActionType.NAVIGATE_MENU:
            # "file then save as" → ["file", "save as"]
            menu_parts = re.split(r"\bthen\b|\band\b|>|→|/", target)
            params["menu_path"] = [p.strip() for p in menu_parts if p.strip()]

        # ── 4. Build confidence ──
        confidence = 1.0 if text.startswith(matched_phrase) else 0.8

        intent = Intent(
            action=matched_action,
            target=target,
            target_extra=target_extra,
            params=params,
            confidence=confidence,
            raw=raw,
        )
        logger.debug(f"Parsed: {intent}")
        return intent


# ─────────────────────────────────────────────
#  Quick smoke-test
# ─────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    engine = IntentEngine()
    tests = [
        "hi jarvis",
        "open chrome",
        "launch notepad",
        "close jarvis",
        "set volume to 80",
        "increase brightness by 20",
        "decrease volume 10",
        "start typing",
        "stop typing",
        "press enter",
        "hold ctrl",
        "click save button",
        "go to documents",
        "navigate to C drive",
        "scroll down 5",
        "type in search box hello world",
        "open settings wifi",
        "rescan apps",
        "search for python tutorial",
        "minimize window",
        "switch window",
        "snap left",
    ]
    for t in tests:
        i = engine.parse(t)
        print(f"  {t!r:40s} → {i}")
