"""
Unit tests for jarvis.agents.agent_bus
"""

import asyncio
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

from jarvis.agents.agent_interface import AgentInterface
from jarvis.agents.agent_result import AgentResult
from jarvis.agents.agent_bus import AgentBus, FunctionalAgentWrapper
from jarvis.agents.memory.agent_local_memory import AgentLocalMemory
from jarvis.agents.memory.shared_context import SharedAgentContext
from jarvis.agents.task_graph import AgentTask, TaskGraph


class MockAgent(AgentInterface):
    def __init__(self, name="mock_agent", parallel_safe=True):
        self._name = name
        self._parallel_safe = parallel_safe
        self.run_called = 0
        self.last_task = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def parallel_safe(self) -> bool:
        return self._parallel_safe

    @property
    def description(self) -> str:
        return f"A Mock Agent named {self._name}"

    def run(
        self,
        task: str,
        context: dict,
        local_memory: AgentLocalMemory,
        shared: SharedAgentContext,
    ) -> AgentResult:
        self.run_called += 1
        self.last_task = task
        local_memory.log_step(f"Running task: {task}")
        return AgentResult(
            success=True,
            output=f"Processed: {task}",
            agent_name=self._name,
            steps_taken=local_memory.exec_log.copy()
        )


class TestAgentBus(unittest.TestCase):

    def test_agent_bus_init(self):
        """Verify initialization of AgentBus."""
        bus = AgentBus()
        self.assertFalse(bus._discovered)
        self.assertEqual(len(bus._registry), 0)

    def test_manual_registration(self):
        """Verify manual registration of agents."""
        bus = AgentBus()
        agent = MockAgent(name="agent1")
        bus.register(agent)
        self.assertIn("agent1", bus._registry)
        self.assertEqual(bus._registry["agent1"], agent)

    def test_run_single_success(self):
        """Verify executing a registered agent successfully."""
        bus = AgentBus()
        agent = MockAgent(name="agent1")
        bus.register(agent)

        res = bus.run_single("agent1", "do something", {"some": "context"})
        self.assertTrue(res.success)
        self.assertEqual(res.output, "Processed: do something")
        self.assertEqual(res.agent_name, "agent1")
        self.assertIn("Running task: do something", res.steps_taken[0])
        self.assertEqual(agent.run_called, 1)
        self.assertEqual(agent.last_task, "do something")

    def test_run_single_not_found(self):
        """Verify executing a non-existent agent returns failure result."""
        bus = AgentBus()
        res = bus.run_single("nonexistent", "do something", {})
        self.assertFalse(res.success)
        self.assertIn("not found", res.output)
        self.assertEqual(res.agent_name, "nonexistent")

    def test_run_single_exception(self):
        """Verify that AgentBus catches exceptions raised by agents."""
        bus = AgentBus()
        agent = MockAgent(name="broken")
        def broken_run(*args, **kwargs):
            raise RuntimeError("something went wrong")
        agent.run = broken_run
        bus.register(agent)

        res = bus.run_single("broken", "task", {})
        self.assertFalse(res.success)
        self.assertIn("something went wrong", res.output)

    def test_run_parallel(self):
        """Verify running independent tasks concurrently."""
        bus = AgentBus()
        agent1 = MockAgent(name="agent1")
        agent2 = MockAgent(name="agent2")
        bus.register(agent1)
        bus.register(agent2)

        async def run():
            tasks = [("agent1", "task A"), ("agent2", "task B")]
            return await bus.run_parallel(tasks, {})

        loop = asyncio.new_event_loop()
        try:
            results = loop.run_until_complete(run())
        finally:
            loop.close()

        self.assertEqual(len(results), 2)
        self.assertTrue(results[0].success)
        self.assertTrue(results[1].success)
        self.assertEqual(results[0].output, "Processed: task A")
        self.assertEqual(results[1].output, "Processed: task B")

    def test_run_pipeline(self):
        """Verify pipeline execution respects dependencies."""
        bus = AgentBus()
        agent1 = MockAgent(name="agent1")
        agent2 = MockAgent(name="agent2")
        bus.register(agent1)
        bus.register(agent2)

        graph = TaskGraph()
        t1 = AgentTask(id="task1", agent="agent1", task="Decompose problem")
        t2 = AgentTask(id="task2", agent="agent2", task="Solve decomposed", depends_on=["task1"])
        graph.add_task(t1)
        graph.add_task(t2)

        async def run():
            return await bus.run_pipeline(graph, {"init": True})

        loop = asyncio.new_event_loop()
        try:
            results = loop.run_until_complete(run())
        finally:
            loop.close()

        self.assertEqual(len(results), 2)
        self.assertTrue(results[0].success)
        self.assertTrue(results[1].success)
        self.assertEqual(results[0].output, "Processed: Decompose problem")
        self.assertEqual(results[1].output, "Processed: Solve decomposed")

    def test_get_agent_catalog(self):
        """Verify formatting of the agent catalog string."""
        bus = AgentBus()
        agent1 = MockAgent(name="agent1")
        agent2 = MockAgent(name="agent2", parallel_safe=False)
        bus.register(agent1)
        bus.register(agent2)

        catalog = bus.get_agent_catalog()
        self.assertIn("- agent1: A Mock Agent named agent1 (parallel safe: yes)", catalog)
        self.assertIn("- agent2: A Mock Agent named agent2 (parallel safe: no)", catalog)

    def test_functional_agent_wrapper(self):
        """Verify that FunctionalAgentWrapper correctly wraps a standard function."""
        def run_fn(task, context, local_mem, shared):
            local_mem.log_step("Inside function")
            return "Result text"

        wrapper = FunctionalAgentWrapper("func_agent", run_fn, "A functional agent", parallel_safe=True)
        self.assertEqual(wrapper.name, "func_agent")
        self.assertEqual(wrapper.description, "A functional agent")
        self.assertTrue(wrapper.parallel_safe)

        local_mem = AgentLocalMemory("func_agent")
        shared = MagicMock()
        res = wrapper.run("my task", {}, local_mem, shared)
        self.assertTrue(res.success)
        self.assertEqual(res.output, "Result text")
        self.assertIn("Inside function", res.steps_taken[1])
