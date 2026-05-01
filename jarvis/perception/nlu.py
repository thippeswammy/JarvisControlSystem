"""
NLU — Natural Language Understanding
=====================================
Parses raw utterances into structured intents + entities.
Replaces the v1 IntentEngine (Jarvis/core/intent_engine.py).

Key changes from v1:
  - No OPEN_SETTINGS / CLOSE_SETTINGS special cases → generic open_app
  - Compound command detection ("open notepad AND type hello")
  - Sub-location extraction ("settings wifi" → app=settings, sub=wifi)
  - Returns PerceptionPacket (not a plain string)
"""

import logging
import re
from typing import Optional

from jarvis.perception.perception_packet import Utterance, PerceptionPacket

logger = logging.getLogger(__name__)

# ── Intent patterns (order matters — first match wins) ──────────
_INTENT_PATTERNS = [
    # Session
    (r"\b(hi|hello|hey|wake up|activate)\s+jarvis\b",         "session_activate",   {}),
    (r"\b(bye|goodbye|stop|deactivate|sleep|close)\s+jarvis\b","session_deactivate", {}),
    (r"^(status|health|how are you)$",                         "system_status",      {}),
    (r"\b(jarvis\s+status|system\s+status)\b",                 "system_status",      {}),

    # Volume
    (r"\b(set|change|put)\s+(volume|sound)\s+(?:to\s+)?(\d+)", "set_volume",    {"level": 3}),
    (r"\b(mute)\b",                                            "set_volume",    {"mute": True}),
    (r"\b(unmute)\b",                                          "set_volume",    {"mute": False}),
    (r"\bvolume\s+(?:up|increase)\b",                          "set_volume",    {"action": "up"}),
    (r"\bvolume\s+(?:down|decrease|lower)\b",                  "set_volume",    {"action": "down"}),

    # Brightness
    (r"\b(set|change)\s+brightness\s+(?:to\s+)?(\d+)",        "set_brightness", {"level": 2}),

    # Power
    (r"\b(shutdown|shut down|power off)\b",                    "power_action",  {"action": "shutdown"}),
    (r"\b(restart|reboot)\b",                                  "power_action",  {"action": "restart"}),
    (r"\b(sleep|hibernate)\b",                                 "power_action",  {"action": "sleep"}),

    # Window management
    (r"\b(minimize|minimise)\b",                               "minimize_window", {}),
    (r"\b(maximize|maximise|fullscreen|full\s*screen)\b",      "maximize_window", {}),
    (r"\bsnap\s+(left|right)\b",                               "snap_window",   {"direction": 1}),
    (r"\b(switch|alt.?tab)\b",                                 "switch_window", {}),
    (r"\b(close|quit|exit)\s+(.+)",                            "close_app",     {"target": 2}),

    # Navigation (before open_app — "go to wifi" should be navigate, not open)
    (r"\b(go\s+to|navigate\s+to|navigate)\s+(.+)",            "navigate_location", {"target": 2}),

    # App launching
    (r"\b(open|launch|start|run)\s+(.+)",                      "open_app",      {"target": 2}),

    # Keyboard
    (r"\bpress\s+(.+)",                                        "press_key",     {"key": 1}),
    (r"\bhold\s+(.+)",                                         "press_key",     {"key": 1}),
    (r"\b(type|write)\s+(.+)",                                 "type_text",     {"text": 2}),

    # Search
    (r"\b(search|google|find|look\s+up)\s+(?:for\s+)?(.+)",   "search_web",    {"query": 2}),
    (r"\b(click)\s+(.+)",                                      "click_element", {"label": 2}),

    # Scroll
    (r"\bscroll\s+(down|up)\b",                                "scroll_page",   {"direction": 1}),
]

# Words and symbols that signal compound commands
_COMPOUND_SEPARATORS = re.compile(
    r"\s*(?:and\s+(?:then\s+)?|then\s+|after\s+that\s+|also\s+|,)\s*",
    re.IGNORECASE,
)

# Settings sub-location extraction
_SETTINGS_SUB = re.compile(
    r"\bsettings?\s+(.+)|(.+)\s+settings?\b",
    re.IGNORECASE,
)


class NLU:
    """
    Parses raw text → PerceptionPacket.

    Usage:
        nlu = NLU()
        packet = nlu.parse(Utterance("open display settings"))
        # packet.intent == "open_app"
        # packet.entities == {"target": "settings"}
        # packet.sub_location == "display"
    """

    def parse(self, utterance: Utterance, app_context: str = "") -> PerceptionPacket:
        text = utterance.text.strip()
        text_lower = text.lower()

        # Detect compound commands first
        parts = _COMPOUND_SEPARATORS.split(text_lower)
        if len(parts) > 1:
            sub_commands = []
            for part in parts:
                part = part.strip()
                if part:
                    intent, entities = self._match_intent(part)
                    sub_commands.append({"intent": intent, "entities": entities, "text": part})

            packet = PerceptionPacket(
                utterance=utterance,
                intent=sub_commands[0]["intent"] if sub_commands else "unknown",
                entities=sub_commands[0]["entities"] if sub_commands else {},
                app_context=app_context,
                compound=True,
                sub_commands=sub_commands,
            )
            logger.info(f"[NLU] Compound: {[c['intent'] for c in sub_commands]}")
            return packet

        # Single command
        intent, entities = self._match_intent(text_lower)

        # Sub-location: "open settings wifi" → app=settings, sub=wifi
        sub_location = ""
        if intent == "open_app":
            target = entities.get("target", "")
            if "setting" in target:
                sub_location = self._extract_settings_sub(target)
                entities["target"] = "settings"
                if sub_location:
                    entities["sub_location"] = sub_location
        elif intent == "navigate_location":
            target = entities.get("target", "")
            if "setting" in target:
                sub_location = self._extract_settings_sub(target)

        packet = PerceptionPacket(
            utterance=utterance,
            intent=intent,
            entities=entities,
            app_context=app_context,
            sub_location=sub_location,
        )
        logger.info(f"[NLU] '{text}' → intent={intent}, entities={entities}")
        return packet

    # ── Private ──────────────────────────────────────

    def _match_intent(self, text: str) -> tuple[str, dict]:
        for pattern, intent, entity_map in _INTENT_PATTERNS:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                entities = self._extract_entities(m, entity_map)
                return intent, entities
        return "unknown", {"raw": text}

    @staticmethod
    def _extract_entities(match: re.Match, entity_map: dict) -> dict:
        entities = {}
        for key, group_or_val in entity_map.items():
            if isinstance(group_or_val, int):
                try:
                    entities[key] = match.group(group_or_val).strip()
                except (IndexError, AttributeError):
                    pass
            elif isinstance(group_or_val, bool):
                entities[key] = group_or_val
            else:
                entities[key] = group_or_val
        return entities

    @staticmethod
    def _extract_settings_sub(target: str) -> str:
        """Extract sub-location from 'settings wifi' or 'wifi settings'."""
        target_clean = re.sub(r"\bsettings?\b", "", target, flags=re.IGNORECASE).strip()
        return target_clean if target_clean else ""
