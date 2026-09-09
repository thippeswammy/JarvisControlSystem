"""
tests/unit/test_dom_serializer.py
===================================
Unit tests for jarvis.mcp.servers.ui_windows.dom_serializer
(find_node_by_id, serialize_targeted, serialize_interactive,
serialize_full, serialize_dom).
"""
import pytest

from jarvis.mcp.servers.ui_windows.dom_serializer import (
    find_node_by_id,
    serialize_targeted,
    serialize_interactive,
    serialize_full,
    serialize_dom,
)

pytestmark = pytest.mark.unit


def _make_tree():
    return {
        "element_id": "root",
        "name": "Root Window",
        "control_type": "Window",
        "enabled": True,
        "actions_available": ["read_value"],
        "children": [
            {
                "element_id": "btn_ok",
                "name": "OK",
                "control_type": "Button",
                "auto_id": "okBtn",
                "enabled": True,
                "visible": True,
                "rect": {"x": 0, "y": 0, "w": 10, "h": 10},
                "actions_available": ["click", "invoke"],
                "children": [],
            },
            {
                "element_id": "txt_label",
                "name": "Some Label",
                "control_type": "Text",
                "enabled": True,
                "actions_available": ["read_value"],
                "children": [],
            },
        ],
    }


# ── find_node_by_id ───────────────────────────────────────────

def test_find_node_by_id_finds_root():
    tree = _make_tree()
    assert find_node_by_id(tree, "root") is tree


def test_find_node_by_id_finds_nested_child():
    tree = _make_tree()
    found = find_node_by_id(tree, "btn_ok")
    assert found is not None
    assert found["name"] == "OK"


def test_find_node_by_id_not_found_returns_none():
    tree = _make_tree()
    assert find_node_by_id(tree, "does_not_exist") is None


def test_find_node_by_id_none_input_returns_none():
    assert find_node_by_id(None, "anything") is None


# ── serialize_targeted ────────────────────────────────────────

def test_serialize_targeted_formats_all_fields():
    node = _make_tree()["children"][0]
    text = serialize_targeted(node)
    assert "Element: [btn_ok]" in text
    assert 'Name: "OK"' in text
    assert "ControlType: Button" in text
    assert 'AutoId: "okBtn"' in text
    assert "Actions available: click, invoke" in text


# ── serialize_interactive ─────────────────────────────────────

def test_serialize_interactive_includes_only_interactive_elements():
    tree = _make_tree()
    text = serialize_interactive(tree)
    assert "btn_ok" in text
    assert "txt_label" not in text  # only has read_value, not interactive


def test_serialize_interactive_no_matches_reports_none_found():
    tree = {"element_id": "root", "control_type": "Text", "actions_available": ["read_value"], "children": []}
    text = serialize_interactive(tree)
    assert text == "INTERACTIVE ELEMENTS:\n  (No interactive elements found)"


def test_serialize_interactive_truncates_when_over_budget():
    # Build many interactive nodes with long names so the running length exceeds a tiny max_chars.
    children = [
        {
            "element_id": f"btn_{i}",
            "name": "X" * 100,
            "control_type": "Button",
            "actions_available": ["click"],
            "children": [],
        }
        for i in range(20)
    ]
    tree = {"element_id": "root", "control_type": "Window", "actions_available": [], "children": children}
    text = serialize_interactive(tree, max_chars=200)
    assert "TRUNCATED" in text
    # Should not have emitted all 20 entries given the tiny budget.
    assert text.count("btn_") < 20


# ── serialize_full ────────────────────────────────────────────

def test_serialize_full_includes_indentation_for_nested_levels():
    tree = _make_tree()
    text = serialize_full(tree)
    lines = text.splitlines()
    assert lines[0].startswith("Window [Root Window]")
    # Children should be indented two spaces deeper than the root.
    child_lines = [l for l in lines if "btn_ok" in l]
    assert len(child_lines) == 1
    assert child_lines[0].startswith("  Button [OK]")


def test_serialize_full_truncates_when_over_budget():
    children = [
        {
            "element_id": f"c_{i}",
            "name": "Y" * 100,
            "control_type": "Text",
            "enabled": True,
            "actions_available": ["read_value"],
            "children": [],
        }
        for i in range(20)
    ]
    tree = {"element_id": "root", "name": "Root", "control_type": "Window", "enabled": True, "actions_available": [], "children": children}
    text = serialize_full(tree, max_chars=200)
    assert "TRUNCATED" in text


# ── serialize_dom (dispatcher) ────────────────────────────────

def test_serialize_dom_targeted_without_target_id_returns_error_string():
    tree = _make_tree()
    result = serialize_dom(tree, mode="TARGETED", target_id=None)
    assert result == "Error: TARGETED mode requires target_id"


def test_serialize_dom_targeted_missing_element_returns_not_found_string():
    tree = _make_tree()
    result = serialize_dom(tree, mode="TARGETED", target_id="ghost")
    assert result == "Element with ID 'ghost' not found"


def test_serialize_dom_targeted_found_element_delegates_to_serialize_targeted():
    tree = _make_tree()
    result = serialize_dom(tree, mode="TARGETED", target_id="btn_ok")
    assert result == serialize_targeted(tree["children"][0])


def test_serialize_dom_interactive_only_delegates():
    tree = _make_tree()
    assert serialize_dom(tree, mode="INTERACTIVE_ONLY") == serialize_interactive(tree)


def test_serialize_dom_defaults_to_full_for_unrecognized_mode():
    tree = _make_tree()
    # Anything other than TARGETED/INTERACTIVE_ONLY falls through to full serialization.
    assert serialize_dom(tree, mode="BOGUS_MODE") == serialize_full(tree)


def test_serialize_dom_mode_is_case_insensitive():
    tree = _make_tree()
    assert serialize_dom(tree, mode="interactive_only") == serialize_interactive(tree)
