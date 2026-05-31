"""
Knowledge Gap Engine
====================
Detects missing required parameters and insufficient knowledge in a GoalModel
before the planning phase begins. If gaps are found, it triggers the
UserInteractionManager for clarifications.

In the cognitive loop pipeline:
    NLU → GoalUnderstanding → GroundingLayer → **KnowledgeGapEngine** → CapabilityPlanner

This engine prevents the system from generating incomplete or hallucinated plans
by identifying what it doesn't know and asking the user proactively.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from jarvis.perception.perception_packet import GoalModel

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeGap:
    """Represents a single missing piece of information."""
    parameter: str          # The missing parameter name (e.g. "target_directory", "date_range")
    description: str        # Human-readable description of what's missing
    severity: str = "required"  # "required" = blocks execution, "optional" = can infer/skip
    suggested_question: str = ""  # Pre-built clarification question for the user
    default_value: str = ""       # Fallback default if user doesn't respond


@dataclass
class GapCheckResult:
    """Result of a knowledge gap analysis."""
    has_gaps: bool = False
    gaps: List[KnowledgeGap] = field(default_factory=list)
    goal: Optional[GoalModel] = None  # Updated goal model (if gaps were auto-resolved)
    clarification_needed: bool = False  # True if user interaction is required


# ── Intent-Specific Required Parameters ──────────────────

# Maps abstract intents to their required parameters
_INTENT_REQUIREMENTS = {
    "app_interaction": {
        "required": ["target_app"],
        "questions": {
            "target_app": "Which application should I open?",
        },
    },
    "web_search": {
        "required": ["search_query"],
        "questions": {
            "search_query": "What would you like me to search for?",
        },
    },
    "file_management": {
        "required": ["file_path"],
        "questions": {
            "file_path": "Which file or directory are you referring to?",
        },
    },
    "content_generation": {
        "required": ["content_topic"],
        "questions": {
            "content_topic": "What should the content be about?",
        },
    },
    "system_control": {
        "required": ["control_target"],
        "questions": {
            "control_target": "Which system setting should I modify?",
        },
    },
    "communication": {
        "required": ["recipient", "message_content"],
        "questions": {
            "recipient": "Who should I send this to?",
            "message_content": "What message should I send?",
        },
    },
}


class KnowledgeGapEngine:
    """
    Scans a GoalModel for missing required parameters and knowledge prerequisites.

    Usage::

        engine = KnowledgeGapEngine()
        result = engine.check(goal_model)
        if result.clarification_needed:
            # Route to UserInteractionManager
            for gap in result.gaps:
                answer = uim.prompt_clarification(gap.suggested_question)
                goal_model = engine.fill_gap(goal_model, gap.parameter, answer)
    """

    def __init__(self, confidence_threshold: float = 0.5):
        """
        Parameters
        ----------
        confidence_threshold : float
            Minimum confidence required from GoalUnderstandingLayer.
            Below this threshold, the entire goal is treated as ambiguous.
        """
        self._confidence_threshold = confidence_threshold

    def check(self, goal: GoalModel) -> GapCheckResult:
        """
        Analyze a GoalModel for missing information.

        Parameters
        ----------
        goal : GoalModel
            The grounded goal model to analyze.

        Returns
        -------
        GapCheckResult
            Analysis result with any detected gaps and clarification needs.
        """
        gaps: List[KnowledgeGap] = []

        # 1. Check overall confidence
        if goal.confidence < self._confidence_threshold:
            gaps.append(KnowledgeGap(
                parameter="goal_clarity",
                description="The goal interpretation has low confidence",
                severity="required",
                suggested_question=f"I'm not sure I understood correctly. Did you mean: '{goal.primary_goal}'?",
            ))

        # 2. Check for empty primary goal
        if not goal.primary_goal or not goal.primary_goal.strip():
            gaps.append(KnowledgeGap(
                parameter="primary_goal",
                description="No goal was extracted from the utterance",
                severity="required",
                suggested_question="What would you like me to do?",
            ))
            goal.knowledge_gaps = [g.parameter for g in gaps]
            goal.is_complete = False
            return GapCheckResult(has_gaps=True, gaps=gaps, goal=goal, clarification_needed=True)

        # 3. Check intent-specific requirements
        for intent in goal.intents:
            intent_gaps = self._check_intent_requirements(intent, goal)
            gaps.extend(intent_gaps)

        # 4. Check for target app when intents require one
        app_intents = {"app_interaction", "text_edit"}
        if app_intents.intersection(set(goal.intents)) and not goal.target_app:
            # Check if target is embedded in the goal text
            if not self._can_infer_app_from_text(goal.primary_goal):
                gaps.append(KnowledgeGap(
                    parameter="target_app",
                    description="No target application specified for app interaction",
                    severity="required",
                    suggested_question="Which application should I use?",
                ))

        # 5. Check required knowledge prerequisites
        for knowledge_req in goal.required_knowledge:
            gaps.append(KnowledgeGap(
                parameter=f"knowledge_{knowledge_req}",
                description=f"Required knowledge not available: {knowledge_req}",
                severity="optional",  # Can attempt to acquire dynamically
                suggested_question=f"I may need additional information about: {knowledge_req}. Can you provide details?",
            ))

        # Build result
        required_gaps = [g for g in gaps if g.severity == "required"]
        has_gaps = len(gaps) > 0
        clarification_needed = len(required_gaps) > 0

        if has_gaps:
            goal.knowledge_gaps = [g.parameter for g in gaps]
            goal.is_complete = not clarification_needed

        return GapCheckResult(
            has_gaps=has_gaps,
            gaps=gaps,
            goal=goal,
            clarification_needed=clarification_needed,
        )

    def fill_gap(self, goal: GoalModel, parameter: str, value: str) -> GoalModel:
        """
        Fill a specific knowledge gap with a user-provided value.

        Parameters
        ----------
        goal : GoalModel
            The goal model with gaps.
        parameter : str
            The parameter name to fill.
        value : str
            The user-provided value.

        Returns
        -------
        GoalModel
            Updated goal model with the gap filled.
        """
        if parameter == "target_app":
            goal.target_app = value
        elif parameter == "goal_clarity":
            # User confirmed or corrected the goal
            goal.confidence = 1.0
        elif parameter == "primary_goal":
            goal.primary_goal = value

        # Remove from gaps list
        goal.knowledge_gaps = [g for g in goal.knowledge_gaps if g != parameter]
        goal.is_complete = len([g for g in goal.knowledge_gaps]) == 0

        logger.info(f"[KnowledgeGapEngine] Filled gap '{parameter}' = '{value}'")
        return goal

    def _check_intent_requirements(self, intent: str, goal: GoalModel) -> List[KnowledgeGap]:
        """Check if an intent's required parameters are satisfied."""
        gaps = []
        requirements = _INTENT_REQUIREMENTS.get(intent, {})
        required_params = requirements.get("required", [])
        questions = requirements.get("questions", {})

        for param in required_params:
            # Skip target_app check here — handled separately with text inference
            if param == "target_app":
                continue
            if not self._is_parameter_available(param, goal):
                gaps.append(KnowledgeGap(
                    parameter=param,
                    description=f"Missing required parameter '{param}' for intent '{intent}'",
                    severity="required",
                    suggested_question=questions.get(param, f"What is the {param.replace('_', ' ')}?"),
                ))

        return gaps

    @staticmethod
    def _is_parameter_available(param: str, goal: GoalModel) -> bool:
        """Check if a required parameter can be found in the goal model."""
        if param == "target_app":
            return bool(goal.target_app)
        if param == "search_query":
            # Search query is typically embedded in the primary goal
            return bool(goal.primary_goal)
        if param == "content_topic":
            return bool(goal.primary_goal)
        if param == "control_target":
            return bool(goal.primary_goal)
        if param == "file_path":
            # Check if a file path is mentioned in the goal
            return any(c in goal.primary_goal for c in ["/", "\\", ".txt", ".py", ".doc"])
        # Default: assume available if we have a goal
        return bool(goal.primary_goal)

    @staticmethod
    def _can_infer_app_from_text(text: str) -> bool:
        """Check if the target app can be inferred from the goal text."""
        text_lower = text.lower()
        known_apps = [
            "notepad", "chrome", "edge", "firefox", "word", "excel", "vscode",
            "terminal", "powershell", "cmd", "explorer", "settings", "slack",
            "spotify", "discord", "teams", "outlook", "calculator", "paint",
            "brave", "opera",
        ]
        return any(app in text_lower for app in known_apps)
