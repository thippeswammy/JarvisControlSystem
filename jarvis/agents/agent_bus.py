"""
Agent Bus
=========
Central bus that discovers, registers, and executes Jarvis autonomous agents.

Supports running agents sequentially, in parallel (via asyncio + thread pools),
and orchestrating full TaskGraph pipelines.
"""

import asyncio
import importlib
import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Type

from jarvis.agents.agent_interface import AgentInterface
from jarvis.agents.agent_result import AgentResult
from jarvis.agents.memory.agent_local_memory import AgentLocalMemory
from jarvis.agents.memory.shared_context import SharedAgentContext
from jarvis.agents.task_graph import AgentTask, TaskGraph

logger = logging.getLogger(__name__)

try:
    import yaml  # type: ignore[import-untyped]
except ImportError:
    yaml = None

_DEFAULT_CONFIG = (
    Path(__file__).parent.parent / "config" / "agents.yaml"
)


class FunctionalAgentWrapper(AgentInterface):
    """Wraps a simple function as a compliant AgentInterface agent."""

    def __init__(
        self,
        name: str,
        fn: Callable[..., Any],
        description: str = "",
        parallel_safe: bool = True,
        audit_required: bool = False,
    ) -> None:
        self._name = name
        self._fn = fn
        self._description = description
        self._parallel_safe = parallel_safe
        self._audit_required = audit_required

    @property
    def name(self) -> str:
        return self._name

    @property
    def parallel_safe(self) -> bool:
        return self._parallel_safe

    @property
    def description(self) -> str:
        return self._description

    @property
    def audit_required(self) -> bool:
        return self._audit_required

    def run(
        self,
        task: str,
        context: dict,
        local_memory: AgentLocalMemory,
        shared: SharedAgentContext,
    ) -> AgentResult:
        try:
            local_memory.log_step(f"Running agent function '{self._name}'")
            # Invoke the wrapped function
            res = self._fn(task, context, local_memory, shared)
            if isinstance(res, AgentResult):
                return res
            if isinstance(res, tuple) and len(res) == 2 and isinstance(res[0], bool):
                return AgentResult(
                    success=res[0],
                    output=str(res[1]),
                    agent_name=self._name,
                    steps_taken=local_memory.exec_log.copy(),
                )
            return AgentResult(
                success=True,
                output=str(res),
                agent_name=self._name,
                steps_taken=local_memory.exec_log.copy(),
            )
        except Exception as exc:
            logger.exception(f"Error in functional agent {self._name}: {exc}")
            local_memory.log_step(f"Execution failed: {exc}")
            return AgentResult(
                success=False,
                output=f"Error executing agent {self._name}: {exc}",
                agent_name=self._name,
                steps_taken=local_memory.exec_log.copy(),
            )


class AgentBus:
    """Discovers, registers, and dispatches calls to autonomous agents."""

    def __init__(self, memory_manager: Optional[Any] = None) -> None:
        self._memory_manager = memory_manager
        self._registry: Dict[str, AgentInterface] = {}
        self._discovered = False
        self._thread_pool = ThreadPoolExecutor(max_workers=10)

    # ── Discovery ────────────────────────────────────

    def discover(
        self,
        config_path: Optional[str] = None,
        external_dir: Optional[str] = None,
    ) -> int:
        """
        Load built-in and external agents from configuration and directory scanning.
        """
        if self._discovered:
            logger.debug("[AgentBus] Agents already discovered. Skipping.")
            return len(self._registry)
        # 1. Discover built-in agents
        self._discover_builtins()

        # 2. Load from YAML config
        loaded_yaml = self._discover_from_yaml(config_path)

        # 3. Load from external directory scanning
        loaded_external = self._discover_from_directory(external_dir)

        self._discovered = True
        logger.info(
            f"[AgentBus] Discovered {len(self._registry)} total agents: "
            f"{sorted(self._registry.keys())}"
        )
        return len(self._registry)

    def register(self, agent: AgentInterface) -> None:
        """Manually register an agent."""
        if agent.name in self._registry:
            existing = self._registry[agent.name]
            is_same = False
            if type(existing) is type(agent):
                if type(agent).__name__ == "FunctionalAgentWrapper":
                    is_same = getattr(existing, "_fn", None) == getattr(agent, "_fn", None)
                else:
                    is_same = True
            if is_same:
                logger.debug(f"[AgentBus] Re-registering identical agent: {agent.name!r}")
            else:
                logger.warning(f"[AgentBus] Overriding existing agent: {agent.name!r}")
        self._registry[agent.name] = agent
        logger.debug(f"[AgentBus] Registered agent: {agent.name!r}")

    # ── Execution ─────────────────────────────────────

    def run_single(self, name: str, task: str, context: dict) -> AgentResult:
        """Execute a single agent by name synchronously (thread-safe block)."""
        agent = self._registry.get(name)
        if agent is None:
            logger.error(f"[AgentBus] Agent not found: {name!r}")
            return AgentResult(
                success=False,
                output=f"Agent '{name}' not found.",
                agent_name=name,
            )

        local_mem = AgentLocalMemory(agent_name=name)
        shared_ctx = SharedAgentContext(self._memory_manager) if self._memory_manager else None

        from jarvis.agents.peer_review import PeerReviewAuditor
        auditor = PeerReviewAuditor(router=context.get("_router"))

        max_attempts = 2  # 1 initial + 1 regeneration attempt if audit fails
        current_task = task
        feedback = ""

        for attempt in range(1, max_attempts + 1):
            if feedback:
                current_task = (
                    f"{task}\n\n"
                    f"[PEER REVIEW AUDIT FEEDBACK]: The previous attempt failed validation. "
                    f"Please regenerate/correct the output according to this feedback: {feedback}"
                )

            try:
                result = agent.run(current_task, context, local_mem, shared_ctx)
            except Exception as exc:
                logger.exception(f"Unhandled exception in agent {name}: {exc}")
                return AgentResult(
                    success=False,
                    output=f"Unhandled exception running agent '{name}': {exc}",
                    agent_name=name,
                    steps_taken=local_mem.exec_log.copy(),
                )

            # If the run itself failed, return it immediately without auditing
            if not result.success:
                return result

            # If peer review is not required, return immediately
            if not getattr(agent, "audit_required", False):
                return result

            # Audit the output
            audit_res = auditor.audit(result.output, name)
            if audit_res.accepted:
                logger.info(f"[AgentBus] Peer review PASSED for agent '{name}' (confidence={audit_res.confidence})")
                return result
            else:
                logger.warning(f"[AgentBus] Peer review FAILED for agent '{name}': {audit_res.feedback}")
                feedback = audit_res.feedback
                local_mem.log_step(f"Peer review failed (attempt {attempt}): {feedback}")

        # If it failed all attempts
        logger.error(f"[AgentBus] Peer review failed after {max_attempts} attempts for agent '{name}'")
        return AgentResult(
            success=False,
            output=f"Peer review audit failed after {max_attempts} attempts. Feedback: {feedback}",
            agent_name=name,
            steps_taken=local_mem.exec_log.copy(),
        )

    async def run_parallel(
        self, tasks: List[Tuple[str, str]], context: dict
    ) -> List[AgentResult]:
        """
        Run multiple independent agent tasks concurrently in separate threads.
        """
        loop = asyncio.get_running_loop()
        futures = []
        for name, task_text in tasks:
            fut = loop.run_in_executor(
                self._thread_pool, self.run_single, name, task_text, context
            )
            futures.append(fut)
        return await asyncio.gather(*futures)

    async def run_pipeline(self, task_graph: TaskGraph, context: dict) -> List[AgentResult]:
        """
        Execute a full TaskGraph using the sequential+parallel hybrid model.

        Groups tasks into independent execution levels, executing tasks within
        each level in parallel, and sequentially chaining levels.
        """
        stages = task_graph.get_execution_stages()
        all_results: List[AgentResult] = []
        results_by_id: Dict[str, AgentResult] = {}

        # We enrich the context passed down so downstream agents have access to upstream outputs.
        pipeline_context = dict(context)
        pipeline_context["__pipeline_results__"] = results_by_id

        for idx, stage in enumerate(stages):
            logger.info(
                f"[AgentBus] Running pipeline stage {idx+1}/{len(stages)} with {len(stage)} tasks."
            )
            stage_tasks = []
            for task in stage:
                # Add prior results of dependencies to individual task context if needed
                stage_tasks.append((task.agent, task.task))

            # Run stage in parallel
            stage_results = await self.run_parallel(stage_tasks, pipeline_context)

            # Store results by task ID
            for task, res in zip(stage, stage_results):
                results_by_id[task.id] = res
                all_results.append(res)
                # Also log observe for shared global memory
                if res.success and self._memory_manager:
                    shared = SharedAgentContext(self._memory_manager)
                    shared.observe(
                        f"Agent {task.agent} completed task '{task.id}' with output: {res.output[:200]}..."
                    )

        return all_results

    # ── Catalog ──────────────────────────────────────

    def get_agent_catalog(self) -> str:
        """
        Build a formatted catalog of all registered agents and their descriptions
        for injection into LLM prompts.
        """
        lines: List[str] = []
        for name in sorted(self._registry.keys()):
            agent = self._registry[name]
            desc = getattr(agent, "description", "")
            if not desc and agent.__doc__:
                desc = agent.__doc__.strip().split("\n")[0]
            safe = "yes" if agent.parallel_safe else "no"
            lines.append(f"- {name}: {desc} (parallel safe: {safe})")
        return "\n".join(lines)

    # ── Private helpers ──────────────────────────────

    def _discover_builtins(self) -> None:
        """Register built-in agents."""
        try:
            from jarvis.agents.builtin.planner_agent import PlannerAgent
            self.register(PlannerAgent())
        except ImportError as exc:
            logger.debug(f"[AgentBus] Builtin PlannerAgent not found/imported: {exc}")

        try:
            from jarvis.agents.builtin.aggregator_agent import AggregatorAgent
            self.register(AggregatorAgent())
        except ImportError as exc:
            logger.debug(f"[AgentBus] Builtin AggregatorAgent not found/imported: {exc}")

        try:
            from jarvis.agents.builtin.brave_agent import BraveAgent
            self.register(BraveAgent())
        except ImportError as exc:
            logger.debug(f"[AgentBus] Builtin BraveAgent not found/imported: {exc}")

        try:
            from jarvis.agents.builtin.ui_windows_agent import UIWindowsAgent
            self.register(UIWindowsAgent())
        except ImportError as exc:
            logger.debug(f"[AgentBus] Builtin UIWindowsAgent not found/imported: {exc}")

    def _discover_from_yaml(self, config_path: Optional[str]) -> int:
        """Load agents listed in config/agents.yaml."""
        if yaml is None:
            logger.debug("[AgentBus] PyYAML not installed — config/agents.yaml loading skipped")
            return 0

        path = Path(config_path) if config_path else _DEFAULT_CONFIG
        if not path.exists():
            return 0

        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
                entries = data.get("agents", [])
                if entries is None:
                    entries = []
        except Exception as exc:
            logger.error(f"[AgentBus] Failed to load config {path}: {exc}")
            return 0

        if not isinstance(entries, list):
            logger.error("[AgentBus] config agents must be a list")
            return 0

        loaded = 0
        for entry in entries:
            try:
                name = entry.get("name")
                module_name = entry.get("module")
                fn_name = entry.get("fn", "run")
                description = entry.get("description", "")
                parallel_safe = entry.get("parallel_safe", True)

                if not name or not module_name:
                    continue

                # Dynamically import the module
                mod = importlib.import_module(module_name)
                fn = getattr(mod, fn_name)

                # Wrap and register
                wrapper = FunctionalAgentWrapper(
                    name=name,
                    fn=fn,
                    description=description,
                    parallel_safe=parallel_safe,
                )
                self.register(wrapper)
                loaded += 1
            except Exception as exc:
                logger.warning(
                    f"[AgentBus] Failed to load agent entry {entry.get('name')}: {exc}"
                )
        return loaded

    def _discover_from_directory(self, external_dir: Optional[str]) -> int:
        """Scan a directory for custom python agent files and dynamically load them."""
        # Find external directory
        dir_path = Path(external_dir) if external_dir else Path("agents_external")
        if not dir_path.exists() or not dir_path.is_dir():
            return 0

        # Ensure parent of external_dir is in sys.path so we can import it
        parent_str = str(dir_path.parent.resolve())
        if parent_str not in sys.path:
            sys.path.insert(0, parent_str)

        loaded = 0
        for p in dir_path.glob("*.py"):
            if p.name.startswith("_"):
                continue
            try:
                module_name = f"{dir_path.name}.{p.stem}"
                # If already loaded in sys.modules, reload it to allow hot reloading!
                if module_name in sys.modules:
                    mod = importlib.reload(sys.modules[module_name])
                else:
                    mod = importlib.import_module(module_name)

                # Check if it defines an Agent class inheriting from AgentInterface
                # or a conventional run function.
                agent_instance: Optional[AgentInterface] = None
                for attr_name in dir(mod):
                    attr = getattr(mod, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, AgentInterface)
                        and attr is not AgentInterface
                    ):
                        agent_instance = attr()
                        break

                if agent_instance is not None:
                    self.register(agent_instance)
                    loaded += 1
                elif hasattr(mod, "run"):
                    # Conventional run function
                    run_fn = getattr(mod, "run")
                    desc = getattr(mod, "__doc__", "") or f"External agent {p.stem}"
                    desc = desc.strip().split("\n")[0]
                    parallel_safe = getattr(mod, "PARALLEL_SAFE", True)
                    wrapper = FunctionalAgentWrapper(
                        name=p.stem,
                        fn=run_fn,
                        description=desc,
                        parallel_safe=parallel_safe,
                    )
                    self.register(wrapper)
                    loaded += 1

            except Exception as exc:
                logger.warning(f"[AgentBus] Failed to load external agent file {p.name}: {exc}")

        return loaded
