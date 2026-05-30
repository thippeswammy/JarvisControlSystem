"""
Intent Safety Layer
===================
Classifies if an incoming query is informational/educational/discussion
(e.g., "How do I open settings?") and intercepts it to prevent accidental command execution.
"""

import logging
import re
from jarvis.perception.perception_packet import PerceptionPacket

logger = logging.getLogger(__name__)

class IntentSafetyLayer:
    """Protects against accidental execution from informational queries."""
    
    DISCUSSION_PATTERNS = [
        re.compile(r"^\s*(how\s+(?:do|can|to|should|would)|what\s+is|why\s+does|explain|teach|tell\s+me\s+about|how\s+to\s+use|can\s+you(\s+explain)?|if\s+i\s+asked\s+you|summarize|translate|analyze)\b", re.I),
        re.compile(r"\b(how\s+do\s+i|how\s+can\s+i|what\s+does|how\s+does)\b", re.I)
    ]

    def check_safety(self, packet: PerceptionPacket) -> PerceptionPacket:
        """
        Intercepts educational / discussion text, setting safe_mode and overriding
        the intent to prevent executable plan generation.
        """
        text = packet.text.strip().lower()

        is_discussion = False
        for pattern in self.DISCUSSION_PATTERNS:
            if pattern.search(text):
                is_discussion = True
                break

        if is_discussion:
            logger.info(f"[IntentSafety] Intercepted discussion/educational query: {packet.text!r}")
            packet.safe_mode = True
            packet.override_prompt = f"The user is asking an informational/educational question: '{packet.text}'. Answer their question clearly and conversationally. Do NOT generate any desktop execution steps or commands."
            
        return packet
