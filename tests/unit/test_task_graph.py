"""
Unit tests for jarvis.agents.task_graph
"""

import unittest
from jarvis.agents.task_graph import AgentTask, TaskGraph


class TestTaskGraph(unittest.TestCase):

    def test_agent_task_validation(self):
        """Verify that AgentTask validates its fields on initialization."""
        with self.assertRaises(ValueError):
            AgentTask(id="", agent="search", task="Search python news")

        with self.assertRaises(ValueError):
            AgentTask(id="task-1", agent="", task="Search python news")

        task = AgentTask(id="task-1", agent="search", task="Search python news")
        self.assertEqual(task.id, "task-1")
        self.assertEqual(task.agent, "search")
        self.assertEqual(task.task, "Search python news")
        self.assertEqual(task.depends_on, [])

    def test_task_graph_add_and_get(self):
        """Verify adding and retrieving tasks from a TaskGraph."""
        graph = TaskGraph()
        t1 = AgentTask(id="t1", agent="search", task="Search for news")
        t2 = AgentTask(id="t2", agent="writer", task="Write summary", depends_on=["t1"])

        graph.add_task(t1)
        graph.add_task(t2)

        self.assertEqual(len(graph.tasks), 2)
        self.assertEqual(graph.get_task("t1"), t1)
        self.assertEqual(graph.get_task("t2"), t2)

        with self.assertRaises(KeyError):
            graph.get_task("nonexistent")

    def test_cycle_detection(self):
        """Verify that cycles are correctly identified in TaskGraph."""
        graph = TaskGraph()
        t1 = AgentTask(id="t1", agent="agent1", task="Task 1")
        t2 = AgentTask(id="t2", agent="agent2", task="Task 2", depends_on=["t1"])
        graph.add_task(t1)
        graph.add_task(t2)

        # No cycles
        self.assertFalse(graph.has_cycles())

        # Self cycle
        graph_self_cycle = TaskGraph()
        ts = AgentTask(id="ts", agent="agent", task="Self cycle", depends_on=["ts"])
        graph_self_cycle.add_task(ts)
        self.assertTrue(graph_self_cycle.has_cycles())

        # Simple 2-node cycle
        graph_2_cycle = TaskGraph()
        ta = AgentTask(id="ta", agent="agentA", task="Task A", depends_on=["tb"])
        tb = AgentTask(id="tb", agent="agentB", task="Task B", depends_on=["ta"])
        graph_2_cycle.add_task(ta)
        graph_2_cycle.add_task(tb)
        self.assertTrue(graph_2_cycle.has_cycles())

        # Deep cycle (A -> B -> C -> A)
        graph_deep_cycle = TaskGraph()
        tc1 = AgentTask(id="tc1", agent="a", task="T1", depends_on=["tc3"])
        tc2 = AgentTask(id="tc2", agent="b", task="T2", depends_on=["tc1"])
        tc3 = AgentTask(id="tc3", agent="c", task="T3", depends_on=["tc2"])
        graph_deep_cycle.add_task(tc1)
        graph_deep_cycle.add_task(tc2)
        graph_deep_cycle.add_task(tc3)
        self.assertTrue(graph_deep_cycle.has_cycles())

    def test_execution_stages(self):
        """Verify that tasks are grouped into execution stages correctly."""
        graph = TaskGraph()
        # Stage 1: independent tasks
        t1 = AgentTask(id="t1", agent="search", task="Search A")
        t2 = AgentTask(id="t2", agent="vision", task="Vision B")
        # Stage 2: depends on Stage 1
        t3 = AgentTask(id="t3", agent="writer", task="Merge A and B", depends_on=["t1", "t2"])
        # Stage 3: depends on Stage 2
        t4 = AgentTask(id="t4", agent="notifier", task="Send email", depends_on=["t3"])

        graph.add_task(t1)
        graph.add_task(t2)
        graph.add_task(t3)
        graph.add_task(t4)

        stages = graph.get_execution_stages()
        self.assertEqual(len(stages), 3)

        # Stage 1
        self.assertEqual(set(t.id for t in stages[0]), {"t1", "t2"})
        # Stage 2
        self.assertEqual(set(t.id for t in stages[1]), {"t3"})
        # Stage 3
        self.assertEqual(set(t.id for t in stages[2]), {"t4"})

    def test_execution_stages_missing_dependency(self):
        """Verify handling of dependencies on tasks not present in the graph."""
        graph = TaskGraph()
        t1 = AgentTask(id="t1", agent="search", task="Task 1", depends_on=["missing_dep"])
        graph.add_task(t1)

        # A warning is logged, but the task is scheduled as Stage 1 since the dependency is missing
        stages = graph.get_execution_stages()
        self.assertEqual(len(stages), 1)
        self.assertEqual(stages[0][0].id, "t1")

    def test_execution_stages_raise_on_cycle(self):
        """Verify ValueError is raised when getting stages for a cyclic graph."""
        graph = TaskGraph()
        ta = AgentTask(id="ta", agent="agentA", task="Task A", depends_on=["tb"])
        tb = AgentTask(id="tb", agent="agentB", task="Task B", depends_on=["ta"])
        graph.add_task(ta)
        graph.add_task(tb)

        with self.assertRaises(ValueError):
            graph.get_execution_stages()

    def test_disconnected_orphan_node(self):
        """A fully isolated task (no deps, nothing depends on it) must coexist
        correctly alongside an unrelated dependency chain rather than being
        dropped or breaking stage resolution."""
        graph = TaskGraph()
        # Chain: t1 -> t2
        t1 = AgentTask(id="t1", agent="search", task="Search A")
        t2 = AgentTask(id="t2", agent="writer", task="Summarize A", depends_on=["t1"])
        # Fully disconnected orphan: no dependencies, no dependents
        orphan = AgentTask(id="orphan", agent="logger", task="Log heartbeat")

        graph.add_task(t1)
        graph.add_task(t2)
        graph.add_task(orphan)

        self.assertFalse(graph.has_cycles())

        stages = graph.get_execution_stages()
        # Orphan has zero dependencies, so it is scheduled immediately in stage 1
        self.assertEqual(len(stages), 2)
        self.assertEqual(set(t.id for t in stages[0]), {"t1", "orphan"})
        self.assertEqual(set(t.id for t in stages[1]), {"t2"})
        self.assertEqual(graph.get_task("orphan").depends_on, [])

    def test_multiple_disconnected_components(self):
        """Two entirely separate dependency chains with no edges between them
        must each resolve independently within the same graph, and the total
        stage count must be driven by the longest chain."""
        graph = TaskGraph()
        # Component A: a1 -> a2 (2 levels)
        a1 = AgentTask(id="a1", agent="agentA", task="A1")
        a2 = AgentTask(id="a2", agent="agentA", task="A2", depends_on=["a1"])
        # Component B: b1 -> b2 -> b3 (3 levels, unrelated to component A)
        b1 = AgentTask(id="b1", agent="agentB", task="B1")
        b2 = AgentTask(id="b2", agent="agentB", task="B2", depends_on=["b1"])
        b3 = AgentTask(id="b3", agent="agentB", task="B3", depends_on=["b2"])

        for t in (a1, a2, b1, b2, b3):
            graph.add_task(t)

        self.assertFalse(graph.has_cycles())
        stages = graph.get_execution_stages()
        self.assertEqual(len(stages), 3)
        self.assertEqual(set(t.id for t in stages[0]), {"a1", "b1"})
        self.assertEqual(set(t.id for t in stages[1]), {"a2", "b2"})
        self.assertEqual(set(t.id for t in stages[2]), {"b3"})
        self.assertEqual(sum(len(s) for s in stages), 5)

    def test_large_graph_scales_correctly(self):
        """Verify a 20-node layered DAG (1 root -> 10 workers -> 9 fan-in
        mergers) resolves into the correct stages, exercising the scheduler
        beyond trivial 2-3 node graphs."""
        graph = TaskGraph()

        root = AgentTask(id="root", agent="coordinator", task="Kick off")
        graph.add_task(root)

        # Level 1: 10 tasks depending directly on root
        level1_ids = [f"l1_{i}" for i in range(10)]
        for tid in level1_ids:
            graph.add_task(AgentTask(id=tid, agent="worker", task=f"Work {tid}", depends_on=["root"]))

        # Level 2: 9 tasks, each fanning in from two adjacent level-1 tasks
        level2_ids = []
        for i in range(9):
            tid = f"l2_{i}"
            level2_ids.append(tid)
            deps = [level1_ids[i], level1_ids[i + 1]]
            graph.add_task(AgentTask(id=tid, agent="merger", task=f"Merge {tid}", depends_on=deps))

        self.assertEqual(len(graph.tasks), 20)
        self.assertFalse(graph.has_cycles())

        stages = graph.get_execution_stages()
        self.assertEqual(len(stages), 3)
        self.assertEqual(set(t.id for t in stages[0]), {"root"})
        self.assertEqual(set(t.id for t in stages[1]), set(level1_ids))
        self.assertEqual(set(t.id for t in stages[2]), set(level2_ids))

        # Every task from the graph appears exactly once across all stages
        all_staged_ids = [t.id for stage in stages for t in stage]
        self.assertEqual(len(all_staged_ids), 20)
        self.assertEqual(set(all_staged_ids), set(t.id for t in graph.tasks))
