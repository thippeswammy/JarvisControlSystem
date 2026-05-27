"""
Integration tests for the Agent, Multi-agent, and MCP execution pipeline.
Verifies that text -> NLU -> Planner -> plugin_skill -> AgentBus/MCPBus dispatch works perfectly.
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from jarvis.memory.memory_manager import MemoryManager
from jarvis.llm.llm_interface import LLMDecision
from jarvis.skills.skill_bus import SkillBus
from jarvis.brain.orchestrator import Orchestrator
from jarvis.agents.agent_bus import AgentBus
from jarvis.agents.agent_interface import AgentInterface
from jarvis.agents.agent_result import AgentResult
from jarvis.agents.memory.agent_local_memory import AgentLocalMemory
from jarvis.agents.memory.shared_context import SharedAgentContext
from jarvis.mcp.mcp_interface import MCPInterface
from jarvis.mcp.mcp_bus import MCPBus
from jarvis.skills.builtins.plugin_skill import run_agent, run_agent_pipeline, call_mcp_tool


class MockAgent(AgentInterface):
    def __init__(self, name="mock_agent", parallel_safe=True):
        self._name = name
        self._parallel_safe = parallel_safe
        self.calls = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def parallel_safe(self) -> bool:
        return self._parallel_safe

    def run(
        self,
        task: str,
        context: dict,
        local_memory: AgentLocalMemory,
        shared: SharedAgentContext,
    ) -> AgentResult:
        self.calls.append(task)
        local_memory.log_step(f"MockAgent task: {task}")
        return AgentResult(
            success=True,
            output=f"MockAgent output for task: {task}",
            agent_name=self._name,
            steps_taken=local_memory.exec_log
        )


class MockMCPAdapter(MCPInterface):
    def __init__(self, name="mock-mcp"):
        self._name = name
        self.calls = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def transport(self) -> str:
        return "stdio"

    def list_tools(self) -> list[dict]:
        return [
            {
                "name": "mock_tool",
                "description": "A mock tool",
                "params": {"type": "object"}
            }
        ]

    def call(self, tool: str, params: dict) -> dict:
        self.calls.append((tool, params))
        if tool == "mock_tool":
            return {"result": f"Mock tool called with: {params}"}
        return {"error": "unknown tool"}

    def health_check(self) -> bool:
        return True

    def shutdown(self) -> None:
        pass


class TestPluginPipeline(unittest.TestCase):

    def setUp(self):
        self._tmpfile = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmpfile.close()

        self.memory = MemoryManager(db_path=self._tmpfile.name)
        self.router = MagicMock()
        self.bus = SkillBus()

        # Manually register the plugin skills onto the skill bus
        self.bus.register(run_agent)
        self.bus.register(run_agent_pipeline)
        self.bus.register(call_mcp_tool)

        self.agent_bus = AgentBus(self.memory)
        self.mcp_bus = MCPBus()

        # Instantiate orchestrator
        self.orch = Orchestrator(
            memory=self.memory,
            router=self.router,
            bus=self.bus,
            agent_bus=self.agent_bus,
            mcp_bus=self.mcp_bus
        )

        from jarvis.pathfinding.graph_pathfinder import GraphPathfinder
        self.orch._pathfinder = GraphPathfinder(self.memory.get_db())
        self.memory.set_pathfinder(self.orch._pathfinder)

        # Register mock agents
        self.mock_agent = MockAgent(name="search_agent")
        self.mock_aggregator = MockAgent(name="aggregator_agent", parallel_safe=False)
        self.agent_bus.register(self.mock_agent)
        self.agent_bus.register(self.mock_aggregator)

        # Register mock MCP tools
        self.mock_mcp = MockMCPAdapter(name="filesystem")
        self.mcp_bus.register(self.mock_mcp)

    def tearDown(self):
        self.memory.close()
        try:
            os.unlink(self._tmpfile.name)
        except OSError:
            pass

    def test_single_agent_dispatch_pipeline(self):
        """Verify that a single agent decision routes and executes successfully."""
        self.router.decide.return_value = LLMDecision(
            type="agent",
            agent="search_agent",
            agent_task="find Python tutorials",
            message="Delegating to agent"
        )

        results = self.orch.process("ask search_agent to search for python tutorials", source="text")

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].success)
        self.assertIn("MockAgent output for task: find Python tutorials", results[0].message)
        self.assertEqual(self.mock_agent.calls, ["find Python tutorials"])

    def test_multi_agent_pipeline(self):
        """Verify that a multi-agent decision decomposes and executes task waves successfully."""
        self.router.decide.return_value = LLMDecision(
            type="multiagent",
            agent_tasks=[
                {"id": "t1", "agent": "search_agent", "task": "find Python tutorials"},
                {"id": "t2", "agent": "aggregator_agent", "task": "merge and summarize", "depends_on": ["t1"]}
            ],
            message="Running multiagent tasks"
        )

        results = self.orch.process("decomposing parallel tasks", source="text")

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].success)
        self.assertIn("MockAgent output for task: merge and summarize", results[0].message)
        self.assertEqual(self.mock_agent.calls, ["find Python tutorials"])
        self.assertEqual(self.mock_aggregator.calls, ["merge and summarize"])

    def test_mcp_tool_pipeline(self):
        """Verify that an MCP tool call decision routes and executes successfully."""
        self.router.decide.return_value = LLMDecision(
            type="mcp",
            mcp_server="filesystem",
            mcp_tool="mock_tool",
            mcp_params={"path": "notes.txt"},
            message="Calling MCP tool"
        )

        results = self.orch.process("read files via filesystem", source="text")

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].success)
        self.assertIn("Mock tool called with: {'path': 'notes.txt'}", results[0].message)
        self.assertEqual(self.mock_mcp.calls, [("mock_tool", {"path": "notes.txt"})])


if __name__ == "__main__":
    unittest.main()
