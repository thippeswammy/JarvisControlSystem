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
    """Resolves conversational coreferences and blends dynamic history context."""
    
    PRONOUN_PATTERNS = [
        re.compile(r"\b(it|them|this|that|the app|the window)\b", re.I)
    ]
    
    ACTION_PATTERNS = [
        (re.compile(r"\b(close|quit|exit)\s+(it|them|this|that|the app|the window)\b", re.I), "close_app"),
        (re.compile(r"\b(maximize|maximise|fullscreen)\s+(it|them|this|that|the app|the window)\b", re.I), "maximize_window"),
        (re.compile(r"\b(minimize|minimise)\s+(it|them|this|that|the app|the window)\b", re.I), "minimize_window"),
        (re.compile(r"\b(focus|activate|switch to)\s+(it|them|this|that|the app|the window)\b", re.I), "activate_window"),
    ]

    def fuse(self, packet: PerceptionPacket, snapshot: Optional[ContextSnapshot] = None) -> PerceptionPacket:
        """
        Processes the PerceptionPacket, substituting pronouns and coreferences
        based on active snapshot app or episodic last active application.
        """
        if not snapshot:
            return packet

        original_text = packet.text
        active_app = snapshot.active_app or ""
        
        # If no active app is found, fallback to standard lookup
        if not active_app and hasattr(snapshot, "active_window_title") and snapshot.active_window_title:
            from jarvis.perception.context_harvester import ContextHarvester
            active_app = ContextHarvester._infer_app_id(snapshot.active_window_title)

        if not active_app:
            return packet

        # 1. Direct regex replacement on raw text if pronouns exist
        resolved_text = original_text
        has_pronoun = False
        for pattern in self.PRONOUN_PATTERNS:
            if pattern.search(original_text):
                has_pronoun = True
                resolved_text = pattern.sub(active_app, original_text)

        if has_pronoun and resolved_text != original_text:
            logger.info(f"[ContextFusion] Resolved command: {original_text!r} -> {resolved_text!r} (using active app: {active_app!r})")
            packet.override_prompt = resolved_text
            packet.app_context = active_app
            
            # Enrich entities if targets are pronouns
            if "target" in packet.entities and packet.entities["target"] in ["it", "them", "this", "that", "active", ""]:
                packet.entities["target"] = active_app
            if "app" in packet.entities and packet.entities["app"] in ["it", "them", "this", "that", "active", ""]:
                packet.entities["app"] = active_app

        # 2. Check for action coreferences (e.g. just saying "close" or "close it")
        for pattern, intent in self.ACTION_PATTERNS:
            if pattern.search(original_text):
                logger.info(f"[ContextFusion] Direct action coreference matched: {intent} on target: {active_app}")
                packet.intent = intent
                packet.entities["target"] = active_app
                break

        return packet
