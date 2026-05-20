"""
Task Graph
==========
Represents a dependency graph of agent tasks, allowing topological sorting,
cycle detection, and grouping tasks into parallelizable execution levels.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set

logger = logging.getLogger(__name__)


@dataclass
class AgentTask:
    """A single task delegated to a specific agent, with optional dependencies."""

    id: str
    agent: str
    task: str
    depends_on: List[str] = field(default_factory=list)  # IDs of tasks this task depends on

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("AgentTask must have a non-empty 'id'.")
        if not self.agent:
            raise ValueError("AgentTask must specify an 'agent'.")


@dataclass
class TaskGraph:
    """A collection of AgentTasks forming a directed acyclic dependency graph (DAG)."""

    tasks: List[AgentTask] = field(default_factory=list)

    def add_task(self, task: AgentTask) -> None:
        """Add a task to the graph."""
        self.tasks.append(task)

    def get_task(self, task_id: str) -> AgentTask:
        """Retrieve a task by ID."""
        for t in self.tasks:
            if t.id == task_id:
                return t
        raise KeyError(f"Task with ID {task_id!r} not found in graph.")

    def has_cycles(self) -> bool:
        """Return True if the dependency graph contains any cycles (deadlocks)."""
        adj: Dict[str, List[str]] = {t.id: t.depends_on for t in self.tasks}
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for neighbor in adj.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.remove(node)
            return False

        for t in self.tasks:
            if t.id not in visited:
                if dfs(t.id):
                    return True
        return False

    def get_execution_stages(self) -> List[List[AgentTask]]:
        """
        Group tasks into sequential execution stages/levels.

        Each stage contains tasks that are completely independent of each other
        and whose dependencies have been satisfied in prior stages.

        Returns
        -------
        List[List[AgentTask]]:
            A list of execution stages, where each stage is a list of AgentTasks
            to be executed in parallel.

        Raises
        ------
        ValueError:
            If the graph has cycles (cannot be topologically sorted).
        """
        if self.has_cycles():
            raise ValueError("Cannot resolve execution stages: graph contains cycles/deadlocks.")

        # Mapping task ID to actual AgentTask object
        task_map = {t.id: t for t in self.tasks}

        # Build dependency structures
        in_degree: Dict[str, int] = {}
        adj: Dict[str, List[str]] = {t.id: [] for t in self.tasks}

        for t in self.tasks:
            in_degree[t.id] = len(t.depends_on)
            for dep in t.depends_on:
                if dep in adj:
                    adj[dep].append(t.id)
                else:
                    # Dependency ID is not in graph — we count it as satisfied
                    # or missing. Let's log a warning and decrement in_degree.
                    logger.warning(
                        f"Task {t.id!r} depends on non-existent task {dep!r}."
                    )
                    in_degree[t.id] -= 1

        stages: List[List[AgentTask]] = []
        # Find all nodes with 0 in-degree to start
        current_queue = [t_id for t_id, deg in in_degree.items() if deg <= 0]

        while current_queue:
            stage_tasks: List[AgentTask] = []
            next_queue: List[str] = []

            for node in current_queue:
                stage_tasks.append(task_map[node])
                for neighbor in adj.get(node, []):
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        next_queue.append(neighbor)

            stages.append(stage_tasks)
            current_queue = next_queue

        # Double check we didn't miss anything (e.g. isolated cycle)
        processed = sum(len(stage) for stage in stages)
        if processed < len(self.tasks):
            raise ValueError("Dependency resolution failed due to unresolved cycles.")

        return stages
