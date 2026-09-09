"""
tests/unit/test_element_context.py
====================================
Unit tests for jarvis.mcp.servers.ui_windows.element_context
(get_actions_for_control_type).
"""
import pytest

from jarvis.mcp.servers.ui_windows.element_context import (
    get_actions_for_control_type,
    CONTROL_TYPE_ACTIONS,
)

pytestmark = pytest.mark.unit


def test_get_actions_known_control_type_button():
    assert get_actions_for_control_type("Button") == ["click", "invoke"]


def test_get_actions_known_control_type_edit():
    assert get_actions_for_control_type("Edit") == ["type_text", "read_value", "set_value"]


def test_get_actions_unmatched_control_type_defaults_to_click():
    assert get_actions_for_control_type("Unknown") == ["click"]


def test_get_actions_normalizes_lowercase_input():
    # "button" (lowercase) should be capitalized to "Button" and matched.
    assert get_actions_for_control_type("button") == ["click", "invoke"]


def test_get_actions_normalizes_all_caps_input():
    # "BUTTON" -> first char upper + rest unchanged -> "BUTTON" (not "Button"), so it
    # actually does NOT match the "Button" key; only the first character is touched.
    assert get_actions_for_control_type("BUTTON") == ["click"]


def test_get_actions_empty_string_defaults_to_click():
    assert get_actions_for_control_type("") == ["click"]


def test_get_actions_strips_surrounding_whitespace():
    # strip() removes the leading/trailing whitespace before capitalization,
    # so "  Button  " normalizes to "Button" and matches the known key.
    assert get_actions_for_control_type("  Button  ") == ["click", "invoke"]


def test_get_actions_whitespace_only_string_defaults_to_click():
    # strip() reduces whitespace-only input to "", which is falsy, so the
    # capitalization branch is skipped and it falls back to the default.
    assert get_actions_for_control_type("   ") == ["click"]


def test_get_actions_returns_the_same_list_object_from_the_map():
    # get_actions_for_control_type returns the actual list stored in
    # CONTROL_TYPE_ACTIONS rather than a defensive copy. Mutating the
    # result therefore corrupts the shared mapping for future callers.
    result = get_actions_for_control_type("Slider")
    assert result is CONTROL_TYPE_ACTIONS["Slider"]
    result.append("mutated")
    assert get_actions_for_control_type("Slider") == ["set_value", "read_value", "mutated"]
    # Clean up the shared module-level state so this test doesn't poison others.
    CONTROL_TYPE_ACTIONS["Slider"].remove("mutated")
