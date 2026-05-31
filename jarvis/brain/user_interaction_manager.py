"""
User Interaction Manager
========================
Session-aware gatekeeper for all interactive communications between Jarvis and the user.
Dispatches queries through the appropriate InteractionAdapter based on session routing.
"""

import logging
from typing import List, Optional, Any, Dict
from jarvis.brain.interaction_adapter import AdapterRegistry, InteractionAdapter

logger = logging.getLogger(__name__)

class UserInteractionManager:
    """
    Manages session-aware interactive communication with the user.
    """

    def __init__(self, registry: Optional[AdapterRegistry] = None, default_timeout: float = 60.0):
        self._registry = registry or AdapterRegistry()
        self._default_timeout = default_timeout
        self._interaction_timeouts: Dict[str, float] = {
            "clarification": default_timeout,
            "confirmation": default_timeout,
            "decision": default_timeout
        }

    def register_adapter(self, adapter: InteractionAdapter) -> None:
        """Register a new interaction adapter."""
        self._registry.register(adapter)

    def _get_adapter(self, session_id: str) -> Optional[InteractionAdapter]:
        """Find the active adapter for the session."""
        return self._registry.get_active_adapter(session_id)

    def prompt_clarification(
        self, 
        session_id: str, 
        question: str, 
        options: Optional[List[str]] = None,
        timeout: Optional[float] = None
    ) -> Optional[str]:
        """
        Asks user to resolve knowledge gaps.
        Returns the user's text response, or None on timeout.
        """
        adapter = self._get_adapter(session_id)
        if not adapter:
            logger.warning(f"[UserInteractionManager] No adapter found for session: {session_id}")
            return None

        to = timeout if timeout is not None else self._interaction_timeouts.get("clarification", self._default_timeout)
        logger.info(f"[UserInteractionManager] Prompting clarification on session {session_id} (timeout={to})")
        
        if options:
            adapter.send_choices(session_id, question, options)
        else:
            adapter.send_message(session_id, question)

        response = adapter.wait_for_response(session_id, timeout=to)
        if response is None:
            logger.warning(f"[UserInteractionManager] Clarification request timed out for session {session_id}")
        return response

    def request_confirmation(
        self, 
        session_id: str, 
        action_description: str,
        timeout: Optional[float] = None
    ) -> bool:
        """
        Safety approval gate. Asks user to confirm an action.
        Returns True if confirmed, False if denied or timed out (safety first).
        """
        adapter = self._get_adapter(session_id)
        if not adapter:
            logger.warning(f"[UserInteractionManager] No adapter found for session: {session_id}")
            return False

        to = timeout if timeout is not None else self._interaction_timeouts.get("confirmation", self._default_timeout)
        logger.info(f"[UserInteractionManager] Requesting confirmation on session {session_id} (timeout={to})")

        question = f"⚠️ *Safety Approval Required*\nDo you allow the following action?\n\n{action_description}"
        options = ["Yes, proceed", "No, cancel"]
        
        adapter.send_choices(session_id, question, options)
        
        response = adapter.wait_for_response(session_id, timeout=to)
        if response is None:
            logger.warning(f"[UserInteractionManager] Confirmation request timed out (default Deny) for session {session_id}")
            return False

        response_clean = response.strip().lower()
        if response_clean in ("yes, proceed", "yes", "y", "allow", "approve", "ok", "proceed"):
            return True

        logger.info(f"[UserInteractionManager] Action denied by user: {response}")
        return False

    def request_decision(
        self, 
        session_id: str, 
        question: str, 
        choices: List[str],
        timeout: Optional[float] = None
    ) -> Optional[str]:
        """
        Structured multi-choice selection.
        Returns the chosen option, or None on timeout.
        """
        adapter = self._get_adapter(session_id)
        if not adapter:
            logger.warning(f"[UserInteractionManager] No adapter found for session: {session_id}")
            return None

        to = timeout if timeout is not None else self._interaction_timeouts.get("decision", self._default_timeout)
        logger.info(f"[UserInteractionManager] Requesting decision on session {session_id} (timeout={to})")
        
        adapter.send_choices(session_id, question, choices)
        
        response = adapter.wait_for_response(session_id, timeout=to)
        if response is None:
            logger.warning(f"[UserInteractionManager] Decision request timed out for session {session_id}")
            return None

        # Check if response matches one of the choices (case-insensitive fuzzy match)
        response_clean = response.strip().lower()
        for choice in choices:
            if choice.strip().lower() == response_clean or response_clean in choice.strip().lower():
                return choice

        return response

    def notify(self, session_id: str, message: str) -> bool:
        """
        One-way status updates to the user.
        """
        adapter = self._get_adapter(session_id)
        if not adapter:
            logger.warning(f"[UserInteractionManager] No adapter found for session: {session_id}")
            return False

        return adapter.send_message(session_id, message)
