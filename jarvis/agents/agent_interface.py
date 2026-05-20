"""
Agent Interface
===============
Abstract base class defining the contract for Jarvis autonomous agents.
"""

from abc import ABC, abstractmethod
from typing import Any

from jarvis.agents.agent_result import AgentResult
from jarvis.agents.memory.agent_local_memory import AgentLocalMemory
from jarvis.agents.memory.shared_context import SharedAgentContext


class AgentInterface(ABC):
    """
    Abstract base class for all Jarvis agents.

    Agents are discoverable, configurable sub-routines that the LLM planner
    can delegate tasks to.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the agent."""

    @property
    def parallel_safe(self) -> bool:
        """Whether this agent is safe to run concurrently with other agents.

        Defaults to True. Agents modifying global state should return False.
        """
        return True

    @abstractmethod
    def run(
        self,
        task: str,
        context: dict,
        local_memory: AgentLocalMemory,
        shared: SharedAgentContext,
    ) -> AgentResult:
        """
        Execute the agent's logic for the specified task.

        Parameters
        ----------
        task:
            The instruction or goal for this agent.
        context:
            Execution context containing session, config, or helper objects.
        local_memory:
            Ephemeral local memory/scratchpad store for this agent run.
        shared:
            Shared global memory wrapper for writing observes/recalls.

        Returns
        -------
        AgentResult:
            The uniform result envelope containing success status, output, and trace.
        """
