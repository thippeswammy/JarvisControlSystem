# Implementation Plan — Jarvis Agents + MCP + Plugin Architecture v2

## Goal
Extend the Jarvis AI OS into a fully extensible system where:
- **Agents** are autonomous sub-routines the LLM can delegate tasks to, running in a **Hybrid Concurrency Model** (sequential planning + parallel execution + sequential aggregation).
- **MCP (Model Context Protocol)** tools give Jarvis access to external resources via **both stdio and HTTP/SSE transports**.
- **Skills & Tools** can be added by dropping a file — no code changes needed.
- **Custom Slash Commands** (`/commands`) are pluggable — any skill or agent registers its own `/cmd`.
- **Hybrid Memory Architecture** — each agent has local episodic/scratchpad memory, plus all agents share a global MemoryManager (vector DB, knowledge graph, world model).
- **Planner** dynamically discovers what's available and includes it in LLM context so the LLM fully decides how to route.

---

## Architecture Overview

```
User Input
    │
    ▼
Gateway (slash_handler / TUI / Telegram / CLI)
    │
    ├─ /slash commands ──► SlashRegistry  (dynamic, pluggable)
    │      /spin <agent>            spawn a single agent
    │      /multiagents <a1> <a2>   spawn agents in parallel
    │      /AgentName <task>        shorthand invoke any agent
    │      /skills / /agents / /mcp / /tool / /reload
    │
    ▼
Orchestrator → NLU → Planner
                        │
            ┌─── Planner Agent (sequential) ───┐
            │    Understands full intent        │
            │    Decomposes into sub-tasks      │
            └───────────────┬───────────────────┘
                            │
            ┌───────────────▼──────────────────────────┐
            │        Parallel Task Runner              │
            │  ┌──────────┬──────────┬──────────┐     │
            │  │ Search   │ Vision   │ Memory   │ ... │
            │  │ Agent    │ Agent    │ Agent    │     │
            │  └──────────┴──────────┴──────────┘     │
            └───────────────┬──────────────────────────┘
                            │  (all results collected)
            ┌───────────────▼───────────────────┐
            │      Aggregator Agent (seq)       │
            │  Merges results, resolves conflicts│
            └───────────────┬───────────────────┘
                            │
            ┌───────────────▼────────┐
            │   SkillBus / MCPBus    │
            │   Final skill dispatch │
            └────────────────────────┘
```

---

## Decisions Locked In

| Decision | Choice |
|----------|--------|
| MCP Transport | **Both** stdio subprocess + HTTP/SSE |
| Agent Concurrency | **Hybrid**: Sequential Planner → Parallel Tasks → Sequential Aggregator |
| Agent Memory | **Hybrid**: Local per-agent memory + Shared global MemoryManager |

---

## Hybrid Concurrency Model (Detailed)

### Stage 1 — Planner Agent (Sequential)
The LLM first analyzes the full user intent and decomposes it into a task graph: which sub-tasks are **independent** (run in parallel) vs. **dependent** (must run sequentially).

### Stage 2 — Parallel Task Runner
Independent sub-tasks are dispatched concurrently via `asyncio.gather()` (or `ThreadPoolExecutor` for blocking agents). Each task runs in its own agent instance with isolated local memory.

### Stage 3 — Aggregator Agent (Sequential)
Collects all parallel results, resolves conflicts, merges outputs, and produces the final response or action plan.

### Stage 4 — Final Response / SkillBus dispatch

---

## Hybrid Memory Architecture (Detailed)

```
┌──────────────────────────────────────────────────────────┐
│                  Global MemoryManager                    │
│  - Vector DB (semantic embeddings)                       │
│  - Knowledge Graph (GraphDB nodes/edges)                 │
│  - World Model (current system state)                    │
│  - Shared Observations (cross-agent facts)               │
│  - Long-term persistent storage                          │
│  memory_manager.shared_context                           │
└──────────────────────────────────────────────────────────┘
         ▲                        ▲
         │ read/write             │ read/write
┌────────┴──────┐        ┌────────┴──────┐
│  Agent Local  │        │  Agent Local  │
│  Memory       │        │  Memory       │
│  - episodic   │        │  - episodic   │
│  - scratchpad │        │  - scratchpad │
│  - reasoning  │        │  - reasoning  │
│  - task state │        │  - task state │
│  - exec logs  │        │  - exec logs  │
└───────────────┘        └───────────────┘
   agent.local_memory       agent.local_memory
```

Each agent:
1. Reads relevant context from **Global Memory** at start of task.
2. Writes intermediate reasoning into **Local Memory** (isolated scratchpad).
3. Writes confirmed facts/results back into **Global Memory** on completion.

---

## Proposed Changes

### Component 1: Config Layer (`jarvis/config/`)

#### [NEW] `jarvis/config/mcp_servers.yaml`
```yaml
mcp_servers:
  - name: filesystem
    transport: stdio           # stdio subprocess
    command: ["python", "agents_external/mcp_filesystem.py"]
    description: "Read/write files on disk"
  - name: web_search
    transport: http            # HTTP/SSE endpoint
    url: "http://localhost:8765"
    description: "Search the web via DuckDuckGo"
```

#### [NEW] `jarvis/config/agents.yaml`
```yaml
agents:
  - name: search_agent
    module: agents_external.search_agent
    fn: run
    description: "Searches the web and returns structured results"
    parallel_safe: true        # can run in parallel
  - name: code_agent
    module: agents_external.code_agent
    fn: run
    description: "Writes, runs, and debugs Python scripts"
    parallel_safe: true
  - name: vision_agent
    module: agents_external.vision_agent
    fn: run
    description: "Analyzes screenshots and UI state"
    parallel_safe: true
  - name: memory_agent
    module: agents_external.memory_agent
    fn: run
    description: "Queries and updates the knowledge graph"
    parallel_safe: false       # must run sequentially (write access)
  - name: aggregator_agent
    module: jarvis.agents.builtin.aggregator
    fn: run
    description: "Merges multi-agent results into final response"
    parallel_safe: false
```

---

### Component 2: Agent Memory System (`jarvis/agents/memory/`)

#### [NEW] `jarvis/agents/memory/__init__.py`

#### [NEW] `jarvis/agents/memory/agent_local_memory.py`
Per-agent isolated memory store:
```python
@dataclass
class AgentLocalMemory:
    agent_name: str
    episodic: list[dict]      # task history
    scratchpad: dict          # temporary k/v reasoning store
    task_state: dict          # current task progress
    exec_log: list[str]       # step-by-step execution log

    def note(self, key, value): ...
    def recall(self, key): ...
    def log_step(self, msg): ...
    def clear(self): ...
```

#### [NEW] `jarvis/agents/memory/shared_context.py`
Thin wrapper around `MemoryManager` to expose a clean cross-agent API:
```python
class SharedAgentContext:
    def observe(self, fact: str, confidence: float): ...  # write to global
    def recall(self, query: str) -> list[str]: ...        # semantic search
    def get_world_state(self) -> dict: ...                # current system snapshot
    def set_world_state(self, key, value): ...
```

---

### Component 3: Agent Interface & Bus (`jarvis/agents/`)

#### [NEW] `jarvis/agents/__init__.py`

#### [NEW] `jarvis/agents/agent_interface.py`
```python
class AgentInterface(ABC):
    @property
    def name(self) -> str: ...

    @property
    def parallel_safe(self) -> bool:
        return True

    def run(
        self,
        task: str,
        context: dict,
        local_memory: AgentLocalMemory,
        shared: SharedAgentContext,
    ) -> AgentResult: ...
```

#### [NEW] `jarvis/agents/agent_result.py`
```python
@dataclass
class AgentResult:
    success: bool
    output: str
    agent_name: str
    steps_taken: list[str] = field(default_factory=list)
    data: Any = None
```

#### [NEW] `jarvis/agents/agent_bus.py`
Core responsibilities:
- `discover()` — loads `config/agents.yaml` + scans `agents_external/`.
- `run_single(name, task, context)` — dispatch to a named agent.
- `run_parallel(tasks: list[(name, task)], context)` — concurrent via `asyncio.gather`.
- `run_pipeline(task_graph, context)` — full Planner→Parallel→Aggregator pipeline.
- `get_agent_catalog()` → `str` — formatted for LLM prompt injection.

#### [NEW] `jarvis/agents/task_graph.py`
`TaskGraph` dataclass used by the Planner Agent output:
```python
@dataclass
class AgentTask:
    agent: str
    task: str
    depends_on: list[str] = field(default_factory=list)  # task IDs

@dataclass
class TaskGraph:
    tasks: list[AgentTask]
    def independent_tasks(self) -> list[AgentTask]: ...
    def dependent_tasks(self) -> list[AgentTask]: ...
```

#### [NEW] `jarvis/agents/builtin/__init__.py`

#### [NEW] `jarvis/agents/builtin/planner_agent.py`
Built-in Planner Agent: calls the LLM to decompose a complex request into a `TaskGraph`.

#### [NEW] `jarvis/agents/builtin/aggregator_agent.py`
Built-in Aggregator Agent: merges all `AgentResult` outputs into a final unified response.

---

### Component 4: MCP Bus (`jarvis/mcp/`)

#### [NEW] `jarvis/mcp/__init__.py`

#### [NEW] `jarvis/mcp/mcp_interface.py`
```python
class MCPInterface(ABC):
    @property
    def name(self) -> str: ...
    def list_tools(self) -> list[dict]: ...     # [{"name": ..., "description": ..., "params": ...}]
    def call(self, tool: str, params: dict) -> dict: ...
    def health_check(self) -> bool: ...
```

#### [NEW] `jarvis/mcp/mcp_bus.py`
- `discover()` — loads `config/mcp_servers.yaml`, instantiates adapters.
- `call(server, tool, params)` — routes to the correct adapter.
- `get_tool_catalog()` → `str` — all MCP tools formatted for LLM context.

#### [NEW] `jarvis/mcp/adapters/stdio_adapter.py`
Launches an MCP server as a subprocess (stdin/stdout JSON-RPC 2.0). Handles process lifecycle.

#### [NEW] `jarvis/mcp/adapters/http_adapter.py`
HTTP/SSE client for MCP servers exposing a REST or SSE endpoint.

---

### Component 5: Dynamic Slash Registry (`jarvis/gateway/`)

#### [NEW] `jarvis/gateway/slash_registry.py`
```python
class SlashRegistry:
    _commands: dict[str, SlashEntry] = {}

    @classmethod
    def register(cls, cmd: str, handler: Callable, description: str, category: str = "general"): ...

    @classmethod
    def handle(cls, cmd: str, args: list, session, gateway) -> Optional[str]: ...

    @classmethod
    def list_commands(cls) -> dict[str, SlashEntry]: ...   # cmd → entry
```
All builtin commands self-register at module import. External skills/agents can call `SlashRegistry.register()` in their module body.

#### [MODIFY] `jarvis/gateway/slash_handler.py`
- Replace hardcoded `if/elif` chain → `SlashRegistry.handle(cmd, args, ...)`.
- Add new builtin slash commands:

| Command | Description |
|---------|-------------|
| `/skills [category]` | List available skills, optionally filtered |
| `/agents` | List registered agents with descriptions |
| `/mcp [server]` | List MCP servers and available tools |
| `/spin <agent> <task>` | Spawn a single named agent with a task |
| `/multiagents <a1> <a2> ... -- <task>` | Spawn multiple agents in parallel |
| `/<AgentName> <task>` | Shorthand: any registered agent name as slash cmd |
| `/tool <server> <tool> [json]` | Directly invoke an MCP tool |
| `/agent <name> <task>` | Alias for `/spin` |
| `/reload` | Hot-reload all external skills, agents, MCP configs |

---

### Component 6: Planner Extension (`jarvis/brain/planner.py`)

#### [MODIFY] `jarvis/brain/planner.py`
- Accept `mcp_bus: MCPBus` and `agent_bus: AgentBus` in `__init__`.
- Extend `_plan_via_unified_llm()` enriched context to include:
  - `[Available Skills]` (existing)
  - `[Available MCP Tools]` — `mcp_bus.get_tool_catalog()`
  - `[Available Agents]` — `agent_bus.get_agent_catalog()`
- Handle new LLM decision types in the decision loop:
  - `"agent"` — single agent dispatch: `agent_bus.run_single(name, task, context)`
  - `"multiagent"` — parallel pipeline: `agent_bus.run_pipeline(task_graph, context)`
  - `"mcp"` — MCP tool call: `mcp_bus.call(server, tool, params)`
- LLM JSON response contracts:
```json
// Single agent
{"type": "agent", "agent": "code_agent", "task": "write hello world in Python"}

// Multi-agent pipeline (Planner decides decomposition)
{"type": "multiagent", "tasks": [
  {"agent": "search_agent", "task": "find Python tutorials"},
  {"agent": "code_agent",   "task": "write the code", "depends_on": ["search_agent"]}
]}

// MCP tool call
{"type": "mcp", "server": "filesystem", "tool": "read_file", "params": {"path": "notes.txt"}}
```

---

### Component 7: LLM Interface Extension (`jarvis/llm/llm_interface.py`)

#### [MODIFY] `jarvis/llm/llm_interface.py`
```python
@dataclass
class LLMDecision:
    type: str   # "chat"|"plan"|"mixed"|"clarify"|"agent"|"multiagent"|"mcp"
    message: Optional[str] = None
    steps: Optional[Plan] = None
    question: Optional[str] = None
    # Agent fields
    agent: Optional[str] = None
    agent_task: Optional[str] = None
    agent_tasks: Optional[list[dict]] = None   # for multiagent
    # MCP fields
    mcp_server: Optional[str] = None
    mcp_tool: Optional[str] = None
    mcp_params: Optional[dict] = None
```

---

### Component 8: Orchestrator Wiring (`jarvis/brain/orchestrator.py`)

#### [MODIFY] `jarvis/brain/orchestrator.py`
- Instantiate `MCPBus` and `AgentBus` in `__init__`.
- Pass both to `Planner.__init__`.
- In `boot()`: call `mcp_bus.discover()` and `agent_bus.discover()`.
- In the results loop: handle `AgentResult` wrapped as `SkillResult` for uniform output.

---

### Component 9: Example External Plugins

#### [NEW] `agents_external/README.md`
How to write a custom agent (implement `AgentInterface`, place in `agents_external/`, optionally register a slash command).

#### [NEW] `agents_external/example_agent.py`
Reference agent: echoes task back, logs steps, demonstrates local + shared memory usage. Auto-registers `/example_agent` slash command.

#### [NEW] `skills_external/README.md`
How to write a custom skill (`@skill` decorator, `SlashRegistry.register()` optional).

#### [NEW] `skills_external/example_skill.py`
Sample skill with custom slash command: `/greet [name]`.

---

## File Map

```
jarvis/
├── brain/
│   ├── orchestrator.py               [MODIFY] wire MCPBus + AgentBus
│   └── planner.py                    [MODIFY] unified catalog + new decision types
├── llm/
│   └── llm_interface.py              [MODIFY] agent/mcp/multiagent decision types
├── agents/
│   ├── __init__.py                   [NEW]
│   ├── agent_interface.py            [NEW] ABC with local+shared memory
│   ├── agent_result.py               [NEW]
│   ├── agent_bus.py                  [NEW] discover + run_single/parallel/pipeline
│   ├── task_graph.py                 [NEW] AgentTask + TaskGraph
│   ├── memory/
│   │   ├── __init__.py               [NEW]
│   │   ├── agent_local_memory.py     [NEW] per-agent scratchpad + episodic
│   │   └── shared_context.py         [NEW] global shared context wrapper
│   └── builtin/
│       ├── __init__.py               [NEW]
│       ├── planner_agent.py          [NEW] LLM-powered task decomposer
│       └── aggregator_agent.py       [NEW] result merger
├── mcp/
│   ├── __init__.py                   [NEW]
│   ├── mcp_interface.py              [NEW] ABC
│   ├── mcp_bus.py                    [NEW] discover + call + catalog
│   └── adapters/
│       ├── stdio_adapter.py          [NEW] subprocess JSON-RPC
│       └── http_adapter.py           [NEW] HTTP/SSE client
├── gateway/
│   ├── slash_registry.py             [NEW] dynamic slash cmd registry
│   └── slash_handler.py              [MODIFY] use registry + new cmds
└── config/
    ├── mcp_servers.yaml              [NEW]
    └── agents.yaml                   [NEW]

agents_external/
├── README.md                         [NEW]
└── example_agent.py                  [NEW]

skills_external/
├── README.md                         [NEW]
└── example_skill.py                  [NEW]

tests/
├── unit/
│   ├── test_agent_bus.py             [NEW]
│   ├── test_mcp_bus.py               [NEW]
│   ├── test_slash_registry.py        [NEW]
│   └── test_task_graph.py            [NEW]
└── integration/
    └── test_plugin_pipeline.py       [NEW]
```

---

## Verification Plan

### Automated Tests
- `test_agent_bus.py` — discover, run_single, run_parallel, unknown agent fallback, task graph ordering.
- `test_mcp_bus.py` — stdio adapter process lifecycle, http adapter request/response, offline graceful fallback.
- `test_slash_registry.py` — register, handle, list, unknown command, dynamic registration from external plugin.
- `test_task_graph.py` — independent vs. dependent task classification, cycle detection.
- `test_plugin_pipeline.py` — full end-to-end: external skill + agent + MCP tool via LLM decision.
- Full `pytest` run (275 existing + new) → 0 regressions.

### Manual Verification
- Drop `skills_external/example_skill.py` → `/skills` shows it; `/greet Jarvis` works.
- Drop `agents_external/example_agent.py` → `/agents` shows it; `/example_agent hello` works.
- `/spin search_agent find Python tutorials` → spawns and runs agent.
- `/multiagents search_agent code_agent -- build a web scraper` → runs both in parallel, aggregates.
- Add entry to `config/mcp_servers.yaml` → `/mcp` shows it; `/tool filesystem read_file {"path":"notes.txt"}` works.
- `/reload` → picks up new files without restart.
