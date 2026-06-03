"""
Element Context
===============
Provides mapping from Windows UI element control types to their available
actions. This feeds the structured context that the LLM needs to know
what operations it can perform on each element.
"""

from typing import List, Dict

# Map control types to standard actions
CONTROL_TYPE_ACTIONS: Dict[str, List[str]] = {
    "Button": ["click", "invoke"],
    "Edit": ["type_text", "read_value", "set_value"],
    "Document": ["type_text", "read_value", "set_value"],
    "CheckBox": ["click", "set_value", "read_value"],  # checkbox toggle is achieved via click or set_value
    "RadioButton": ["click", "set_value", "read_value"],
    "ComboBox": ["click", "set_value", "read_value"],
    "ListItem": ["click", "read_value"],
    "TreeItem": ["click", "read_value"],
    "TabItem": ["click", "read_value"],
    "MenuItem": ["click", "invoke"],
    "Slider": ["set_value", "read_value"],
    "ScrollBar": ["set_value", "read_value"],
    "Text": ["read_value"],
    "Static": ["read_value"],
    "Pane": ["read_value"],
    "Group": ["read_value"],
    "Hyperlink": ["click", "invoke"],
    "Window": ["read_value"]
}


def get_actions_for_control_type(control_type: str) -> List[str]:
    """
    Get the list of actions available for a specific control type.
    Falls back to a default list if control type is not matched.
    """
    # Normalize by capitalizing the first character to match UIA standard names
    normalized = control_type.strip()
    if normalized:
        normalized = normalized[0].upper() + normalized[1:]

    # Return matched actions or default to click-only
    return CONTROL_TYPE_ACTIONS.get(normalized, ["click"])
