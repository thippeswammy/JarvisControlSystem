"""
Aggregator Agent
================
Builtin agent that aggregates results from multiple sub-agent executions into a
single, cohesive, and user-friendly final response.
"""

import logging
from typing import Any, Dict, List

from jarvis.agents.agent_interface import AgentInterface
from jarvis.agents.agent_result import AgentResult
from jarvis.agents.memory.agent_local_memory import AgentLocalMemory
from jarvis.agents.memory.shared_context import SharedAgentContext

logger = logging.getLogger(__name__)


class AggregatorAgent(AgentInterface):
    """Builtin Aggregator Agent that merges multiple sub-agent results."""

    @property
    def name(self) -> str:
        return "aggregator_agent"

    @property
    def description(self) -> str:
        return "Aggregates outputs from multiple sub-agents into a final summary."

    @property
    def parallel_safe(self) -> bool:
        return False  # Run as the final sequential step

    def run(
        self,
        task: str,
        context: dict,
        local_memory: AgentLocalMemory,
        shared: SharedAgentContext,
    ) -> AgentResult:
        local_memory.log_step("Starting aggregation of sub-agent results...")

        # 1. Retrieve sub-agent results
        results_by_id: Dict[str, AgentResult] = context.get("__pipeline_results__", {})
        if not results_by_id:
            # Fallback: look for generic results list
            results_by_id = {}

        if not results_by_id:
            local_memory.log_step("No sub-agent results found to aggregate.")
            return AgentResult(
                success=True,
                output="No task results were provided for aggregation.",
                agent_name=self.name,
                steps_taken=local_memory.exec_log.copy(),
            )

        # 2. Format findings for prompt/aggregation
        formatted_results: List[str] = []
        for t_id, res in results_by_id.items():
            status = "SUCCESS" if res.success else "FAILED"
            formatted_results.append(
                f"Task ID: {t_id}\n"
                f"Agent: {res.agent_name}\n"
                f"Status: {status}\n"
                f"Output: {res.output}\n"
                f"----------------------------------------"
            )
        results_block = "\n".join(formatted_results)

        # 3. Formulate system prompt
        system_prompt = (
            "You are the Jarvis Aggregator Agent.\n"
            "Your job is to read the original user request and the outputs of the sub-agents that ran, "
            "then synthesize them into a clean, concise, high-quality response for the user.\n"
            "Do NOT include technical JSON blocks or pipeline task IDs unless specifically asked.\n"
            f"Sub-agent Results:\n{results_block}\n"
        )

        # 4. Query LLM router
        router = context.get("llm_router") or context.get("router")
        if not router:
            try:
                from jarvis.llm.llm_router import LLMRouter
                router = LLMRouter.from_config()
            except Exception:
                pass

        if router:
            try:
                local_memory.log_step("Querying LLM to synthesize final response...")
                decision = router.decide(
                    prompt=f"Summarize and aggregate the results for the request: '{task}'",
                    context=system_prompt,
                )
                if decision and decision.message:
                    local_memory.log_step("LLM successfully synthesized response.")
                    return AgentResult(
                        success=True,
                        output=decision.message,
                        agent_name=self.name,
                        steps_taken=local_memory.exec_log.copy(),
                    )
            except Exception as exc:
                logger.warning(
                    f"[AggregatorAgent] LLM aggregation failed: {exc}. Falling back to text merge."
                )
                local_memory.log_step(f"LLM synthesis failed ({exc}). Falling back to text merge.")

        # Textual fallback aggregation
        summary_lines = [
            f"Here is a summary of the executed tasks for your request: '{task}'\n"
        ]
        for t_id, res in results_by_id.items():
            status = "✓" if res.success else "✗"
            summary_lines.append(f"{status} [{res.agent_name}] Task {t_id}: {res.output}")

        final_output = "\n".join(summary_lines)
        local_memory.log_step("Fallback textual merge complete.")
        return AgentResult(
            success=True,
            output=final_output,
            agent_name=self.name,
            steps_taken=local_memory.exec_log.copy(),
        )
