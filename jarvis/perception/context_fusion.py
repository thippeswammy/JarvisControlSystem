"""
Context Fusion Layer
====================
Blends conversation memory, active window states, and last action cues to resolve
pronouns and ambiguous commands (e.g., "close it", "type in it", "switch back").
"""

import logging
import re
from typing import Optional
from jarvis.perception.perception_packet import PerceptionPacket, ContextSnapshot

logger = logging.getLogger(__name__)

class ContextFusionLayer:
    """
    Context Fusion Layer
    ====================
    Identifies commands containing ambiguous pronouns (e.g. 'it', 'this', 'them')
    and routes them straight to the cognitive layer (LLM) for reference resolution.
    
    Uses zero `re.compile` regular expressions, relying on clean Python string checks.
    """

    def fuse(self, packet: PerceptionPacket, snapshot: Optional[ContextSnapshot] = None) -> PerceptionPacket:
        """
        Detects ambiguous pronouns. If found, forces routing to cognitive layer.
        """
        text_lower = packet.text.lower()
        words = text_lower.split()

        # Pronouns indicating an ambiguous coreference target
        ambiguous_pronouns = ["it", "them", "this", "that", "the app", "the window", "previous", "back"]

        is_ambiguous = False
        for pronoun in ambiguous_pronouns:
            # Check for exact word matches or substring containment with surrounding whitespace
            if pronoun in words or f" {pronoun} " in f" {text_lower} ":
                is_ambiguous = True
                break

        if is_ambiguous:
            logger.info(f"[ContextFusion] Ambiguous reference detected in command: {packet.text!r}. Routing to LLM for cognitive resolution.")
            packet.intent = "llm_route"

        return packet
