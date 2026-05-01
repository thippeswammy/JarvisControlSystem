# Jarvis v2 + v2.1 — Full Implementation Plan (Updated)

## User Feedback Incorporated

| Question | Decision |
|---|---|
| V1 parallel operation? | **Not required. OK to let old code yield to new.** |
| Voice input (Phase 7)? | **Yes — include it. CUDA toolkit setup notes included.** |
| Local LLM with 16GB RAM + 4GB GPU? | **Yes — use Ollama + qwen2.5:7b-instruct-q4_K_M** |
| Settings handler deletion tradeoff? | **Approved.** |
| Phase ordering? | **Sequential only. No parallel phases.** |
| Final test count? | **14 live scenarios (original 12 + new 15, 16, 17)** |

---

## Key Architecture Decisions (v2 + v2.1 Combined)

| Decision | Choice |
|---|---|
| Memory Storage | **SQLite + NetworkX** (persistent, atomic, sub-ms queries) |
| Node Model | **Location + UIState hash** (state-aware verification) |
| Pathfinding | **A\* with hierarchical pruning** (L1/L2/L3) |
| Learning Loop | **Execute → Verify → Learn** (zero false-positive paths) |
| Settings Handler | **Deleted → DAG-seeded procedural graph** |
| Skill Registration | **@skill decorator + pkgutil auto-discover** |
| LLM Backends | **Ollama (local) + cloud + tunneled + mock** |
| Human-readable output | **Exporter → .md snapshots on demand** |

---

## Local LLM Stack — Model, Method, Integration

### Model: `qwen2.5:7b-instruct-q4_K_M`
- **Provider**: Alibaba Qwen team (open weights)
- **Why**: 7B parameters fits in 4GB VRAM with Q4_K_M quantization (~3.8GB)
- **Quantization method**: GGUF Q4_K_M (k-quant mixed precision — best quality/size tradeoff at 4-bit)
- **Context window**: 32k tokens — enough for full memory RAG injection
- **Fallback model**: `llama3.2:3b` (2.0GB VRAM — fits even if GPU is busy)

### Runner: Ollama
- **Why Ollama over raw `transformers` pipeline**:
  - Handles CUDA library setup automatically (cuBLAS, cuDNN bundled)
  - Exposes an **OpenAI-compatible HTTP API** at `http://localhost:11434/v1`
  - Model management: `ollama pull qwen2.5:7b-instruct-q4_K_M`
  - GPU layers auto-negotiated (`num_gpu` layers fit to VRAM)
  - No Python CUDA version conflicts — Ollama ships its own CUDA runtime
- **API endpoint used**: `POST /api/chat` (streaming) or `/v1/chat/completions` (OpenAI compat)

### CUDA / NVIDIA Setup Notes
Your 4GB GPU needs:
1. **NVIDIA Driver**: ≥ 525.xx (supports CUDA 12.x). Run `nvidia-smi` to verify.
2. **CUDA Toolkit**: Ollama bundles its own — you do **not** need to install CUDA Toolkit separately.
3. **cuBLAS / cuDNN**: Bundled inside Ollama. No manual installation needed.
4. **faster-whisper (voice)**: Requires `ctranslate2` with CUDA. Install:
   ```
   pip install faster-whisper
   pip install ctranslate2 --extra-index-url https://download.pytorch.org/whl/cu121
   ```
5. If your current system CUDA version conflicts, Ollama isolates itself — only faster-whisper needs matching.

### Integration: `jarvis/llm/backends/local_llm.py`
```
LocalLLM → HTTP client → Ollama REST API (localhost:11434)
         → Same interface as TunneledLLM (both are OpenAI-compat HTTP)
         → Health check: GET /api/tags → check if model loaded
         → On first call: `ollama pull qwen2.5:7b-instruct-q4_K_M` if not present
```

### Techniques Used in Prompting
- **System prompt**: Jarvis identity + JSON output format spec
- **RAG injection**: Top-4 memory snippets from procedural + semantic layers
- **Chain-of-thought**: LLM asked to reason step-by-step then emit `Plan` JSON
- **Structured output**: Response parsed as `Plan = List[SkillCall]`
- **Temperature**: 0.1 (deterministic, no hallucination on action names)
- **Token budget**: max_tokens=300 per call (keeps latency low on 4GB GPU)

---

## New Directory Structure

```
JarvisControlSystem/
├── jarvis/                         ← NEW v2 package
│   ├── config/
│   │   ├── config.yaml             ← LLM, memory, voice threshold settings
│   │   └── settings_seed.yaml      ← 130 ms-settings: URIs
│   ├── perception/
│   │   ├── nlu.py                  ← from core/intent_engine.py
│   │   ├── context_harvester.py    ← from core/context_collector.py
│   │   └── perception_packet.py    ← NEW dataclass
│   ├── brain/
│   │   ├── orchestrator.py         ← refactor of jarvis_engine.py
│   │   ├── planner.py              ← refactor of jarvis_llm.py
│   │   └── reactive_learner.py     ← NEW centralized learning
│   ├── llm/
│   │   ├── llm_router.py           ← primary→fallback→mock chain
│   │   ├── llm_interface.py        ← abstract base
│   │   └── backends/
│   │       ├── openai_llm.py       ← OpenAI/Anthropic cloud
│   │       ├── local_llm.py        ← Ollama HTTP client
│   │       ├── tunneled_llm.py     ← self-hosted via ngrok/cloudflared
│   │       └── mock_llm.py         ← heuristic, always available
│   ├── memory/
│   │   ├── graph_db.py             ← SQLite schema + NetworkX sync
│   │   ├── memory_manager.py       ← v2.1 DAG-based manager
│   │   ├── state_harvester.py      ← UIState extraction
│   │   ├── state_comparator.py     ← fuzzy state diff
│   │   ├── exporter.py             ← GraphDB → .md snapshots
│   │   ├── migration.py            ← v1 .md → SQLite migration
│   │   └── layers/
│   │       ├── procedural.py
│   │       ├── episodic.py
│   │       ├── semantic.py
│   │       ├── preference.py
│   │       └── task.py
│   ├── pathfinding/
│   │   └── graph_pathfinder.py     ← A* with hierarchical pruning
│   ├── skills/
│   │   ├── skill_bus.py            ← auto-discover + dispatch
│   │   ├── skill_decorator.py      ← @skill(triggers=[...])
│   │   └── builtins/
│   │       ├── app_skill.py
│   │       ├── system_skill.py
│   │       ├── keyboard_skill.py
│   │       ├── window_skill.py
│   │       ├── navigator_skill.py
│   │       ├── search_skill.py
│   │       ├── session_skill.py
│   │       └── crawler_skill.py
│   ├── input/
│   │   ├── input_adapter.py        ← abstract + Utterance dataclass
│   │   ├── text_adapter.py         ← stdin reader
│   │   └── voice_adapter.py        ← faster-whisper + wake word
│   └── verification/
│       ├── verification_loop.py    ← Execute → Scan → Verify
│       └── recovery.py             ← retry, alt path, rollback, ask
├── memory/
│   ├── jarvis.db                ← SQLite graph database
│   ├── procedural/apps/settings/
│   ├── episodic/sessions/
│   ├── semantic/apps/
│   ├── preference/
│   └── task/active/
└── tests/
    ├── live/                        ← reorganized from TEST/live/
    ├── unit/
    ├── integration/
    └── regression/
        ├── crash_detector.py
        ├── regression_runner.py
        └── baseline.json
```

---

## config.yaml Schema

```yaml
jarvis:
  input_mode: text
  voice_confidence_threshold: 0.70

llm:
  primary: local            # try Ollama first (always on)
  fallback: tunneled        # if Ollama down
  emergency_fallback: mock  # always works

  backends:
    local:
      engine: ollama
      api_url: "http://localhost:11434/v1"
      model: "qwen2.5:7b-instruct-q4_K_M"
      fallback_model: "llama3.2:3b"
      max_tokens: 300
      temperature: 0.1
      timeout_seconds: 15

    openai:
      provider: openai
      api_key: "${OPENAI_API_KEY}"
      model: gpt-4o-mini
      max_tokens: 300
      temperature: 0.1

    tunneled:
      api_url: "${JARVIS_TUNNEL_URL}"
      api_key: "${JARVIS_TUNNEL_KEY}"
      model: "${JARVIS_TUNNEL_MODEL}"
      timeout_seconds: 10

    mock:
      enabled: true

memory:
  root_dir: ./memory
  db_path: ./memory/jarvis.db
  confidence_decay_per_fail: 0.05
  confidence_boost_per_success: 0.02
  min_confidence_threshold: 0.30

navigator:
  ocr_fallback: true

voice:
  model_size: base.en          # faster-whisper model size
  device: cuda                 # cuda | cpu
  compute_type: float16        # float16 for GPU
  wake_word: jarvis
```

---

## Sequential Phase Plan

### Phase 0 — Baseline Capture
**Goal**: Know exactly what passes before any change.

- Run all existing TEST/live/ scenarios → record pass/fail per step
- Save as `tests/regression/baseline_v1.json`
- Build `tests/regression/crash_detector.py`:
  - Python exception wrapper around every step
  - 30s per-step timeout (`threading.Timer`)
  - `faulthandler.enable()` for C-level crashes
  - Visual assertion: screenshot before/after key steps

---

### Phase 1 — YAML Config + LLM Router
**Goal**: LLM backend switchable via config. Ollama as primary.

- Write `jarvis/config/config.yaml`
- `jarvis/llm/llm_interface.py` — abstract `LLMInterface.plan(prompt) → Plan`
- `jarvis/llm/backends/mock_llm.py` — extract existing heuristic logic
- `jarvis/llm/backends/local_llm.py` — Ollama HTTP client:
  - `health_check()`: GET `http://localhost:11434/api/tags` → verify model loaded
  - `plan(prompt)`: POST `/v1/chat/completions` with structured output format
  - Auto-pull model on first use if not present
- `jarvis/llm/backends/openai_llm.py` — OpenAI/Anthropic via `openai` SDK
- `jarvis/llm/backends/tunneled_llm.py` — same as local_llm but remote URL
- `jarvis/llm/llm_router.py`:
  - Reads config, instantiates all backends
  - Background health thread (60s interval)
  - `route(prompt)` → primary → fallback → mock (never fails)
- **Unit test**: `tests/unit/test_llm_router_failover.py`

---

### Phase 2 — SQLite Graph DB + DAG Memory
**Goal**: Replace flat .md files with persistent graph database.

- **Install**: `pip install networkx` (sqlite3 is stdlib)
- `jarvis/memory/graph_db.py`:
  - Schema: `nodes(id, app_id, type, label, state_hash, ui_metadata_json)`
  - Schema: `edges(id, from_id, to_id, action_type, action_params_json, confidence, success_count, fail_count, triggers_json, fast_path, fast_path_value)`
  - `get_graph(app_id) → nx.DiGraph`
  - `save_node(node)`, `save_edge(edge)` — atomic upsert
  - `update_edge_confidence(edge_id, delta)`
- `jarvis/memory/state_harvester.py` — extract UIState: toggle values, selections, visibility → `state_hash` (MD5)
- `jarvis/memory/state_comparator.py` — fuzzy state diff (ignores clock/status bar noise)
- `jarvis/memory/exporter.py` — `export_app_graph(app_id) → .md` (on demand, debug only)
- `jarvis/memory/migration.py` — convert v1 `memory/*.md` recipes → SQLite edges (idempotent)
- `jarvis/memory/memory_manager.py` — new v2.1 API: `recall()`, `save()`, `get_relevant_context()`
- `jarvis/memory/layers/procedural.py` — `seed_settings_graph()` seeds 130 ms-settings nodes
- Stub remaining layers (episodic, semantic, preference, task)
- **Unit tests**: `test_dag_pathfinding.py`, `test_memory_graph_rw.py`

---

### Phase 3 — SkillBus Auto-Discovery
**Goal**: Drop a .py file → auto-loaded. Zero core file changes.

- `jarvis/skills/skill_decorator.py` — `@skill(triggers=[...], priority=0)` decorator
- `jarvis/skills/skill_bus.py`:
  - `discover(paths)` — `pkgutil.walk_packages()` + `importlib.import_module()`
  - Priority: `skills_external/ > builtins/ > built-in`
  - `SkillCall(skill_name, params, category, source)` dataclass
  - `SkillResult(success, message, data, action_taken)` dataclass
  - `dispatch(skill_call) → SkillResult`
- Migrate handlers → skills (logic unchanged, only decorator changes):
  - `app_skill.py`, `system_skill.py`, `keyboard_skill.py`, `window_skill.py`
  - `navigator_skill.py`, `search_skill.py`, `session_skill.py`, `crawler_skill.py`
  - **`settings_handler.py` is NOT migrated — deleted in Phase 5**
- **Unit test**: `test_skill_bus_discovery.py`

---

### Phase 4 — A\* Pathfinding with Hierarchical Pruning
**Goal**: Find best path in <100ms, even on large graphs.

- `jarvis/pathfinding/graph_pathfinder.py`:
  - **Hierarchical search**: L1 App → L2 Page → L3 Element
  - **Contextual pruning**: searching Notepad ignores all Chrome/Settings nodes
  - **A\* with heuristic**: `h(node, target)` = hierarchical depth distance
  - **Edge weight**: `1 / (confidence × log(success_count + 2))` + BACK edge penalty ×1.5
  - **Cycle guard**: per-path `visited` set (not global)
  - **Fast-path**: check `entry_strategy: uri` before A\* (O(1) teleport)
  - **Node matching**: trigram similarity + word overlap (Phase 1: edge triggers, Phase 2: node labels)
  - Returns `Optional[List[Edge]]` — None → LLM planner
- **Unit test** covers all 4 cases: forward nav, back-button cycle, cross-link, no-path→None

---

### Phase 5 — Brain Refactor + PerceptionPacket + Delete Settings Handler
**Goal**: Clean pipeline. Settings is just another app.

- `jarvis/perception/perception_packet.py` — `PerceptionPacket` + `ContextSnapshot` dataclasses
- `jarvis/perception/nlu.py` — move IntentEngine; **remove `OPEN_SETTINGS`, `CLOSE_SETTINGS`**
- `jarvis/perception/context_harvester.py` — generic location extraction, no hardcoded app dict
- `jarvis/brain/reactive_learner.py` — singleton, wraps VerificationLoop before storing
- `jarvis/brain/planner.py` — `Plan = List[SkillCall]`, supports compound commands
- `jarvis/brain/orchestrator.py` — decision tree: Memory hit → Known intent → LLM → Ask User
- **DELETE** `Jarvis/core/handlers/settings_handler.py`
- NLU: `"open settings wifi"` → `OPEN_APP("settings")` + sublocation `"wifi"` in params
- Orchestrator: detect sublocation → split into `open_app(settings)` + `navigate_location(wifi)`
- `AppNavigationStrategy`: auto-detect `uri | path | search | graph_traversal` per app
- **Integration test**: `test_full_pipeline_mock.py`

---

### Phase 6 — Verification Loop + Recovery (v2.1 Pillars 3 & 5)
**Goal**: Zero false-positive paths stored in memory.

- `jarvis/verification/verification_loop.py`:
  - After each SkillCall: re-capture UIState → compare to `target_node.state_hash`
  - Match → boost edge confidence → store
  - Mismatch → trigger recovery → do NOT store
- `jarvis/verification/recovery.py`:
  - `retry(max=2)` — re-attempt with delay (handles UI lag)
  - `try_alternative_path()` — next best A\* path
  - `rollback()` — BACK edge to last known-good state
  - `ask_user()` — final resort with current vs expected state message
- Wire into Orchestrator — every SkillCall in a Plan is wrapped

---

### Phase 7 — Multi-Modal Input (Voice + Text)
**Goal**: `python -m jarvis.main --text` or `--voice`.

- `jarvis/input/input_adapter.py` — abstract `InputAdapter` + `Utterance` dataclass
- `jarvis/input/text_adapter.py` — reads stdin line by line
- `jarvis/input/voice_adapter.py`:
  - **Library**: `faster-whisper` (CTranslate2 backend, ~2–4× faster than openai-whisper)
  - **Model**: `base.en` (142MB, fast, English-only — good for 4GB GPU)
  - **Wake word**: lightweight `pvporcupine` or simple energy threshold + "jarvis" keyword check
  - **CUDA**: `device="cuda", compute_type="float16"` in config
  - Returns `Utterance(text, confidence, source="voice", ...)`
  - If `confidence < voice_confidence_threshold` → Orchestrator asks to confirm
- **CUDA setup for faster-whisper**:
  ```
  pip install faster-whisper
  # CTranslate2 CUDA wheel (matches your CUDA version):
  pip install ctranslate2 --extra-index-url https://download.pytorch.org/whl/cu121
  ```
  No cuDNN manual install needed — bundled in the wheel.
- `jarvis/main.py` — parses `--text/--voice`, selects adapter, graceful shutdown

---

### Phase 8 — Iron Man Memory Layers (Full Activation)
**Goal**: All 5 memory layers active and injected into LLM context.

- `episodic.py` — background thread: session log per command (timestamp, cmd, success, apps used)
- `semantic.py` — pre-seeded: VS Code shortcuts, Chrome shortcuts, Windows system facts
- `preference.py` — background analysis every 10 sessions: frequency → preference nodes
- `task.py` — multi-step goals; triggered by "continue" / "resume" in command
- RAG: top-N snippets from each layer → LLM system prompt (token budget: procedural gets most)

---

### Phase 9 — Settings Graph Seeding + Full Test Suite
**Goal**: 130 ms-settings seeded. All 14 live scenarios passing.

- Write `jarvis/config/settings_seed.yaml` (130 ms-settings: URIs as nodes + edges)
- Run `procedural.seed_settings_graph()` → seeds SQLite DB
- Reorganize `TEST/` → `tests/` with new scenario layout
- Implement `tests/regression/regression_runner.py`
- Write new scenarios:
  - `scenario_10_graph_memory.py` — save edge → recall → replay
  - `scenario_11_llm_router.py` — primary fail → fallback → mock
  - `scenario_12_compound_commands.py` — "open notepad and type hello"
  - `scenario_13_self_learning_demo.py` — teach Jarvis new path, recall next session
  - `scenario_14_voice_mode.py` — voice input end-to-end
  - `scenario_15_verification_loop.py` — bad action → verify mismatch → recovery
  - `scenario_16_task_memory.py` — create task → pause → resume
  - `scenario_17_preference_adaptation.py` — repeated command → preference learned → faster
- Save `tests/regression/baseline_v2.json`

---

## Verification Plan

### Per Phase
Each phase ends with: its own unit/integration tests passing + regression runner confirming no new failures vs baseline.

### Final (Phase 9)
- 17 live scenarios pass (original 9 + 8 new)
- 6 unit test files pass
- 3 integration tests pass
- Settings navigation via DAG (not settings_handler)
- LLM router failover: Ollama down → mock takes over
- Voice mode: utterance → Whisper → Orchestrator → action
- Self-learning: teach Jarvis → recalled next session
