import pytest
import os
import shutil
from unittest.mock import MagicMock, patch
from jarvis.utils.app_finder import AppFinder

def test_find_exe_path_settings():
    path = AppFinder.find_exe_path("settings")
    assert path == "ms-settings:"

def test_find_exe_path_empty():
    assert AppFinder.find_exe_path("") is None
    assert AppFinder.find_exe_path("   ") is None

@patch("shutil.which")
def test_find_exe_path_via_path(mock_which):
    # Mocking system PATH resolution
    mock_which.return_value = "C:\\Windows\\System32\\cmd.exe"
    
    # We must patch the earlier checks to return None so it falls back to PATH scan
    with patch.object(AppFinder, "_check_registry_app_path", return_value=None), \
         patch.object(AppFinder, "_scan_start_menu_shortcuts", return_value=None):
         
        path = AppFinder.find_exe_path("cmd")
        assert path == "C:\\Windows\\System32\\cmd.exe"
        # Verify that it searched for either 'cmd' or 'cmd.exe'
        assert mock_which.call_count >= 1
        called_args = [call[0][0] for call in mock_which.call_args_list]
        assert "cmd" in called_args or "cmd.exe" in called_args

def test_resolve_shortcut_failure():
    # Calling it with a non-existent file path should return "" or None
    path = AppFinder._resolve_shortcut("C:\\nonexistent\\path.lnk")
    assert path in (None, "")

@patch("os.path.exists")
def test_find_exe_path_registry_hit(mock_exists):
    mock_exists.return_value = True
    
    with patch.object(AppFinder, "_check_registry_app_path") as mock_reg:
        mock_reg.return_value = "C:\\Program Files\\App\\app.exe"
        
        path = AppFinder.find_exe_path("app")
        assert path == "C:\\Program Files\\App\\app.exe"
        # Verify that it searched for either 'app' or 'app.exe'
        assert mock_reg.call_count >= 1
        called_args = [call[0][0] for call in mock_reg.call_args_list]
        assert "app" in called_args or "app.exe" in called_args
