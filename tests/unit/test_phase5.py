"""
Unit Tests for Phase 5: Windows UI Automation Bridge and configuration
"""

import pytest
import os
from unittest.mock import MagicMock, patch
from jarvis.mcp.adapters.windows_uia_bridge import WindowsUIABridge


class TestWindowsUIABridge:
    """Tests for the WindowsUIABridge."""

    @pytest.fixture
    def mock_env(self):
        # Force mock mode and restore original value on cleanup
        old_val = os.environ.get("JARVIS_ALLOW_MOCK")
        os.environ["JARVIS_ALLOW_MOCK"] = "true"
        yield
        # Cleanup
        if old_val is not None:
            os.environ["JARVIS_ALLOW_MOCK"] = old_val
        elif "JARVIS_ALLOW_MOCK" in os.environ:
            del os.environ["JARVIS_ALLOW_MOCK"]

    def test_bridge_connect_and_disconnect(self, mock_env):
        bridge = WindowsUIABridge()
        assert bridge.connect() is True
        
        # Test RPC connection state
        res = bridge.get_focused_element()
        assert res["element_id"] == "focused_edit_1"
        assert res["control_type"] == "edit"

        bridge.disconnect()
        assert bridge._connected is False

    def test_element_discovery(self, mock_env):
        bridge = WindowsUIABridge()
        
        # Find element
        elem = bridge.find_element("Name", "Start Button")
        assert elem["element_id"] == "elem_Start Button"
        assert elem["control_type"] == "button"

        # Find all elements
        elems = bridge.find_all_elements("ControlType", "list_item")
        assert len(elems) == 1
        assert elems[0]["element_id"] == "elem_1"

    def test_element_interactions(self, mock_env):
        bridge = WindowsUIABridge()
        
        assert bridge.click_element("elem_1") is True
        assert bridge.type_text("edit_1", "Hello World") is True
        assert bridge.set_value("edit_1", "High Value") is True
        assert bridge.toggle_element("checkbox_1") is True
        assert bridge.select_element("tab_item_1") is True
        assert bridge.expand_element("combo_1") is True
        assert bridge.collapse_element("combo_1") is True
        assert bridge.scroll_element("pane_1", "vertical", "page_down") is True
        assert bridge.set_slider_value("slider_1", 75.5) is True
        assert bridge.invoke_element("btn_1") is True

    def test_window_management(self, mock_env):
        bridge = WindowsUIABridge()
        
        # Window properties
        win_info = bridge.get_window_info(12345)
        assert win_info["hwnd"] == 12345
        assert win_info["process"] == "mock.exe"

        # Window state
        assert bridge.set_window_state(12345, "maximize") is True
        assert bridge.move_window(12345, 10, 10) is True
        assert bridge.resize_window(12345, 800, 600) is True
        assert bridge.set_foreground_window(12345) is True

    def test_advanced_patterns(self, mock_env):
        bridge = WindowsUIABridge()
        
        assert bridge.get_grid_data("grid_1", 2, 3)["value"] == "Mock Cell Content"
        assert bridge.get_text_range("doc_1", 0, 100) == "Selected range text content."
        assert bridge.drag_element("elem_from", "elem_to") is True
