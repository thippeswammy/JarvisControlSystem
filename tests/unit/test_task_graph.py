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
