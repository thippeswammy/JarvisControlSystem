"""
NLU — Natural Language Understanding
=====================================
Parses raw utterances into structured intents + entities using LLM semantic parsing.
Replaces the old regex-based engine to handle hypotheticals and complex conversational flow safely.
"""

import logging
import json
from typing import Optional

from jarvis.perception.perception_packet import Utterance, PerceptionPacket

logger = logging.getLogger(__name__)

class NLU:
    """
    Parses raw text → PerceptionPacket using LLMRouter.
    """

    def __init__(self, router=None):
        self._router = router

    def parse(self, utterance: Utterance, app_context: str = "") -> PerceptionPacket:
        text = utterance.text.strip()
        text_lower = text.lower()

        default_packet = PerceptionPacket(
            utterance=utterance,
            intent="unknown",
            entities={},
            app_context=app_context,
            intent_category="EXECUTION",
            intent_confidence=1.0,
            entity_confidence=1.0
        )

        if not self._router:
            logger.warning("[NLU] No router provided, falling back to basic open_app heuristic.")
            if text_lower.startswith("open "):
                default_packet.intent = "open_app"
                default_packet.entities = {"target": text[5:].strip()}
            return default_packet

        system_prompt = (
            "You are an NLU intent parser. You must parse the user's utterance into a single valid JSON object and nothing else.\n"
            "Output JSON format:\n"
            "{\n"
            '  "intent": "open_app" | "close_app" | "type_text" | "power_action" | "chat_reply" | "log_analysis",\n'
            '  "entities": {"target": "name"} or {"text": "some text"},\n'
            '  "intent_category": "EXECUTION" | "EDUCATIONAL" | "HYPOTHETICAL" | "CAPABILITY" | "TEXT_ANALYSIS",\n'
            '  "compound": false,\n'
            '  "sub_commands": []\n'
            "}\n\n"
            "Rules:\n"
            "- 'intent_category' must accurately reflect if the user wants to execute a command (EXECUTION) vs asking how to do something (EDUCATIONAL), asking a hypothetical 'what if' (HYPOTHETICAL), or asking about your features (CAPABILITY).\n"
            "- If the utterance is not execution (e.g. hypothetical), set intent to 'chat_reply'.\n"
            "- If it contains multiple commands (like 'open notepad and type hello'), set compound to true and fill sub_commands array with the individual commands following the same format.\n"
            "- Prioritize quoted strings when extracting entities.\n"
            "- Differentiate opening an application (intent open_app) from executing actions inside it (like clicking, typing, or opening sub-features). Utterances like 'In calculator open the history' or 'Press history button in calculator' are not open_app requests; they are context-dependent actions.\n"
            "- CRITICAL: If the command is context-dependent, relative, contains pronouns ('it', 'this', 'them', 'this window'), refers to a sub-feature (like 'open history' or 'show logs'), or is ambiguous given the App Context, set the intent to 'llm_route' (with category 'EXECUTION') to route it to the cognitive planner for dynamic resolution."
        )

        try:
            # We will use the router's decision logic but wrapped for JSON extraction
            # We can use the primary backend's _call_llm_closed_loop directly for raw generation, or route it safely.
            backends = [self._router._primary, self._router._fallback, self._router._emergency]
            response_json = None
            for backend in backends:
                if not backend: continue
                try:
                    raw = backend._call_llm_closed_loop(prompt=f"App Context: {app_context}\nUtterance: {text}", context=system_prompt)
                    # parse json
                    response_json = self._router._clean_and_parse_json(raw)
                    if isinstance(response_json, dict) and "intent_category" in response_json:
                        break
                except Exception as e:
                    logger.debug(f"[NLU] Backend {backend.name} failed: {e}")
            
            if not response_json:
                return default_packet

            intent = response_json.get("intent", "unknown")
            entities = response_json.get("entities", {})
            intent_category = response_json.get("intent_category", "EXECUTION")
            compound = response_json.get("compound", False)
            sub_commands = response_json.get("sub_commands", [])

            packet = PerceptionPacket(
                utterance=utterance,
                intent=intent,
                entities=entities,
                app_context=app_context,
                compound=compound,
                sub_commands=sub_commands,
                intent_category=intent_category,
                intent_confidence=0.9,
                entity_confidence=0.9
            )
            
            logger.info(f"[NLU] '{text}' → category={intent_category}, intent={intent}, entities={entities}")
            return packet

        except Exception as e:
            logger.error(f"[NLU] Error parsing utterance with LLM: {e}")
            return default_packet
