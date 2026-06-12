"""
Goal Understanding Layer
========================
LLM Call 1 in the autonomous cognitive loop.

Translates raw user text into a structured GoalModel that captures
the target end-state, abstract intents, user constraints, and inferred
target applications. This decouples goal extraction from the simpler
NLU intent classification, producing richer semantic output for
downstream GroundingLayer → KnowledgeGapEngine → CapabilityPlanner.
"""

import json
import logging
from typing import Optional

from jarvis.perception.perception_packet import GoalModel

logger = logging.getLogger(__name__)


# ── System Prompt ────────────────────────────────────────

_GOAL_EXTRACTION_PROMPT = (
    "You are a Goal Extraction Engine. Parse the user's utterance into a structured JSON goal model.\n"
    "Output ONLY valid JSON in this exact format:\n"
    "{\n"
    '  "primary_goal": "concise description of the target end-state the user wants to achieve",\n'
    '  "intents": ["abstract_capability_1", "abstract_capability_2"],\n'
    '  "constraints": ["any explicit user constraints or preferences"],\n'
    '  "target_app": "application name if explicitly mentioned or strongly implied, else null",\n'
    '  "required_knowledge": ["any knowledge prerequisites needed to fulfill this goal"],\n'
    '  "confidence": 0.95\n'
    "}\n\n"
    "Rules:\n"
    "- 'intents' should be abstract capability labels, not skill names. Examples:\n"
    "  web_search, content_generation, file_management, app_interaction, system_control,\n"
    "  text_edit, data_analysis, code_synthesis, communication, media_playback\n"
    "- 'constraints' capture explicit user preferences like 'use notepad', 'avoid command-line',\n"
    "  'keep it short', 'in python', etc.\n"
    "- 'target_app' is null if no specific application is mentioned or implied.\n"
    "- 'required_knowledge' lists things the system needs to know to fulfill the goal\n"
    "  (e.g., 'current weather data', 'ROS2 documentation', 'user email address').\n"
    "- 'confidence' is your confidence that you correctly understood the goal (0.0 to 1.0).\n"
    "- For simple commands like 'open notepad', keep the model minimal.\n"
    "- For complex multi-step requests, be thorough in extracting all components.\n"
)


class GoalUnderstandingLayer:
    """
    Parses raw user text → GoalModel via LLM Call 1.

    Usage::

        layer = GoalUnderstandingLayer(router=llm_router)
        goal = layer.understand("Search for ROS2 on GitHub, write a python example in Notepad")
        # → GoalModel(primary_goal="...", intents=["web_search", "content_generation", "app_interaction"], ...)
    """

    def __init__(self, router=None):
        self._router = router

    def understand(
        self,
        text: str,
        app_context: str = "",
        snapshot=None,
    ) -> GoalModel:
        """
        Extract a structured GoalModel from raw user text.

        Parameters
        ----------
        text : str
            The raw user utterance.
        app_context : str
            Currently active application context (e.g. "notepad", "chrome").
        snapshot : ContextSnapshot, optional
            Current system context snapshot for enrichment.

        Returns
        -------
        GoalModel
            Structured goal representation.
        """
        if not text or not text.strip():
            return GoalModel(primary_goal="", confidence=0.0)

        # Fast path: if no LLM router, return a minimal goal model
        if not self._router:
            logger.debug("[GoalUnderstanding] No router — returning minimal GoalModel")
            return self._build_minimal_goal(text, app_context)

        # Build enriched prompt
        prompt_parts = [f"User Utterance: {text}"]
        if app_context:
            prompt_parts.append(f"Currently Active Application: {app_context}")
        if snapshot:
            if hasattr(snapshot, "active_window_title") and snapshot.active_window_title:
                prompt_parts.append(f"Active Window Title: {snapshot.active_window_title}")

        prompt = "\n".join(prompt_parts)

        # Call LLM for goal extraction
        try:
            response_json = self._call_llm_for_goal(prompt)
            if response_json:
                return self._parse_goal_response(response_json, text)
        except Exception as e:
            logger.error(f"[GoalUnderstanding] LLM goal extraction failed: {e}")

        # Fallback to minimal goal model
        return self._build_minimal_goal(text, app_context)

    def _call_llm_for_goal(self, prompt: str) -> Optional[dict]:
        """Call LLM backends for goal extraction JSON."""
        try:
            raw = self._router.call_raw_for_task(
                task="goal_understanding",
                prompt=prompt,
                context=_GOAL_EXTRACTION_PROMPT,
            )
            if raw:
                parsed = self._router._clean_and_parse_json(raw)
                if isinstance(parsed, dict) and "primary_goal" in parsed:
                    return parsed
        except Exception as e:
            logger.error(f"[GoalUnderstanding] call_raw_for_task failed: {e}")
        return None

    def _parse_goal_response(self, data: dict, original_text: str) -> GoalModel:
        """Parse LLM JSON response into a GoalModel."""
        return GoalModel(
            primary_goal=data.get("primary_goal", original_text),
            intents=data.get("intents", []),
            constraints=data.get("constraints", []),
            target_app=data.get("target_app"),
            required_knowledge=data.get("required_knowledge", []),
            confidence=float(data.get("confidence", 0.9)),
        )

    @staticmethod
    def _build_minimal_goal(text: str, app_context: str = "") -> GoalModel:
        """Build a minimal GoalModel from raw text without LLM."""
        text_lower = text.lower().strip()

        # Simple heuristic intent detection for fast-path
        intents = []
        target_app = None

        if text_lower.startswith("open "):
            intents.append("app_interaction")
            target_app = text[5:].strip()
        elif text_lower.startswith("close "):
            intents.append("app_interaction")
            target_app = text[6:].strip()
        elif any(kw in text_lower for kw in ("search", "find", "look up", "google")):
            intents.append("web_search")
        elif any(kw in text_lower for kw in ("write", "type", "draft", "compose")):
            intents.append("content_generation")
            intents.append("text_edit")
        elif any(kw in text_lower for kw in ("set volume", "set brightness", "wifi", "bluetooth")):
            intents.append("system_control")
        else:
            intents.append("general")

        if not target_app and app_context:
            target_app = app_context

        return GoalModel(
            primary_goal=text,
            intents=intents,
            target_app=target_app,
            confidence=0.6,  # Lower confidence for heuristic extraction
        )
