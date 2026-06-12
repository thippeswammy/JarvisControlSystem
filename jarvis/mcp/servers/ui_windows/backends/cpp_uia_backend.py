"""
C++ UIA Backend Stub
===================
Stub implementation of the CppUIABackend. This is reserved for Phase 2
integration when the WinRT DLL initialization issues are resolved.
"""

from typing import Any, Optional, Dict, List
from jarvis.mcp.servers.ui_windows.backends.base_backend import UIBackend


class CppUIABackend(UIBackend):
    """
    Stub class representing the C++ UIA Remote Operations backend.
    """

    @staticmethod
    def is_available() -> bool:
        """
        Check if the C++ backend is compiled and runnable.
        Returns False in Phase 1.
        """
        return False

    def list_windows(self) -> List[Dict[str, Any]]:
        raise NotImplementedError("C++ backend is not available in Phase 1.")

    def launch_app(self, app_path: str) -> Dict[str, Any]:
        raise NotImplementedError("C++ backend is not available in Phase 1.")

    def get_dom(self, app_title: Optional[str] = None, depth: Optional[int] = None) -> Dict[str, Any]:
        raise NotImplementedError("C++ backend is not available in Phase 1.")

    def click(self, element_id: str) -> bool:
        raise NotImplementedError("C++ backend is not available in Phase 1.")

    def type_text(self, element_id: str, text: str) -> bool:
        raise NotImplementedError("C++ backend is not available in Phase 1.")

    def set_value(self, element_id: str, value: Any) -> bool:
        raise NotImplementedError("C++ backend is not available in Phase 1.")

    def invoke(self, element_id: str) -> bool:
        raise NotImplementedError("C++ backend is not available in Phase 1.")

    def read_value(self, element_id: str) -> Dict[str, Any]:
        raise NotImplementedError("C++ backend is not available in Phase 1.")
