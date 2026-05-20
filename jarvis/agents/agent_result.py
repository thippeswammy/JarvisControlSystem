"""
Agent Result
============
Dataclass returned by every agent's ``run()`` method.

Provides a uniform envelope so the orchestrator can inspect
success/failure, output text, and execution trace regardless
of which agent produced the result.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentResult:
    """Outcome produced by an agent execution."""

    success: bool
    output: str = ""
    agent_name: str = ""
    steps_taken: list[str] = field(default_factory=list)
    data: Any = None
