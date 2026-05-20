# Custom External Agents for Jarvis AI OS

Jarvis supports plug-in based autonomous agents. You can add new agents by simply dropping a Python file into this directory (`agents_external/`). Jarvis will dynamically discover, register, and make them available to both the LLM Unified Planner and custom slash commands.

## How to implement a Custom Agent

There are two supported ways to implement an agent:

### 1. Class-based implementation (Inheriting `AgentInterface`)
Create a Python class that inherits from `jarvis.agents.agent_interface.AgentInterface`:

```python
from jarvis.agents.agent_interface import AgentInterface
from jarvis.agents.agent_result import AgentResult
from jarvis.agents.memory.agent_local_memory import AgentLocalMemory
from jarvis.agents.memory.shared_context import SharedAgentContext

class MyCustomAgent(AgentInterface):
    @property
    def name(self) -> str:
        return "my_custom_agent"

    @property
    def parallel_safe(self) -> bool:
        return True

    @property
    def description(self) -> str:
        return "A custom agent that performs high-level cognitive automation."

    def run(
        self,
        task: str,
        context: dict,
        local_memory: AgentLocalMemory,
        shared: SharedAgentContext,
    ) -> AgentResult:
        # 1. Log steps to agent's isolated local memory
        local_memory.log_step("Starting my custom task...")
        
        # 2. Recall or query global shared context
        recent_facts = shared.recall("user preferences")
        
        # 3. Perform execution logic
        # ...
        
        # 4. Save learned facts back into global shared context
        shared.observe("custom agent successfully processed user request")
        
        return AgentResult(
            success=True,
            output="Task finished successfully!",
            agent_name=self.name,
            steps_taken=local_memory.exec_log
        )
```

### 2. Functional-based implementation
Define a conventional `run` function in your python module. Jarvis will wrap it inside a functional wrapper:

```python
"""Description of your agent that will be parsed as its docstring description."""

PARALLEL_SAFE = True  # Optional. Defaults to True.

def run(task: str, context: dict, local_memory, shared) -> str:
    local_memory.log_step("Running functional agent...")
    return "Output string"
```

## Hot-Reloading

You can run the `/reload` command in the Jarvis CLI or Telegram chat to reload all external agents and skills instantly without restarting the gateway daemon.
