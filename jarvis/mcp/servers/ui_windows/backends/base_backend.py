"""
Base Backend
============
Abstract base class defining the contract for Windows UI automation backends.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, List


class UIBackend(ABC):
    """
    Abstract base class for all Jarvis Windows UI automation backends.
    """

    @abstractmethod
    def list_windows(self) -> List[Dict[str, Any]]:
        """
        List all open top-level windows.

        Returns:
            List of dicts, each containing:
                - title: str
                - pid: int
                - class_name: str
                - handle: int
        """
        pass

    @abstractmethod
    def launch_app(self, app_path: str) -> Dict[str, Any]:
        """
        Launch an application.

        Parameters:
            app_path: Path to executable or system command to start the app.

        Returns:
            Dict containing:
                - success: bool
                - pid: int or None
                - error: str or None
        """
        pass

    @abstractmethod
    def get_dom(self, app_title: Optional[str] = None, depth: Optional[int] = None) -> Dict[str, Any]:
        """
        Traverse the UI accessibility tree and return it as a structured DOM tree.

        Parameters:
            app_title: Title or substring of the window to target. If None, targets the desktop root.
            depth: Maximum traversal depth. If None, traverses fully.

        Returns:
            A hierarchical dictionary representation of the UI tree.
            Each node represents an element with properties, actions, and children.
        """
        pass

    @abstractmethod
    def click(self, element_id: str) -> bool:
        """
        Click an element by its ID.

        Returns:
            True if successful, False otherwise.
        """
        pass

    @abstractmethod
    def type_text(self, element_id: str, text: str) -> bool:
        """
        Type text into an element by its ID.

        Returns:
            True if successful, False otherwise.
        """
        pass

    @abstractmethod
    def set_value(self, element_id: str, value: Any) -> bool:
        """
        Set value of an element (e.g. checkbox state, combobox selection).

        Returns:
            True if successful, False otherwise.
        """
        pass

    @abstractmethod
    def invoke(self, element_id: str) -> bool:
        """
        Invoke/execute an element (e.g. trigger menu item or button invoke pattern).

        Returns:
            True if successful, False otherwise.
        """
        pass

    @abstractmethod
    def read_value(self, element_id: str) -> Dict[str, Any]:
        """
        Read the text content, value, and state of an element.

        Returns:
            Dict containing:
                - text: str
                - value: Any
                - state: str or None
        """
        pass
