"""
DOM Serializer
==============
Converts structured UI DOM trees into concise, LLM-friendly text formats.
Supports three modes: FULL (indented tree), INTERACTIVE_ONLY (filtered flat list),
and TARGETED (details of a specific element). Enforces strict length/token bounds.
"""

from typing import Any, Optional, Dict, List


def find_node_by_id(node: Dict[str, Any], target_id: str) -> Optional[Dict[str, Any]]:
    """Helper to find a node by its element_id in a DOM tree."""
    if not node:
        return None
    if node.get("element_id") == target_id:
        return node
    for child in node.get("children", []):
        found = find_node_by_id(child, target_id)
        if found:
            return found
    return None


def serialize_targeted(node: Dict[str, Any]) -> str:
    """Format single element properties as text."""
    lines = [
        f"Element: [{node.get('element_id')}]",
        f"  Name: \"{node.get('name')}\"",
        f"  ControlType: {node.get('control_type')}",
        f"  AutoId: \"{node.get('auto_id')}\"",
        f"  Enabled: {node.get('enabled')}",
        f"  Visible: {node.get('visible')}",
        f"  Rect: {node.get('rect')}",
        f"  Actions available: {', '.join(node.get('actions_available', []))}"
    ]
    return "\n".join(lines)


def _collect_interactive(node: Dict[str, Any], results: List[Dict[str, Any]]) -> None:
    """Recursively collect interactive nodes."""
    actions = node.get("actions_available", [])
    # Interactive if it has actions other than read_value
    is_interactive = any(act in {"click", "type_text", "set_value", "invoke"} for act in actions)
    if is_interactive:
        results.append(node)
    for child in node.get("children", []):
        _collect_interactive(child, results)


def serialize_interactive(dom_tree: Dict[str, Any], max_chars: int = 15000) -> str:
    """Serialize only elements that can be clicked, typed, or invoked."""
    results: List[Dict[str, Any]] = []
    _collect_interactive(dom_tree, results)

    lines = ["INTERACTIVE ELEMENTS:"]
    for node in results:
        actions = node.get("actions_available", [])
        line = f"  [{node.get('element_id')}]  {node.get('control_type')} \"{node.get('name')}\" → {', '.join(actions)}"
        
        # Check size limit
        current_len = sum(len(l) for l in lines) + len(lines)
        if current_len + len(line) + 50 > max_chars:
            lines.append("  ... [TRUNCATED due to token budget] ...")
            break
        lines.append(line)

    if len(lines) == 1:
        lines.append("  (No interactive elements found)")

    return "\n".join(lines)


def serialize_full(dom_tree: Dict[str, Any], max_chars: int = 15000) -> str:
    """Serialize the full tree with indentation showing hierarchy."""
    lines: List[str] = []

    def _helper(node: Dict[str, Any], level: int) -> bool:
        eid = node.get("element_id")
        name = node.get("name", "")
        ct = node.get("control_type", "Unknown")
        enabled = str(node.get("enabled", False)).lower()
        actions = node.get("actions_available", [])

        indent = "  " * level
        line_start = f"{indent}{ct} [{name}]"
        # Pad with spaces to align IDs and actions nicely
        pad_len = max(2, 40 - len(line_start))
        line = f"{line_start}{' ' * pad_len}id={eid}  enabled={enabled}  actions={actions}"

        current_len = sum(len(l) for l in lines) + len(lines)
        if current_len + len(line) + 50 > max_chars:
            lines.append("... [TRUNCATED due to token budget] ...")
            return False

        lines.append(line)

        for child in node.get("children", []):
            if not _helper(child, level + 1):
                return False
        return True

    _helper(dom_tree, 0)
    return "\n".join(lines)


def serialize_dom(dom_tree: Dict[str, Any], mode: str = "FULL", target_id: Optional[str] = None, max_chars: int = 15000) -> str:
    """
    Main entry point for serializing a DOM tree.
    """
    mode_upper = mode.upper()
    if mode_upper == "TARGETED":
        if not target_id:
            return "Error: TARGETED mode requires target_id"
        node = find_node_by_id(dom_tree, target_id)
        if not node:
            return f"Element with ID '{target_id}' not found"
        return serialize_targeted(node)

    if mode_upper == "INTERACTIVE_ONLY":
        return serialize_interactive(dom_tree, max_chars)

    return serialize_full(dom_tree, max_chars)
