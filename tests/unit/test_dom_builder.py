"""
tests/unit/test_dom_builder.py
================================
Unit tests for jarvis.mcp.servers.ui_windows.dom_builder
(enrich_dom, compute_dom_delta).
"""
import pytest

from jarvis.mcp.servers.ui_windows.dom_builder import enrich_dom, compute_dom_delta

pytestmark = pytest.mark.unit


# ── enrich_dom ────────────────────────────────────────────────

def test_enrich_dom_adds_actions_for_known_control_type():
    node = {"element_id": "btn_1", "control_type": "Button", "name": "OK"}
    result = enrich_dom(node)
    assert result["actions_available"] == ["click", "invoke"]


def test_enrich_dom_empty_dict_returns_empty_dict():
    assert enrich_dom({}) == {}


def test_enrich_dom_none_returns_empty_dict():
    assert enrich_dom(None) == {}


def test_enrich_dom_missing_control_type_defaults_to_unknown_actions():
    node = {"element_id": "x1", "name": "mystery"}
    result = enrich_dom(node)
    # "Unknown" is not in CONTROL_TYPE_ACTIONS, so it falls back to ["click"]
    assert result["actions_available"] == ["click"]


def test_enrich_dom_recurses_into_children():
    node = {
        "element_id": "root",
        "control_type": "Window",
        "children": [
            {"element_id": "c1", "control_type": "Button"},
            {"element_id": "c2", "control_type": "Edit"},
        ],
    }
    result = enrich_dom(node)
    assert result["actions_available"] == ["read_value"]
    assert result["children"][0]["actions_available"] == ["click", "invoke"]
    assert result["children"][1]["actions_available"] == ["type_text", "read_value", "set_value"]


def test_enrich_dom_filters_out_falsy_children():
    node = {
        "element_id": "root",
        "control_type": "Window",
        "children": [None, {}, {"element_id": "c1", "control_type": "Button"}],
    }
    result = enrich_dom(node)
    # None and {} enrich to {} which is falsy and dropped from the list
    assert len(result["children"]) == 1
    assert result["children"][0]["element_id"] == "c1"


def test_enrich_dom_malformed_children_not_a_list_left_untouched():
    node = {"element_id": "root", "control_type": "Window", "children": "not-a-list"}
    result = enrich_dom(node)
    # children key exists but isn't a list -> the isinstance guard skips processing
    assert result["children"] == "not-a-list"
    assert result["actions_available"] == ["read_value"]


# ── compute_dom_delta ─────────────────────────────────────────

def test_compute_dom_delta_before_none_reports_changed_true_but_empty_lists():
    result = compute_dom_delta(None, {"element_id": "root", "control_type": "Window"})
    assert result == {"changed": True, "added": [], "removed": [], "modified": {}}


def test_compute_dom_delta_after_none_reports_changed_true_but_empty_lists():
    result = compute_dom_delta({"element_id": "root", "control_type": "Window"}, None)
    assert result == {"changed": True, "added": [], "removed": [], "modified": {}}


def test_compute_dom_delta_no_changes_between_identical_trees():
    tree = {
        "element_id": "root",
        "name": "Root",
        "control_type": "Window",
        "auto_id": "",
        "enabled": True,
        "visible": True,
        "children": [
            {"element_id": "c1", "name": "Child", "control_type": "Button", "auto_id": "b1", "enabled": True, "visible": True},
        ],
    }
    # Use separate (but equal) dict instances for before/after to prove real comparison.
    before = {**tree, "children": [dict(tree["children"][0])]}
    after = {**tree, "children": [dict(tree["children"][0])]}
    result = compute_dom_delta(before, after)
    assert result["changed"] is False
    assert result["added"] == []
    assert result["removed"] == []
    assert result["modified"] == {}


def test_compute_dom_delta_detects_added_and_removed_elements():
    before = {
        "element_id": "root",
        "children": [{"element_id": "c1", "name": "OldChild"}],
    }
    after = {
        "element_id": "root",
        "children": [{"element_id": "c2", "name": "NewChild"}],
    }
    result = compute_dom_delta(before, after)
    assert result["changed"] is True
    assert result["added"] == ["c2"]
    assert result["removed"] == ["c1"]
    assert result["modified"] == {}


def test_compute_dom_delta_detects_modified_property():
    before = {"element_id": "root", "name": "Old Name", "enabled": True}
    after = {"element_id": "root", "name": "New Name", "enabled": True}
    result = compute_dom_delta(before, after)
    assert result["changed"] is True
    assert result["added"] == []
    assert result["removed"] == []
    assert result["modified"] == {
        "root": {"name": {"before": "Old Name", "after": "New Name"}}
    }


def test_compute_dom_delta_root_missing_element_id_yields_no_flattened_nodes():
    # _flatten_dom bails out before recursing into children when the node
    # itself lacks "element_id" -- so descendants are never captured either.
    before = {"name": "no id here", "children": [{"element_id": "c1", "name": "orphaned"}]}
    after = {"name": "no id here", "children": [{"element_id": "c1", "name": "orphaned"}]}
    result = compute_dom_delta(before, after)
    assert result == {"changed": False, "added": [], "removed": [], "modified": {}}
