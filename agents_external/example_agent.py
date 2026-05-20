import logging
from jarvis.agents.agent_interface import AgentInterface
from jarvis.agents.agent_result import AgentResult
from jarvis.agents.memory.agent_local_memory import AgentLocalMemory
from jarvis.agents.memory.shared_context import SharedAgentContext

logger = logging.getLogger(__name__)


class ExampleAgent(AgentInterface):
    """
    ExampleAgent
    ============
    A reference external agent demonstrating local per-agent episodic/scratchpad memory
    and shared global graph/world state memory interaction.
    """

    @property
    def name(self) -> str:
        return "example_agent"

    @property
    def parallel_safe(self) -> bool:
        return True

    @property
    def description(self) -> str:
        return "Reference external agent demonstrating local + shared memory"

    def run(
        self,
        task: str,
        context: dict,
        local_memory: AgentLocalMemory,
        shared: SharedAgentContext,
    ) -> AgentResult:
        local_memory.log_step("Initializing reference agent run...")
        
        # Save note into local scratchpad memory
        local_memory.note("active_task", task)
        local_memory.log_step(f"Recorded task in local scratchpad: {task!r}")

        # Interact with global shared context if available
        if shared:
            local_memory.log_step("Querying global shared context...")
            recent_facts = shared.recall("system state", limit=3)
            local_memory.log_step(f"Recalled {len(recent_facts)} global context facts.")
            
            # Save a confirmed observation back into the shared knowledge base
            shared.observe(
                fact=f"ExampleAgent executed task {task!r} successfully",
                confidence=0.95
            )
            local_memory.log_step("Logged execution fact back into global memory.")
        else:
            local_memory.log_step("Global shared context not available (running standalone/mock).")

        local_memory.log_step("Finalizing execution...")
        output = f"Echoing back task: '{task}'. I successfully demonstrated Agent Local + Shared Memory!"
        
        # Record this run in episodic log
        local_memory.log_episode(command=task, success=True, result=output)

        return AgentResult(
            success=True,
            output=output,
            agent_name=self.name,
            steps_taken=local_memory.exec_log.copy(),
            data={"task": task, "local_scratchpad": local_memory.scratchpad}
        )


def handle_slash_example_agent(args, session, gateway) -> str:
    """Slash command handler for /example_agent."""
    task = " ".join(args) if args else "default ping task"
    agent_bus = getattr(gateway, "agent_bus", None)
    if not agent_bus:
        return "❌ AgentBus not loaded on the gateway."
        
    logger.info(f"[example_agent] Slash command invoked for task: {task!r}")
    res = agent_bus.run_single("example_agent", task, {"router": gateway.router})
    
    steps_str = "\n".join(f"  ● {s}" for s in res.steps_taken)
    return (
        f"🟢 **[ExampleAgent] Slash Handler executed!**\n"
        f"**Task:** {task}\n"
        f"**Output:** {res.output}\n"
        f"**Steps Taken:**\n{steps_str}"
    )


# Automatically self-register custom slash command when module is discovered
try:
    from jarvis.gateway.slash_registry import SlashRegistry
    SlashRegistry.register(
        cmd="/example_agent",
        handler=handle_slash_example_agent,
        description="Directly invoke the reference ExampleAgent with a task",
        category="agent"
    )
except Exception as e:
    logger.warning(f"Failed to auto-register /example_agent slash command: {e}")
