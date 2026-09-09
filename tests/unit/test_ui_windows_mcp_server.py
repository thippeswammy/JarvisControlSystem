"""
tests/unit/test_ui_windows_mcp_server.py
===========================================
Unit tests for jarvis.mcp.servers.ui_windows.mcp_ui_windows_server.UIWindowsMCPServer.

The module-level `backend` singleton (auto-selected between PywinautoBackend
and CppUIABackend at import time) is patched out with a MagicMock so these
tests only exercise UIWindowsMCPServer's own routing/dispatch logic --
enrich_dom/compute_dom_delta/serialize_dom are the real implementations,
since they are pure and cheap to run.
"""
import pytest
from unittest.mock import MagicMock, patch

import jarvis.mcp.servers.ui_windows.mcp_ui_windows_server as server_module
from jarvis.mcp.servers.ui_windows.mcp_ui_windows_server import UIWindowsMCPServer

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_backend():
    with patch.object(server_module, "backend") as mock_be:
        yield mock_be


@pytest.fixture
def server(mock_backend):
    return UIWindowsMCPServer()


def _dom_tree(element_id="root", name="Root", control_type="Window", children=None):
    return {
        "element_id": element_id,
        "name": name,
        "control_type": control_type,
        "auto_id": "",
        "enabled": True,
        "visible": True,
        "children": children or [],
    }


# ── list_tools ────────────────────────────────────────────────

def test_list_tools_returns_all_expected_tool_names(server):
    result = server.list_tools()
    names = {t["name"] for t in result["tools"]}
    assert names == {
        "get_dom", "list_windows", "launch_app", "find_elements",
        "click", "type_text", "set_value", "invoke", "read_value",
    }


def test_list_tools_get_dom_requires_mode(server):
    result = server.list_tools()
    get_dom_tool = next(t for t in result["tools"] if t["name"] == "get_dom")
    assert get_dom_tool["inputSchema"]["required"] == ["mode"]


# ── dispatch: routing to correct backend method ──────────────

def test_dispatch_list_windows_routes_to_backend(server, mock_backend):
    mock_backend.list_windows.return_value = [{"title": "Notepad"}]

    result = server.dispatch("list_windows", {})

    mock_backend.list_windows.assert_called_once()
    assert result["windows"] == [{"title": "Notepad"}]
    assert "Found 1 windows" in result["content"][0]["text"]


def test_dispatch_launch_app_routes_to_backend_with_app_path(server, mock_backend):
    mock_backend.launch_app.return_value = {"success": True, "pid": 7, "error": None}

    result = server.dispatch("launch_app", {"app_path": "calc.exe"})

    mock_backend.launch_app.assert_called_once_with("calc.exe")
    assert result["success"] is True
    assert result["pid"] == 7


def test_dispatch_get_dom_calls_backend_and_serializes_with_real_helpers(server, mock_backend):
    raw_tree = _dom_tree(children=[{"element_id": "btn1", "name": "OK", "control_type": "Button", "children": []}])
    mock_backend.get_dom.return_value = raw_tree

    result = server.dispatch("get_dom", {"mode": "FULL"})

    mock_backend.get_dom.assert_called_once_with(None, None)
    # enrich_dom (real, not mocked) should have added actions_available.
    assert result["dom_tree"]["actions_available"] == ["read_value"]
    assert result["dom_tree"]["children"][0]["actions_available"] == ["click", "invoke"]
    assert "OK" in result["dom_text"]
    assert server.last_dom_tree == result["dom_tree"]


def test_dispatch_get_dom_uses_current_app_title_context(server, mock_backend):
    mock_backend.get_dom.return_value = _dom_tree()

    server.dispatch("get_dom", {"mode": "FULL", "app_title": "Notepad"})
    assert server.current_app_title == "Notepad"

    # A subsequent call without app_title should reuse the stored context.
    mock_backend.get_dom.reset_mock()
    server.dispatch("get_dom", {"mode": "FULL"})
    mock_backend.get_dom.assert_called_once_with("Notepad", None)


def test_dispatch_find_elements_matches_by_name(server, mock_backend):
    raw_tree = _dom_tree(children=[
        {"element_id": "btn1", "name": "Submit Order", "control_type": "Button", "children": []},
        {"element_id": "txt1", "name": "Other", "control_type": "Text", "children": []},
    ])
    mock_backend.get_dom.return_value = raw_tree

    result = server.dispatch("find_elements", {"by": "name", "value": "submit"})

    assert len(result["matches"]) == 1
    assert result["matches"][0]["element_id"] == "btn1"


def test_dispatch_read_value_routes_to_backend(server, mock_backend):
    mock_backend.read_value.return_value = {"text": "hi", "value": "hi", "state": None}

    result = server.dispatch("read_value", {"element_id": "e1"})

    mock_backend.read_value.assert_called_once_with("e1")
    assert result["text"] == "hi"
    assert result["value"] == "hi"


@pytest.mark.parametrize("tool_name,backend_method", [
    ("click", "click"),
    ("invoke", "invoke"),
])
def test_dispatch_write_action_captures_before_after_delta(server, mock_backend, tool_name, backend_method):
    before_tree = _dom_tree(children=[{"element_id": "c1", "name": "A", "control_type": "Text", "children": []}])
    after_tree = _dom_tree(children=[{"element_id": "c1", "name": "B", "control_type": "Text", "children": []}])
    mock_backend.get_dom.side_effect = [before_tree, after_tree]
    getattr(mock_backend, backend_method).return_value = True

    with patch.object(server_module.time, "sleep"):
        result = server.dispatch(tool_name, {"element_id": "c1"})

    assert result["success"] is True
    assert result["dom_delta"]["changed"] is True
    assert result["dom_delta"]["modified"]["c1"]["name"] == {"before": "A", "after": "B"}


def test_dispatch_type_text_passes_text_argument(server, mock_backend):
    mock_backend.get_dom.return_value = _dom_tree()
    mock_backend.type_text.return_value = True

    with patch.object(server_module.time, "sleep"):
        result = server.dispatch("type_text", {"element_id": "e1", "text": "hello"})

    mock_backend.type_text.assert_called_once_with("e1", "hello")
    assert result["success"] is True


def test_dispatch_set_value_passes_value_argument(server, mock_backend):
    mock_backend.get_dom.return_value = _dom_tree()
    mock_backend.set_value.return_value = False

    with patch.object(server_module.time, "sleep"):
        result = server.dispatch("set_value", {"element_id": "e1", "value": "x"})

    mock_backend.set_value.assert_called_once_with("e1", "x")
    assert result["success"] is False


def test_dispatch_write_action_falls_back_to_last_dom_tree_when_before_capture_fails(server, mock_backend):
    server.last_dom_tree = _dom_tree(element_id="cached_root")
    mock_backend.get_dom.side_effect = [RuntimeError("cannot read DOM"), _dom_tree(element_id="cached_root")]
    mock_backend.click.return_value = True

    with patch.object(server_module.time, "sleep"):
        result = server.dispatch("click", {"element_id": "e1"})

    # The before-capture exception is caught; dispatch should not raise and should
    # still return a result using the cached last_dom_tree as the "before" state.
    assert result["success"] is True
    assert "dom_delta" in result


def test_dispatch_write_action_dom_after_none_when_after_capture_fails(server, mock_backend):
    mock_backend.get_dom.side_effect = [_dom_tree(), RuntimeError("cannot read DOM")]
    mock_backend.click.return_value = True

    with patch.object(server_module.time, "sleep"):
        result = server.dispatch("click", {"element_id": "e1"})

    assert result["success"] is True
    # compute_dom_delta(before, None) -> changed True with empty lists (per actual dom_builder logic)
    assert result["dom_delta"] == {"changed": True, "added": [], "removed": [], "modified": {}}


def test_dispatch_unknown_tool_raises_value_error(server, mock_backend):
    with pytest.raises(ValueError, match="Unknown tool: bogus_tool"):
        server.dispatch("bogus_tool", {})


# ── _find_nodes_recursive ─────────────────────────────────────

def test_find_nodes_recursive_by_control_type_exact_case_insensitive_match(server):
    tree = _dom_tree(children=[
        {"element_id": "b1", "name": "A", "control_type": "Button", "children": []},
        {"element_id": "t1", "name": "B", "control_type": "Text", "children": []},
    ])
    matches = []
    server._find_nodes_recursive(tree, "control_type", "button", matches)
    assert [m["element_id"] for m in matches] == ["b1"]


def test_find_nodes_recursive_by_auto_id_substring_match(server):
    tree = _dom_tree(children=[
        {"element_id": "e1", "name": "", "auto_id": "usernameField", "control_type": "Edit", "children": []},
    ])
    matches = []
    server._find_nodes_recursive(tree, "auto_id", "username", matches)
    assert len(matches) == 1
    assert matches[0]["element_id"] == "e1"
