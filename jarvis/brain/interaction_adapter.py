"""
Interaction Adapter Interface and Implementations
==================================================
Abstract base class and concrete adapters (Telegram, TUI, WebUI) to decouple the brain's 
interactive communications from specific transport layers.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

class InteractionAdapter(ABC):
    """
    Abstract base class defining the adapter contract.
    Decouples UserInteractionManager from any specific transport layer.
    """

    @property
    @abstractmethod
    def adapter_type(self) -> str:
        """Returns the type/name of the adapter (e.g., 'telegram', 'tui', 'webui')."""
        pass

    @abstractmethod
    def send_message(self, session_id: str, message: str) -> bool:
        """Deliver text message to the user."""
        pass

    @abstractmethod
    def send_choices(self, session_id: str, question: str, options: List[str]) -> bool:
        """Deliver a structured choice prompt to the user."""
        pass

    @abstractmethod
    def wait_for_response(self, session_id: str, timeout: Optional[float] = None) -> Optional[str]:
        """Block and wait for user response with an optional timeout."""
        pass


class TelegramInteractionAdapter(InteractionAdapter):
    """Concrete adapter for Telegram communications."""
    
    def __init__(self, channel_adapter: Optional[Any] = None, session_manager: Optional[Any] = None):
        self._channel_adapter = channel_adapter
        self._session_manager = session_manager
        self._sessions: Dict[str, Any] = {}

    def register_session(self, session: Any) -> None:
        """Register a session with this adapter."""
        self._sessions[session.id] = session

    @property
    def adapter_type(self) -> str:
        return "telegram"

    def send_message(self, session_id: str, message: str) -> bool:
        if self._channel_adapter:
            return self._channel_adapter.send(session_id, message)
        return False

    def send_choices(self, session_id: str, question: str, options: List[str]) -> bool:
        formatted_message = f"{question}\n\n" + "\n".join(f"• {opt}" for opt in options)
        return self.send_message(session_id, formatted_message)

    def wait_for_response(self, session_id: str, timeout: Optional[float] = None) -> Optional[str]:
        session = self._sessions.get(session_id)
        if not session and self._session_manager:
            session = self._session_manager.get(session_id)
        if session and hasattr(session, "event_queue"):
            try:
                evt = session.event_queue.get(timeout=timeout)
                if evt and hasattr(evt, "text"):
                    return evt.text
            except Exception:
                pass
        return None


class TUIInteractionAdapter(InteractionAdapter):
    """Concrete adapter for TUI (Terminal User Interface) communications."""
    
    def __init__(self, channel_adapter: Optional[Any] = None, session_manager: Optional[Any] = None):
        self._channel_adapter = channel_adapter
        self._session_manager = session_manager
        self._sessions: Dict[str, Any] = {}

    def register_session(self, session: Any) -> None:
        """Register a session with this adapter."""
        self._sessions[session.id] = session

    @property
    def adapter_type(self) -> str:
        return "tui"

    def send_message(self, session_id: str, message: str) -> bool:
        if self._channel_adapter:
            return self._channel_adapter.send(session_id, message)
        return False

    def send_choices(self, session_id: str, question: str, options: List[str]) -> bool:
        formatted_message = f"{question}\n\n" + "\n".join(f"• {opt}" for opt in options)
        return self.send_message(session_id, formatted_message)

    def wait_for_response(self, session_id: str, timeout: Optional[float] = None) -> Optional[str]:
        session = self._sessions.get(session_id)
        if not session and self._session_manager:
            session = self._session_manager.get(session_id)
        if session and hasattr(session, "event_queue"):
            try:
                evt = session.event_queue.get(timeout=timeout)
                if evt and hasattr(evt, "text"):
                    return evt.text
            except Exception:
                pass
        return None


class WebUIInteractionAdapter(InteractionAdapter):
    """Concrete adapter for Web UI communications."""
    
    def __init__(self, channel_adapter: Optional[Any] = None, session_manager: Optional[Any] = None):
        self._channel_adapter = channel_adapter
        self._session_manager = session_manager
        self._sessions: Dict[str, Any] = {}

    def register_session(self, session: Any) -> None:
        """Register a session with this adapter."""
        self._sessions[session.id] = session

    @property
    def adapter_type(self) -> str:
        return "webui"

    def send_message(self, session_id: str, message: str) -> bool:
        if self._channel_adapter:
            return self._channel_adapter.send(session_id, message)
        return False

    def send_choices(self, session_id: str, question: str, options: List[str]) -> bool:
        formatted_message = f"{question}\n\n" + "\n".join(f"• {opt}" for opt in options)
        return self.send_message(session_id, formatted_message)

    def wait_for_response(self, session_id: str, timeout: Optional[float] = None) -> Optional[str]:
        session = self._sessions.get(session_id)
        if not session and self._session_manager:
            session = self._session_manager.get(session_id)
        if session and hasattr(session, "event_queue"):
            try:
                evt = session.event_queue.get(timeout=timeout)
                if evt and hasattr(evt, "text"):
                    return evt.text
            except Exception:
                pass
        return None



class AdapterRegistry:
    """Registry to keep track of active interaction adapters."""
    
    def __init__(self):
        self._adapters: Dict[str, InteractionAdapter] = {}

    def register(self, adapter: InteractionAdapter) -> None:
        self._adapters[adapter.adapter_type] = adapter

    def get_adapter(self, adapter_type: str) -> Optional[InteractionAdapter]:
        return self._adapters.get(adapter_type)

    def get_active_adapter(self, session_id: str) -> Optional[InteractionAdapter]:
        # Helper to infer active adapter type from session_id (e.g. 'telegram:123' -> 'telegram')
        if ":" in session_id:
            channel = session_id.split(":")[0]
            # Map telegram-test back to telegram
            if channel == "telegram-test":
                channel = "telegram"
            # Map cli back to tui
            elif channel == "cli":
                channel = "tui"
            return self.get_adapter(channel)
        return None
