"""
Grounding Layer
===============
Resolves coreferences, pronouns, and ambiguous references in a GoalModel
using conversation history, episodic memory, and active window context.

This extends the existing ContextFusionLayer logic (which only detects ambiguity
and routes to LLM) by performing actual resolution of references like "it",
"that", "the app", "again", "previous", "back" → concrete target entities.

In the cognitive loop pipeline:
    NLU → GoalUnderstanding → **GroundingLayer** → KnowledgeGapEngine → CapabilityPlanner
"""

import logging
from typing import Optional, List

from jarvis.perception.perception_packet import GoalModel, ContextSnapshot

logger = logging.getLogger(__name__)

# Pronouns and references that indicate an ambiguous coreference target
_AMBIGUOUS_PRONOUNS = frozenset([
    "it", "them", "this", "that", "those", "these",
    "the app", "the window", "the file", "the document",
    "previous", "back", "again", "last one", "same",
])

# Temporal references that map to recent actions
_TEMPORAL_REFERENCES = frozenset([
    "again", "once more", "repeat", "redo", "same thing",
    "do that again", "one more time",
])


class GroundingLayer:
    """
    Resolves pronouns and ambiguous references in a GoalModel.

    Uses three resolution strategies (in order of priority):
      1. Active window context — resolves "it"/"the app" to the foreground app
      2. Episodic memory — resolves "again"/"previous" to the last executed action
      3. LLM-assisted resolution — falls back to cognitive layer for complex coreferences

    Usage::

        grounding = GroundingLayer(episodic=episodic_memory)
        grounded_goal = grounding.ground(goal_model, snapshot=ctx_snapshot)
    """

    def __init__(self, episodic=None, router=None):
        """
        Parameters
        ----------
        episodic : EpisodicMemory, optional
            Episodic memory for recent action lookups.
        router : LLMRouter, optional
            LLM router for complex coreference resolution.
        """
        self._episodic = episodic
        self._router = router

    def ground(
        self,
        goal: GoalModel,
        snapshot: Optional[ContextSnapshot] = None,
        conversation_history: Optional[List[str]] = None,
    ) -> GoalModel:
        """
        Resolve all ambiguous references in the GoalModel.

        Parameters
        ----------
        goal : GoalModel
            The GoalModel from GoalUnderstandingLayer.
        snapshot : ContextSnapshot, optional
            Current system context (active app, window title).
        conversation_history : list of str, optional
            Recent conversation turns for context.

        Returns
        -------
        GoalModel
            Goal with resolved references populated in `resolved_references`.
        """
        text = goal.primary_goal.lower()
        words = text.split()
        resolutions = {}

        # 1. Detect which pronouns/references are present
        detected_pronouns = []
        for pronoun in _AMBIGUOUS_PRONOUNS:
            if pronoun in words or f" {pronoun} " in f" {text} ":
                detected_pronouns.append(pronoun)

        if not detected_pronouns:
            logger.debug("[GroundingLayer] No ambiguous references detected")
            return goal

        logger.info(f"[GroundingLayer] Detected ambiguous references: {detected_pronouns}")

        # 2. Resolve via active window context
        if snapshot:
            window_resolutions = self._resolve_from_context(detected_pronouns, snapshot)
            resolutions.update(window_resolutions)

        # 3. Resolve temporal references via episodic memory
        temporal_refs = [p for p in detected_pronouns if p in _TEMPORAL_REFERENCES]
        if temporal_refs and self._episodic:
            temporal_resolutions = self._resolve_from_episodic(temporal_refs)
            resolutions.update(temporal_resolutions)

        # 4. Resolve remaining unresolved references
        unresolved = [p for p in detected_pronouns if p not in resolutions]
        if unresolved and self._router:
            llm_resolutions = self._resolve_via_llm(
                unresolved, goal.primary_goal, snapshot, conversation_history
            )
            resolutions.update(llm_resolutions)

        # 5. Apply resolutions to the goal model
        if resolutions:
            goal.resolved_references = resolutions
            goal.primary_goal = self._apply_resolutions(goal.primary_goal, resolutions)

            # Update target_app if resolved
            if not goal.target_app:
                for pronoun, resolved in resolutions.items():
                    if pronoun in ("it", "the app", "the window", "this"):
                        goal.target_app = resolved
                        break

            logger.info(f"[GroundingLayer] Resolved references: {resolutions}")

        return goal

    def _resolve_from_context(
        self, pronouns: List[str], snapshot: ContextSnapshot
    ) -> dict:
        """Resolve pronouns using the active window/app context."""
        resolutions = {}
        active_app = snapshot.active_app or ""
        active_title = snapshot.active_window_title or ""

        # Direct app reference pronouns
        app_pronouns = {"it", "the app", "the window", "this", "that"}
        for pronoun in pronouns:
            if pronoun in app_pronouns and active_app:
                resolutions[pronoun] = active_app
                logger.debug(f"[GroundingLayer] '{pronoun}' → '{active_app}' (from active window)")

        return resolutions

    def _resolve_from_episodic(self, temporal_refs: List[str]) -> dict:
        """Resolve temporal references using episodic memory."""
        resolutions = {}

        try:
            # Get the most recent successful action from episodic memory
            recent = self._episodic.as_llm_context()
            if recent:
                # Extract the last command from episodic context
                lines = recent.strip().split("\n")
                for line in reversed(lines):
                    line = line.strip()
                    if line and "→" in line:
                        # Typical format: "command → SUCCESS (skill: open_app)"
                        last_action = line.split("→")[0].strip()
                        for ref in temporal_refs:
                            resolutions[ref] = last_action
                        break
        except Exception as e:
            logger.debug(f"[GroundingLayer] Episodic resolution failed: {e}")

        return resolutions

    def _resolve_via_llm(
        self,
        unresolved: List[str],
        original_text: str,
        snapshot: Optional[ContextSnapshot],
        conversation_history: Optional[List[str]],
    ) -> dict:
        """Fall back to LLM for complex coreference resolution."""
        resolutions = {}

        context_parts = [
            f"The user said: \"{original_text}\"",
            f"Ambiguous references to resolve: {unresolved}",
        ]
        if snapshot:
            context_parts.append(f"Active application: {snapshot.active_app}")
            context_parts.append(f"Active window title: {snapshot.active_window_title}")
        if conversation_history:
            context_parts.append(f"Recent conversation: {conversation_history[-5:]}")

        prompt = "\n".join(context_parts)
        system = (
            "Resolve the ambiguous pronouns/references in the user's text. "
            "Return a JSON object mapping each ambiguous term to its resolved value. "
            "Example: {\"it\": \"notepad\", \"that\": \"the report file\"}"
        )

        try:
            backends = [self._router._primary, self._router._fallback]
            for backend in backends:
                if not backend:
                    continue
                try:
                    raw = backend._call_llm_closed_loop(prompt=prompt, context=system)
                    parsed = self._router._clean_and_parse_json(raw)
                    if isinstance(parsed, dict):
                        resolutions.update(parsed)
                        break
                except Exception as e:
                    logger.debug(f"[GroundingLayer] LLM resolution backend failed: {e}")
        except Exception as e:
            logger.debug(f"[GroundingLayer] LLM resolution failed: {e}")

        return resolutions

    @staticmethod
    def _apply_resolutions(text: str, resolutions: dict) -> str:
        """Apply resolved references back into the goal text for clarity."""
        resolved_text = text
        for pronoun, resolved in resolutions.items():
            # Only replace standalone pronoun occurrences
            # Avoid replacing substrings (e.g. "it" inside "write")
            import re
            pattern = r'\b' + re.escape(pronoun) + r'\b'
            resolved_text = re.sub(pattern, resolved, resolved_text, count=1, flags=re.IGNORECASE)
        return resolved_text
