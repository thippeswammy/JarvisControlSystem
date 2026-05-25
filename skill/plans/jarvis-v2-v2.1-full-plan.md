# Jarvis v2 + v2.1 — Full Implementation Plan

## Overview

This plan merges **v2** (Iron Man Architecture) and **v2.1** (Robustness) into a single
coherent, phased implementation. No existing functionality is broken during migration.
The new `jarvis/` package is built **alongside** the existing `Jarvis/` package and wired
in incrementally.

---

## Key Architecture Decisions (v2 + v2.1 Combined)

| Decision | Choice | Rationale |
|---|---|---|
| Memory Storage | **SQLite + NetworkX** | Atomic writes, sub-ms queries, no file corruption |
| Node Model | **Location + UIState hash** | Enables state-aware verification |
| Pathfinding | **A\* with hierarchical pruning** | Faster than Dijkstra on large graphs |
| Learning Loop | **Execute → Verify → Learn** | Zero false-positive paths stored |
| Settings Handler | **Delete → DAG-seeded graph** | Settings is just another app |
| Skill Registration | **@skill decorator + auto-discover** | Drop file → auto-load |
| LLM Backends | **YAML config: cloud, local, tunneled, mock** | Never fails completely |
| Human-readable output | **Exporter → .md snapshots on demand** | Debug without opening SQLite |

---

## New Directory Structure

```
JarvisControlSystem/
├── jarvis/                         ← NEW: v2 architecture root package
│   ├── __init__.py
│   ├── main.py                     ← NEW entry point (replaces JarvisAssistantRunWithText.py)
│   ├── config/
│   │   ├── config.yaml             ← YAML config: LLM, memory, navigator settings
│   │   └── settings_seed.yaml      ← 130 ms-settings: URIs for seeding
│   ├── perception/
│   │   ├── nlu.py                  ← MOVED from core/intent_engine.py
│   │   ├── context_harvester.py   ← MOVED from core/context_collector.py
│   │   └── perception_packet.py   ← NEW: PerceptionPacket dataclass
│   ├── brain/
│   │   ├── orchestrator.py         ← REFACTOR of core/jarvis_engine.py
│   │   ├── planner.py              ← REFACTOR of core/jarvis_llm.py
│   │   └── reactive_learner.py    ← NEW: centralized learning observer
│   ├── llm/
│   │   ├── llm_router.py           ← NEW: primary→fallback→mock chain
│   │   ├── llm_interface.py        ← NEW: abstract base class
│   │   └── backends/
│   │       ├── openai_llm.py
│   │       ├── local_llm.py
│   │       ├── tunneled_llm.py
│   │       └── mock_llm.py
│   ├── memory/
│   │   ├── graph_db.py             ← NEW: SQLite schema + NetworkX sync
│   │   ├── memory_manager.py       ← NEW: v2.1 DAG-based manager
│   │   ├── state_harvester.py     ← NEW: UIState extraction from UI tree
│   │   ├── state_comparator.py    ← NEW: fuzzy state diff (ignores clock/noise)
│   │   ├── exporter.py             ← NEW: GraphDB → human-readable .md snapshots
│   │   ├── migration.py            ← NEW: v1 .md → v2.1 SQLite migration script
│   │   └── layers/
│   │       ├── procedural.py       ← Navigation DAGs per app
│   │       ├── episodic.py         ← Session logs
│   │       ├── semantic.py         ← Facts about apps/system
│   │       ├── preference.py       ← User behavior patterns
│   │       └── task.py             ← Multi-step ongoing goals
│   ├── pathfinding/
│   │   └── graph_pathfinder.py    ← NEW: A* with hierarchical pruning (L1/L2/L3)
│   ├── skills/
│   │   ├── skill_bus.py            ← NEW: auto-discover + dispatch (replaces ActionRegistry)
│   │   ├── skill_decorator.py     ← NEW: @skill(triggers=[...]) decorator
│   │   └── builtins/
│   │       ├── app_skill.py        ← MOVED from handlers/app_handler.py
│   │       ├── system_skill.py     ← MOVED from handlers/system_handler.py
│   │       ├── keyboard_skill.py   ← MOVED from handlers/keyboard_handler.py
│   │       ├── window_skill.py     ← MOVED from handlers/window_handler.py
│   │       ├── navigator_skill.py  ← MOVED from handlers/navigator_handler.py
│   │       ├── search_skill.py     ← MOVED from handlers/search_handler.py
│   │       ├── session_skill.py    ← MOVED from handlers/session_handler.py
│   │       └── crawler_skill.py    ← MOVED from handlers/crawler_handler.py
│   ├── input/
│   │   ├── input_adapter.py        ← NEW: abstract base + Utterance dataclass
│   │   ├── text_adapter.py         ← NEW: stdin line reader
│   │   └── voice_adapter.py        ← NEW: faster-whisper + wake word
│   └── verification/
│       ├── verification_loop.py    ← NEW: Execute → Scan → Verify → Learn/Rollback
│       └── recovery.py             ← NEW: retry, alternative path, undo, ask user
├── memory/                         ← Extended structure (v2 layers)
│   ├── jarvis.db                ← NEW: SQLite graph database
│   ├── procedural/
│   │   └── apps/
│   │       ├── settings/
│   │       │   ├── graph.md        ← SEEDED: 130 ms-settings: nodes/edges
│   │       │   └── ui_map.md
│   │       └── global/
│   │           └── apps.md
│   ├── episodic/sessions/
│   ├── semantic/apps/
│   ├── preference/
│   └── task/active/
└── tests/
    ├── live/                        ← REORGANIZED from TEST/live/
    ├── unit/
    ├── integration/
    └── regression/
        ├── crash_detector.py
        ├── regression_runner.py
        └── baseline.json
```

---

## Phase Plan

### Phase 0 — Baseline Capture
**Goal**: Know exactly what passes before changing anything.

**Tasks**:
- [ ] Run all existing test scenarios → record pass/fail per step
- [ ] Save as `tests/regression/baseline_v1.json`
- [ ] Build `crash_detector.py` (exception wrap + 30s per-step timeout + `faulthandler.enable()`)
- [ ] Identify which scenarios are protected (only passing ones go in baseline)

**Files Created**: `tests/regression/crash_detector.py`, `tests/regression/baseline_v1.json`

---

### Phase 1 — YAML Config + LLM Router
**Goal**: Switch LLM backends without code changes.

**Tasks**:
- [ ] Write `jarvis/config/config.yaml` (full schema from v2 design)
- [ ] Create `jarvis/llm/llm_interface.py` — abstract `LLMInterface.plan(prompt) → Plan`
- [ ] Create `jarvis/llm/backends/mock_llm.py` — current heuristic logic extracted
- [ ] Create `jarvis/llm/backends/openai_llm.py` — OpenAI/Anthropic via API key
- [ ] Create `jarvis/llm/backends/local_llm.py` — HuggingFace transformers pipeline
- [ ] Create `jarvis/llm/backends/tunneled_llm.py` — HTTP to self-hosted model
- [ ] Create `jarvis/llm/llm_router.py`:
  - Reads config, instantiates backends
  - Health check thread (60s interval)
  - `route(prompt)` → primary → fallback → mock chain
- [ ] Unit test: `tests/unit/test_llm_router_failover.py`

**Verification**: Mock primary to timeout → verify fallback activates → mock always returns.

---

### Phase 2 — SQLite Graph DB + DAG Memory (v2.1 Core)
**Goal**: Replace flat .md recipe files with a persistent, queryable graph database.

**Tasks**:
- [ ] Install deps: `pip install networkx` (sqlite3 is stdlib)
- [ ] Create `jarvis/memory/graph_db.py`:
  - SQLite schema: `nodes(id, app_id, type, label, state_hash, ui_metadata_json)`
  - SQLite schema: `edges(id, from_id, to_id, action_type, action_params_json, confidence, success_count, fail_count, triggers_json, fast_path, fast_path_value)`
  - `GraphDB.get_graph(app_id) → nx.DiGraph` (load app subgraph into NetworkX)
  - `GraphDB.save_node(node)`, `GraphDB.save_edge(edge)` (atomic upsert)
  - `GraphDB.update_edge_confidence(edge_id, delta)` 
- [ ] Create `jarvis/memory/state_harvester.py`:
  - Extract `UIState`: toggle values, selection states, visibility of key elements
  - Returns `state_hash` (MD5 of normalized state dict)
- [ ] Create `jarvis/memory/state_comparator.py`:
  - Fuzzy state comparison (ignores noise like clock, status bar)
  - `compare(actual_state, target_state) → bool`
- [ ] Create `jarvis/memory/exporter.py`:
  - `export_app_graph(app_id) → str` (generates .md in v2 format)
  - Called on demand for debugging (not on every write)
- [ ] Create `jarvis/memory/migration.py`:
  - Read old `memory/*.md` → parse v1 recipes → insert into SQLite as edges
  - Read old `memory/apps.md` → insert as APP nodes
  - Idempotent (safe to re-run)
- [ ] Create `jarvis/memory/memory_manager.py` (v2.1):
  - `recall(command, snapshot) → Optional[MemoryPath]` — A* path from graph
  - `save(command, steps, snapshot) → None` — verify then store
  - `get_relevant_context(command, snapshot) → str` — RAG for LLM
- [ ] Create `jarvis/memory/layers/procedural.py`:
  - `seed_settings_graph()` — writes 130 ms-settings: nodes from `settings_seed.yaml`
  - `get_app_graph(app_id) → nx.DiGraph`
  - `update_edge(edge_id, success: bool)`
- [ ] Stub remaining layers (episodic, semantic, preference, task) — minimal implementations
- [ ] Unit tests: `tests/unit/test_dag_pathfinding.py`, `tests/unit/test_memory_graph_rw.py`

**Migration**: `python -m jarvis.memory.migration` to convert v1 data.

---

### Phase 3 — SkillBus Auto-Discovery
**Goal**: Drop a .py file in `jarvis/skills/builtins/` → auto-loaded. Zero config.

**Tasks**:
- [ ] Create `jarvis/skills/skill_decorator.py`:
  - `@skill(triggers: list[str], priority: int = 0)` decorator
  - Registers function into a module-level registry dict
- [ ] Create `jarvis/skills/skill_bus.py`:
  - `SkillBus.discover(paths: list[str])` — `pkgutil.walk_packages()` + `importlib.import_module()`
  - Collects all `@skill`-decorated functions
  - Priority: `skills_external/ > builtins/ > built-in`
  - `SkillBus.dispatch(skill_call: SkillCall) → SkillResult`
  - `SkillCall(skill_name, params, category, source)` dataclass
  - `SkillResult(success, message, data, action_taken)` dataclass
- [ ] Migrate each handler to skill format:
  - `app_skill.py` ← `app_handler.py` logic, decorated with `@skill(triggers=[...])`
  - `system_skill.py`, `keyboard_skill.py`, `window_skill.py`
  - `navigator_skill.py`, `search_skill.py`, `session_skill.py`, `crawler_skill.py`
  - **Note**: `settings_handler.py` is NOT migrated — it is deleted in Phase 5
- [ ] Unit test: `tests/unit/test_skill_bus_discovery.py`

**Verification**: Add a mock `test_skill.py` file → verify SkillBus auto-discovers it.

---

### Phase 4 — A\* Pathfinding with Hierarchical Pruning
**Goal**: Find the best navigation path in <100ms, even for large graphs.

**Tasks**:
- [ ] Create `jarvis/pathfinding/graph_pathfinder.py`:
  - **Hierarchical Search**: L1 (App) → L2 (Page) → L3 (Element)
  - **Contextual Pruning**: When searching Notepad, exclude all Chrome/Settings nodes
  - **A\* implementation**:
    - `heuristic(node, target)`: hierarchical depth distance
    - `weight(edge)`: `1 / (confidence × log(success_count + 2))` + BACK edge penalty ×1.5
    - Per-path `visited` set (cycle guard — same as v2 design but now in A\*)
  - **Fast-path short-circuit**: Check `entry_strategy: uri` before searching
  - **Node matching**: trigram similarity + word overlap (Phase 1: edge triggers, Phase 2: node labels)
  - Returns `Optional[List[Edge]]` — ordered edge list, or None → LLM planner
- [ ] Unit test: `tests/unit/test_dag_pathfinding.py` — verify all 4 cases:
  - Normal forward nav
  - Back button cycle guard
  - Cross-link (multi-parent)
  - No path → returns None

---

### Phase 5 — Brain Refactor + PerceptionPacket + Delete Settings Handler
**Goal**: Clean pipeline. Delete `settings_handler.py`. Settings = just another app.

**Tasks**:
- [ ] Create `jarvis/perception/perception_packet.py`:
  - `PerceptionPacket(raw_text, intent, context_snapshot, memory_recall, timestamp, session_id)`
  - `ContextSnapshot`: active_app, current_location, active_window_title, open_windows
- [ ] Create `jarvis/perception/nlu.py` — move `IntentEngine` logic, remove `ActionType.OPEN_SETTINGS / CLOSE_SETTINGS`
- [ ] Create `jarvis/perception/context_harvester.py` — generic location extraction (NO hardcoded app dict)
- [ ] Create `jarvis/brain/reactive_learner.py`:
  - Singleton observer of all `SkillResult`s
  - Decides which memory layer receives the learning
  - Wraps `VerificationLoop.verify()` before storing
- [ ] Create `jarvis/brain/planner.py` — `Plan = List[SkillCall]`, supports compound commands
- [ ] Create `jarvis/brain/orchestrator.py` (replaces `JarvisEngine`):
  - Decision tree: Memory hit → Known intent → LLM → Ask User
  - Calls `VerificationLoop` after each SkillCall step
  - Calls `ReactiveLearner` after each Plan completes
  - Handles voice confidence < 0.70 → confirmation request
- [ ] **Delete** `Jarvis/core/handlers/settings_handler.py`
- [ ] **Remove** `ActionType.OPEN_SETTINGS`, `ActionType.CLOSE_SETTINGS` from NLU
- [ ] NLU: `"open settings wifi"` → `OPEN_APP("settings")` + sub-location `"wifi"` in params
- [ ] Orchestrator: detect sub-location → split into two SkillCalls: `open_app(settings)` + `navigate_location(wifi)`
- [ ] `AppNavigationStrategy`: auto-detect `uri | path | search | graph_traversal` per app type
- [ ] Integration test: `tests/integration/test_full_pipeline_mock.py`

---

### Phase 6 — Verification Loop + Recovery (v2.1 Pillars 3 & 5)
**Goal**: Zero false-positive paths. No bad steps stored in memory.

**Tasks**:
- [ ] Create `jarvis/verification/verification_loop.py`:
  - `verify(skill_call, target_node, timeout=5.0) → bool`
  - After SkillCall: re-capture UIState → compare to `target_node.state_hash`
  - Match → success, boost edge confidence
  - Mismatch → trigger recovery flow, do NOT store
- [ ] Create `jarvis/verification/recovery.py`:
  - `retry(skill_call, max_attempts=2)` — re-attempt with brief delay (handles UI lag)
  - `try_alternative_path(current_node, target_node)` — next best A\* path
  - `rollback(last_known_good_node)` — use BACK edge to return
  - `ask_user(current_state, expected_state)` — final resort with detailed message
- [ ] Wire `VerificationLoop` into `Orchestrator` — wraps every SkillCall in a Plan

---

### Phase 7 — Multi-Modal Input
**Goal**: `python -m jarvis.main --text` or `--voice`. Same engine, different input.

**Tasks**:
- [ ] Create `jarvis/input/input_adapter.py`:
  - `InputAdapter` abstract base: `.stream() → Iterator[Utterance]`
  - `Utterance(text, confidence, source, metadata)` dataclass
- [ ] Create `jarvis/input/text_adapter.py` — reads stdin line by line
- [ ] Create `jarvis/input/voice_adapter.py`:
  - `faster-whisper` for transcription (more efficient)
  - Lightweight wake word detection ("jarvis") before activating
  - Returns `Utterance` with Whisper confidence score
  - Low confidence (<0.70 from config) → Orchestrator asks to confirm
- [ ] Create `jarvis/main.py`:
  - Parses `--text / --voice / --api` arg
  - Selects adapter → feeds to Orchestrator
  - Handles graceful shutdown

---

### Phase 8 — Iron Man Memory Layers (Full Activation)
**Goal**: All 5 memory layers fully active and queryable by LLM.

**Tasks**:
- [ ] Implement `jarvis/memory/layers/episodic.py`:
  - Background thread writes session log after each command
  - Stores: timestamp, command, success/fail, apps used, paths replayed vs learned
  - Retention: keep last 30 sessions, compress older into `index.md`
- [ ] Implement `jarvis/memory/layers/semantic.py`:
  - Pre-seed with: VS Code shortcuts, Chrome shortcuts, Windows system facts
  - `save_fact(id, label, value, category, source)`
  - `query_facts(keywords) → List[Fact]`
- [ ] Implement `jarvis/memory/layers/preference.py`:
  - Background analysis thread (runs every 10 sessions)
  - Reads episodic → updates frequency/pattern nodes
  - Outputs: preferred apps, speed preference, confirmation tolerance
- [ ] Implement `jarvis/memory/layers/task.py`:
  - `create_task(label, steps) → task_id`
  - `resume_task(task_id) → next_step`
  - Triggered by Orchestrator when command contains "continue" or "resume"
- [ ] LLM Context Budget: allocate token budget per layer (procedural: most, task: least)
- [ ] RAG: inject top-N relevant snippets from each layer into LLM system prompt

---

### Phase 9 — Settings Graph Seeding + Test Suite Reorganization
**Goal**: All 130 ms-settings: entries seeded. Full test suite running.

**Tasks**:
- [ ] Write `jarvis/config/settings_seed.yaml` (130 ms-settings: URIs)
- [ ] Run `procedural.seed_settings_graph()` — seeds SQLite DB
- [ ] Reorganize `TEST/` → `tests/` with new scenario structure (see plan)
- [ ] Implement `tests/regression/regression_runner.py`
- [ ] Run all 12 scenarios + unit/integration tests
- [ ] Save `tests/regression/baseline_v2.json`
- [ ] Write live scenario tests:
  - `scenario_10_graph_memory.py` — save edge → recall → replay
  - `scenario_11_llm_router.py` — primary fail → fallback → mock
  - `scenario_12_compound_commands.py` — "open notepad and type hello"

---

## Open Questions

> [!IMPORTANT]
> **Q1 — Migration Order**: Should v1 `Jarvis/` package remain fully functional until Phase 9 is complete (parallel operation), or are you OK with the old engine being partially bypassed during development?

> [!IMPORTANT]
> **Q2 — Voice Adapter**: Do you want Phase 7 (voice input) implemented in this batch, or can it be deferred? `faster-whisper` requires model download + GPU/CPU overhead.

> [!IMPORTANT]
> **Q3 — Local LLM Backend**: Do you want the `local_llm.py` (HuggingFace transformers + Qwen/Llama) backend fully functional from Phase 1, or just stubbed? Running a local model requires significant RAM/VRAM.

> [!WARNING]
> **Settings Handler Deletion**: `settings_handler.py` handles 130+ settings actions today. After Phase 5, ALL settings navigation goes through the procedural DAG + A\*. If the seeded graph is incomplete, some settings commands will fail until the user teaches Jarvis by demo. Are you OK with this tradeoff?

> [!NOTE]
> **Phase Ordering**: Phase 5 (Brain Refactor) depends on Phase 3 (SkillBus) and Phase 4 (A\*). Phase 6 (Verification) depends on Phase 5. All other phases are mostly independent and can proceed in parallel.

---

## Verification Plan

### Per-Phase Verification
Each phase ends with:
1. Its unit/integration test suite passing
2. Regression runner confirming no new failures vs baseline

### Final Verification (Phase 9)
- All 12 live scenarios pass (8 original + 3 new)
- All 6 unit test files pass
- All 3 integration tests pass
- Settings navigation works via DAG (not settings_handler)
- LLM router failover verified
- Self-learning demo: teach Jarvis a new path → it recalls it next session
