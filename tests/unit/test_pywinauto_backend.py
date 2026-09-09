"""
tests/unit/test_pywinauto_backend.py
======================================
Unit tests for jarvis.mcp.servers.ui_windows.backends.pywinauto_backend.PywinautoBackend.

pywinauto is mocked at the module boundary (Desktop/Application) so these
tests exercise only PywinautoBackend's own logic (caching, traversal,
fallback behavior, error handling) without touching a real desktop.
"""
import pytest
from unittest.mock import MagicMock, patch, call

import jarvis.mcp.servers.ui_windows.backends.pywinauto_backend as pwb
from jarvis.mcp.servers.ui_windows.backends.pywinauto_backend import PywinautoBackend

pytestmark = pytest.mark.unit


@pytest.fixture
def backend():
    with patch.object(pwb, "Desktop") as mock_desktop_cls:
        mock_desktop_cls.return_value = MagicMock()
        b = PywinautoBackend()
        yield b


def _make_window_mock(title="MyWindow", pid=123, class_name="Notepad", handle=999):
    win = MagicMock()
    win.window_text.return_value = title
    win.process_id.return_value = pid
    win.class_name.return_value = class_name
    win.handle = handle
    return win


def _make_element(name="Elem", control_type="Button", auto_id="", enabled=True,
                   visible=True, rect=(0, 0, 10, 10), children=None):
    """Build a mock pywinauto element with element_info + children()."""
    elem = MagicMock()
    info = MagicMock()
    info.name = name
    info.control_type = control_type
    info.automation_id = auto_id
    info.enabled = enabled
    info.visible = visible
    if rect is not None:
        r = MagicMock()
        r.left, r.top = rect[0], rect[1]
        r.width.return_value = rect[2]
        r.height.return_value = rect[3]
        info.rectangle = r
    else:
        info.rectangle = None
    elem.element_info = info
    elem.children.return_value = children or []
    return elem


# ── __init__ ──────────────────────────────────────────────────

def test_init_constructs_desktop_with_uia_backend():
    with patch.object(pwb, "Desktop") as mock_desktop_cls:
        PywinautoBackend()
        mock_desktop_cls.assert_called_once_with(backend="uia")


# ── list_windows ──────────────────────────────────────────────

def test_list_windows_returns_expected_fields(backend):
    win = _make_window_mock(title="Notepad", pid=42, class_name="Notepad", handle=555)
    backend._desktop.windows.return_value = [win]

    result = backend.list_windows()

    assert result == [{"title": "Notepad", "pid": 42, "class_name": "Notepad", "handle": 555}]


def test_list_windows_filters_out_untitled_windows(backend):
    titled = _make_window_mock(title="Visible")
    untitled = _make_window_mock(title="")
    backend._desktop.windows.return_value = [titled, untitled]

    result = backend.list_windows()

    assert len(result) == 1
    assert result[0]["title"] == "Visible"


def test_list_windows_skips_window_raising_exception(backend):
    good = _make_window_mock(title="Good")
    bad = MagicMock()
    bad.window_text.side_effect = RuntimeError("COM error")
    backend._desktop.windows.return_value = [bad, good]

    result = backend.list_windows()

    # The exception on `bad` is caught and logged; only `good` is returned.
    assert len(result) == 1
    assert result[0]["title"] == "Good"


# ── launch_app ────────────────────────────────────────────────

def test_launch_app_success_returns_pid(backend):
    with patch.object(pwb, "Application") as mock_app_cls, patch.object(pwb.time, "sleep"):
        mock_app_instance = MagicMock()
        mock_app_instance.process = 4321
        mock_app_cls.return_value.start.return_value = mock_app_instance

        result = backend.launch_app("notepad.exe")

        assert result == {"success": True, "pid": 4321, "error": None}
        mock_app_cls.return_value.start.assert_called_once_with("notepad.exe")


def test_launch_app_calculator_kills_existing_instances_first(backend):
    with patch.object(pwb, "Application") as mock_app_cls, \
         patch.object(pwb.time, "sleep"), \
         patch.object(pwb.os, "system") as mock_system:
        mock_app_instance = MagicMock()
        mock_app_instance.process = 1
        mock_app_cls.return_value.start.return_value = mock_app_instance

        backend.launch_app("calc.exe")

        assert mock_system.call_count == 2  # taskkill for CalculatorApp.exe and Calculator.exe


def test_launch_app_failure_returns_error_string(backend):
    with patch.object(pwb, "Application") as mock_app_cls, patch.object(pwb.time, "sleep"):
        mock_app_cls.return_value.start.side_effect = OSError("file not found")

        result = backend.launch_app("nonexistent.exe")

        assert result["success"] is False
        assert result["pid"] is None
        assert "file not found" in result["error"]


# ── get_dom ───────────────────────────────────────────────────

def test_get_dom_desktop_root_traverses_and_builds_node_dict(backend):
    child = _make_element(name="OK", control_type="Button")
    root = _make_element(name="", control_type="Pane", children=[child])
    backend._desktop.windows.return_value = []
    # For desktop-root traversal, `self._desktop` itself is the root passed to _traverse.
    backend._desktop.element_info = root.element_info
    backend._desktop.children.return_value = [child]

    result = backend.get_dom(app_title=None)

    assert result["control_type"] == "Pane"
    assert len(result["children"]) == 1
    assert result["children"][0]["name"] == "OK"
    assert result["children"][0]["control_type"] == "Button"


def test_get_dom_app_title_not_found_raises_value_error(backend):
    win = _make_window_mock(title="Notepad")
    backend._desktop.windows.return_value = [win]

    with pytest.raises(ValueError, match="Calculator"):
        backend.get_dom(app_title="Calculator")


def test_get_dom_app_title_matches_case_insensitive_substring(backend):
    target_elem_info = MagicMock()
    win = _make_window_mock(title="My Calculator App")
    win.element_info = _make_element(name="My Calculator App", control_type="Window").element_info
    win.children.return_value = []
    backend._desktop.windows.return_value = [win]

    result = backend.get_dom(app_title="calculator")

    assert result["name"] == "My Calculator App"
    assert result["control_type"] == "Window"


def test_get_dom_respects_max_depth(backend):
    grandchild = _make_element(name="Grandchild", control_type="Text")
    child = _make_element(name="Child", control_type="Pane", children=[grandchild])
    root = _make_element(name="Root", control_type="Window", children=[child])
    backend._desktop.element_info = root.element_info
    backend._desktop.children.return_value = [child]

    result = backend.get_dom(app_title=None, depth=1)

    assert result["children"][0]["name"] == "Child"
    # depth=1 means we stop recursing once current_depth reaches 1,
    # so the grandchild level should not be present.
    assert result["children"][0]["children"] == []


def test_get_dom_element_id_disambiguates_duplicate_names(backend):
    child1 = _make_element(name="Item", control_type="ListItem")
    child2 = _make_element(name="Item", control_type="ListItem")
    root = _make_element(name="List", control_type="Pane", children=[child1, child2])
    backend._desktop.element_info = root.element_info
    backend._desktop.children.return_value = [child1, child2]

    result = backend.get_dom(app_title=None)

    ids = [c["element_id"] for c in result["children"]]
    assert len(ids) == 2
    assert len(set(ids)) == 2  # duplicate base ids must be disambiguated


def test_get_dom_populates_element_cache_for_click(backend):
    child = _make_element(name="Submit", control_type="Button")
    root = _make_element(name="Form", control_type="Window", children=[child])
    backend._desktop.element_info = root.element_info
    backend._desktop.children.return_value = [child]

    result = backend.get_dom(app_title=None)
    child_id = result["children"][0]["element_id"]

    assert child_id in backend._element_cache
    assert backend._element_cache[child_id] is child


# ── click ─────────────────────────────────────────────────────

def test_click_element_not_in_cache_returns_false(backend):
    assert backend.click("nonexistent_id") is False


def test_click_success_via_click_method(backend):
    wrapper = MagicMock(spec=["set_focus", "click"])
    backend._element_cache["btn1"] = wrapper

    assert backend.click("btn1") is True
    wrapper.click.assert_called_once()


def test_click_falls_back_to_click_input_when_click_raises(backend):
    wrapper = MagicMock(spec=["set_focus", "click", "click_input"])
    wrapper.click.side_effect = RuntimeError("click() unsupported")
    backend._element_cache["btn1"] = wrapper

    assert backend.click("btn1") is True
    wrapper.click_input.assert_called_once()


def test_click_returns_false_when_both_click_and_click_input_fail(backend):
    wrapper = MagicMock(spec=["set_focus", "click", "click_input"])
    wrapper.click.side_effect = RuntimeError("boom")
    wrapper.click_input.side_effect = RuntimeError("boom2")
    backend._element_cache["btn1"] = wrapper

    assert backend.click("btn1") is False


# ── type_text ─────────────────────────────────────────────────

def test_type_text_element_not_in_cache_returns_false(backend):
    assert backend.type_text("nope", "hello") is False


def test_type_text_uses_set_text_to_clear_then_types(backend):
    wrapper = MagicMock(spec=["set_focus", "set_text", "type_keys"])
    backend._element_cache["edit1"] = wrapper

    assert backend.type_text("edit1", "hello world") is True
    wrapper.set_text.assert_called_once_with("")
    wrapper.type_keys.assert_called_once_with("hello world", with_spaces=True)


def test_type_text_falls_back_to_select_all_backspace_when_no_set_text(backend):
    wrapper = MagicMock(spec=["set_focus", "type_keys"])
    backend._element_cache["edit1"] = wrapper

    assert backend.type_text("edit1", "hi") is True
    # First call clears via ^a{BACKSPACE}, second call types the actual text.
    assert wrapper.type_keys.call_args_list == [
        call("^a{BACKSPACE}"),
        call("hi", with_spaces=True),
    ]


def test_type_text_returns_false_when_typing_raises(backend):
    wrapper = MagicMock(spec=["set_focus", "set_text", "type_keys"])
    wrapper.type_keys.side_effect = RuntimeError("boom")
    backend._element_cache["edit1"] = wrapper

    assert backend.type_text("edit1", "hi") is False


# ── set_value ─────────────────────────────────────────────────

def test_set_value_not_in_cache_returns_false(backend):
    assert backend.set_value("nope", "x") is False


def test_set_value_uses_select_for_combobox(backend):
    wrapper = MagicMock(spec=["set_focus", "select"])
    backend._element_cache["cmb1"] = wrapper

    assert backend.set_value("cmb1", "OptionA") is True
    wrapper.select.assert_called_once_with("OptionA")


def test_set_value_checks_checkbox_for_truthy_value(backend):
    wrapper = MagicMock(spec=["set_focus", "check", "uncheck"])
    backend._element_cache["chk1"] = wrapper

    assert backend.set_value("chk1", True) is True
    wrapper.check.assert_called_once()
    wrapper.uncheck.assert_not_called()


def test_set_value_unchecks_checkbox_for_falsy_value(backend):
    wrapper = MagicMock(spec=["set_focus", "check", "uncheck"])
    backend._element_cache["chk1"] = wrapper

    assert backend.set_value("chk1", False) is True
    wrapper.uncheck.assert_called_once()
    wrapper.check.assert_not_called()


def test_set_value_falls_back_to_set_text(backend):
    wrapper = MagicMock(spec=["set_focus", "set_text"])
    backend._element_cache["edit1"] = wrapper

    assert backend.set_value("edit1", 42) is True
    wrapper.set_text.assert_called_once_with("42")


def test_set_value_falls_back_to_click_when_no_known_method(backend):
    wrapper = MagicMock(spec=["set_focus", "click", "control_type"])
    backend._element_cache["weird1"] = wrapper

    assert backend.set_value("weird1", "x") is True
    wrapper.click.assert_called_once()


def test_set_value_returns_false_on_exception(backend):
    wrapper = MagicMock(spec=["set_focus", "select"])
    wrapper.select.side_effect = RuntimeError("boom")
    backend._element_cache["cmb1"] = wrapper

    assert backend.set_value("cmb1", "x") is False


# ── invoke ────────────────────────────────────────────────────

def test_invoke_not_in_cache_returns_false(backend):
    assert backend.invoke("nope") is False


def test_invoke_uses_invoke_method_when_available(backend):
    wrapper = MagicMock(spec=["set_focus", "invoke"])
    backend._element_cache["menu1"] = wrapper

    assert backend.invoke("menu1") is True
    wrapper.invoke.assert_called_once()


def test_invoke_falls_back_to_click(backend):
    wrapper = MagicMock(spec=["set_focus", "click"])
    backend._element_cache["item1"] = wrapper

    assert backend.invoke("item1") is True
    wrapper.click.assert_called_once()


def test_invoke_returns_false_on_exception(backend):
    wrapper = MagicMock(spec=["set_focus", "invoke"])
    wrapper.invoke.side_effect = RuntimeError("boom")
    backend._element_cache["menu1"] = wrapper

    assert backend.invoke("menu1") is False


# ── read_value ────────────────────────────────────────────────

def test_read_value_not_in_cache_returns_default_dict(backend):
    assert backend.read_value("nope") == {"text": "", "value": None, "state": None}


def test_read_value_reads_text_value_and_checked_state(backend):
    wrapper = MagicMock(spec=["window_text", "get_value", "is_checked"])
    wrapper.window_text.return_value = "Hello"
    wrapper.get_value.return_value = "the_value"
    wrapper.is_checked.return_value = True
    backend._element_cache["e1"] = wrapper

    result = backend.read_value("e1")

    assert result == {"text": "Hello", "value": "the_value", "state": "checked"}


def test_read_value_falls_back_to_text_when_no_get_value(backend):
    wrapper = MagicMock(spec=["window_text"])
    wrapper.window_text.return_value = "Just Text"
    backend._element_cache["e1"] = wrapper

    result = backend.read_value("e1")

    assert result == {"text": "Just Text", "value": "Just Text", "state": None}


def test_read_value_swallows_get_value_exception_and_falls_back_to_text(backend):
    wrapper = MagicMock(spec=["window_text", "get_value"])
    wrapper.window_text.return_value = "Fallback Text"
    wrapper.get_value.side_effect = RuntimeError("boom")
    backend._element_cache["e1"] = wrapper

    result = backend.read_value("e1")

    assert result == {"text": "Fallback Text", "value": "Fallback Text", "state": None}


def test_read_value_returns_default_dict_when_window_text_raises(backend):
    wrapper = MagicMock(spec=["window_text"])
    wrapper.window_text.side_effect = RuntimeError("boom")
    backend._element_cache["e1"] = wrapper

    result = backend.read_value("e1")

    assert result == {"text": "", "value": None, "state": None}
