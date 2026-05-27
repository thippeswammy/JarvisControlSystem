"""
Capability Graph & Dynamic Skill Dependency Network
===================================================
Models action skills as a dependency network. This allows the Planner to autonomously
reason about what pre-requisite conditions must be established before executing a target action
(e.g., establishing a browser profile before clicking a DOM selector).
"""

import logging
from typing import Dict, Any, List, Set

logger = logging.getLogger(__name__)

class SkillNode:
    """Represents a single skill capability in the dependency graph."""
    def __init__(self, name: str, category: str, requires: List[str] = None, provides: List[str] = None):
        self.name = name
        self.category = category
        self.requires = requires or []  # Conditions required before running
        self.provides = provides or []  # State changes this action establishes

class CapabilityGraph:
    """Computes dependency pipelines dynamically for action sequences."""

    def __init__(self):
        self.nodes: Dict[str, SkillNode] = {}
        self._load_default_capabilities()

    def register_skill(self, node: SkillNode):
        self.nodes[node.name] = node
        logger.debug(f"[CapabilityGraph] Registered dynamic capability: {node.name}")

    def get_skill_path(self, target_skill: str) -> List[str]:
        """
        Runs a depth-first search on the capability graph to establish
        the list of prerequisite skills that must be run to fulfill the target.
        """
        if target_skill not in self.nodes:
            return [target_skill]

        visited: Set[str] = set()
        path: List[str] = []

        def dfs(name: str):
            if name in visited:
                return
            visited.add(name)
            node = self.nodes.get(name)
            if node:
                # Find other skills that satisfy its requirements
                for req in node.requires:
                    for prov_name, prov_node in self.nodes.items():
                        if req in prov_node.provides:
                            dfs(prov_name)
            path.append(name)

        dfs(target_skill)
        return path

    def _load_default_capabilities(self):
        """Loads core operating-system and browser skill dependencies."""
        default_skills = [
            # Desktop apps
            SkillNode(name="open_app", category="app", provides=["app_open", "window_focused"]),
            SkillNode(name="close_app", category="app", requires=["window_focused"]),
            SkillNode(name="activate_window", category="window", provides=["window_focused"]),
            SkillNode(name="type_text", category="keyboard", requires=["window_focused"]),
            SkillNode(name="press_key", category="keyboard", requires=["window_focused"]),
            
            # Browser
            SkillNode(name="open_brave_profile", category="browser", provides=["browser_open", "window_focused"]),
            SkillNode(name="switch_browser_tab", category="browser", requires=["browser_open"], provides=["tab_focused"]),
            SkillNode(name="extract_browser_dom_tree", category="browser", requires=["browser_open"]),
            SkillNode(name="click_browser_node", category="browser", requires=["browser_open", "tab_focused"]),
            SkillNode(name="fill_browser_node", category="browser", requires=["browser_open", "tab_focused"]),
            SkillNode(name="click_web_element", category="browser", requires=["browser_open"], provides=["web_clicked"]),
            
            # Desktop Navigation
            SkillNode(name="navigate_location", category="navigation", requires=["window_focused"], provides=["location_loaded"])
        ]
        for s in default_skills:
            self.register_skill(s)
