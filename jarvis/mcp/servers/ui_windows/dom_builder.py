"""
DOM Builder
===========
Processes raw UI automation node trees, enriches them with actions,
and computes structural deltas (diffs) between before/after UI states.
"""

from typing import Any, Optional, Dict, List
from jarvis.mcp.servers.ui_windows.element_context import get_actions_for_control_type


def enrich_dom(node: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively enriches raw DOM nodes with action information.
    Adds `actions_available` key based on control type.
    """
    if not node:
        return {}

    control_type = node.get("control_type", "Unknown")
    node["actions_available"] = get_actions_for_control_type(control_type)

    if "children" in node and isinstance(node["children"], list):
        enriched_children = []
        for child in node["children"]:
            enriched = enrich_dom(child)
            if enriched:
                enriched_children.append(enriched)
        node["children"] = enriched_children

    return node


def _flatten_dom(node: Dict[str, Any], flat_map: Dict[str, Dict[str, Any]]) -> None:
    """Recursively flattens a DOM tree into a map of element_id -> properties."""
    if not node or "element_id" not in node:
        return

    flat_map[node["element_id"]] = {
        "name": node.get("name", ""),
        "control_type": node.get("control_type", ""),
        "auto_id": node.get("auto_id", ""),
        "enabled": node.get("enabled", False),
        "visible": node.get("visible", False),
        # Treat value separately if needed, default to None
        "value": node.get("value", None)
    }

    if "children" in node and isinstance(node["children"], list):
        for child in node["children"]:
            _flatten_dom(child, flat_map)


def compute_dom_delta(before: Optional[Dict[str, Any]], after: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compare before and after DOM states and return a structural delta dictionary.

    Returns:
        Dict containing:
            - changed: bool
            - added: list of element_ids
            - removed: list of element_ids
            - modified: dict mapping element_id -> changed properties with before/after values
    """
    if not before:
        return {"changed": True, "added": [], "removed": [], "modified": {}}
    if not after:
        return {"changed": True, "added": [], "removed": [], "modified": {}}

    flat_before: Dict[str, Dict[str, Any]] = {}
    flat_after: Dict[str, Dict[str, Any]] = {}

    _flatten_dom(before, flat_before)
    _flatten_dom(after, flat_after)

    added = []
    removed = []
    modified = {}

    # Check for additions and modifications
    for eid, props in flat_after.items():
        if eid not in flat_before:
            added.append(eid)
        else:
            before_props = flat_before[eid]
            item_mods = {}
            for prop_name, new_val in props.items():
                old_val = before_props.get(prop_name)
                if old_val != new_val:
                    item_mods[prop_name] = {"before": old_val, "after": new_val}
            if item_mods:
                modified[eid] = item_mods

    # Check for removals
    for eid in flat_before:
        if eid not in flat_after:
            removed.append(eid)

    changed = bool(added or removed or modified)
    return {
        "changed": changed,
        "added": added,
        "removed": removed,
        "modified": modified
    }
