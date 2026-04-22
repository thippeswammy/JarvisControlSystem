# Jarvis v2 — Complete System Design
### Design-Only. Methods, Algorithms, Approaches, System Decisions.
### No implementation code. No files touched.

---

## Comments Received → Design Decisions Made

| Your Comment | Design Decision |
|---|---|
| "Plan all phases in detail, describe methods/algorithms/approaches" | This document = pure design only |
| "3 LLM backends: cloud, local, tunneled self-hosted, configurable by YAML" | LLM Router with YAML config |
| "Seed settings nodes in same format as Jarvis learning" | Seeded nodes are IDENTICAL to learned nodes — one format for all |
| "Not only for navigation — any new memory things" | Memory is a generic DAG that any subsystem can extend |
| "Iron Man Jarvis — if you have ideas, add them" | 5-layer cognitive memory architecture |
| "Use DAG" | Directed Acyclic Graph with Dijkstra path-finding |
| "Nodes need more hierarchical — buttons, items, any clickable action" | 4-level node hierarchy: App → Page → Section → Element |
| "Yes correct on path-finding" | Confirmed: confidence-weighted Dijkstra is the approach |
| "Yes on graph traversal for settings wifi" | Confirmed: generic for all apps |
| "ms-settings URIs work only for specific apps, handle all others" | Navigation strategy is app-type-aware, NOT URI-dependent |
| "Remove redundancy in tests, keep more complex things" | Test suite pruned from 14 → 8 high-value scenarios |

---

## Part 1 — Overall System Architecture

### The Core Pipeline (unchanged flow, refined components)

```
INPUT → PERCEPTION → BRAIN → SKILL BUS → ACTION → MEMORY
  ↑                                                    |
  └──────────── ReactiveLearner observes ─────────────┘
```

Every utterance follows this exact sequence. The pipeline is linear and deterministic.
No shortcuts, no special cases, no per-app branches.

### The 5 Architectural Layers

```
┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 1 — INPUT (Multi-Modal)                                           │
│   Text CLI  |  Voice (Whisper)  |  API (HTTP)  |  Schedule (cron)       │
│   All produce: raw text utterance + metadata                            │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │ Utterance + InputMetadata
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 2 — PERCEPTION                                                    │
│   NLU (parse intent)  +  ContextHarvester (where is Jarvis now?)        │
│   +  MemoryRecall (did we already learn this?)                          │
│   All three run in parallel → combine into ONE PerceptionPacket         │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │ PerceptionPacket
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 3 — BRAIN (Orchestrator + Planner)                                │
│   Decision tree:                                                        │
│     Memory hit?  → YES → build Plan from graph path                    │
│                   NO  → Intent known? → YES → single SkillCall         │
│                                         NO  → LLM Planner              │
│                                               ↓                        │
│                                         confident? → execute Plan      │
│                                         not sure?  → ASK_USER          │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │ Plan (ordered list of SkillCalls)
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 4 — SKILL BUS                                                     │
│   Auto-discovers all skills.  Executes Plan steps in order.            │
│   Each SkillCall → one registered skill function → SkillResult         │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │ SkillResults (one per step)
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 5 — MEMORY (DAG, multi-layer, auto-growing)                      │
│   ReactiveLearner writes successful paths into the correct memory layer │
│   All memory is a DAG. Human-readable .md. Queryable by the LLM.       │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Part 2 — Multi-Modal Input Layer

### Design Principle
The input source is completely invisible to the rest of the system.
All adapters implement a single contract: they produce a stream of `(text, metadata)` tuples.

### The 4 Input Adapters

| Adapter | Trigger | Output | Status |
|---|---|---|---|
| `TextAdapter` | `--text` | stdin lines | Phase 5 |
| `VoiceAdapter` | `--voice` | Whisper transcription | Phase 5 |
| `APIAdapter` | `--api` | HTTP POST body | Future |
| `SchedulerAdapter` | `--schedule` | cron-defined strings | Future |

### `InputMetadata` (attached to every utterance)
Carries: source type, timestamp, confidence (for voice: Whisper confidence score),
raw audio if applicable. Used by the Orchestrator to decide how to handle low-confidence inputs.

### Design Decision: Voice Confidence Threshold
If Whisper confidence < 0.70 → Orchestrator asks user to confirm before executing.
If confidence >= 0.70 → execute normally.
Threshold is configurable in `config.yaml`.

---

## Part 3 — LLM Router (3 Backends, YAML Config)

### The 3 Backends

```
┌──────────────────────────────────────────────────────────────────────┐
│                          LLM Router                                  │
│                                                                      │
│  1. openai    → OpenAI / Anthropic API (cloud, req. API key)         │
│  2. local     → transformers pipeline (Qwen/Llama, runs on machine)  │
│  3. tunneled  → HTTP API to user's self-hosted model via tunnel      │
│                 (ngrok / cloudflared / bore.pub)                     │
│  4. mock      → current heuristic mock (always available, fallback)  │
│                                                                      │
│  Selection:   primary → fallback → mock (never fails completely)     │
└──────────────────────────────────────────────────────────────────────┘
```

### `config.yaml` Structure (full design)

```yaml
jarvis:
  input_mode: text            # text | voice | api
  voice_confidence_threshold: 0.70

llm:
  primary: tunneled           # try this first
  fallback: local             # if primary fails
  emergency_fallback: mock    # always works

  backends:
    openai:
      provider: openai        # openai | anthropic | azure
      api_key: "${OPENAI_API_KEY}"   # from env var, never hardcoded
      model: gpt-4o-mini
      max_tokens: 200
      temperature: 0.1

    local:
      model_id: Qwen/Qwen2.5-1.5B-Instruct
      device: auto            # cuda | cpu | auto
      load_in_4bit: true      # memory saving quantization

    tunneled:
      api_url: "${JARVIS_TUNNEL_URL}"     # e.g. https://abc.ngrok.io/v1
      api_key: "${JARVIS_TUNNEL_KEY}"
      model: "${JARVIS_TUNNEL_MODEL}"     # model name exposed by your server
      timeout_seconds: 10

    mock:
      enabled: true           # always enabled as last resort

memory:
  root_dir: ./memory
  confidence_decay_per_fail: 0.05
  confidence_boost_per_success: 0.02
  min_confidence_threshold: 0.30   # edges below this are pruned

navigator:
  strategy_detection: auto    # how to detect app nav strategy (see Part 6)
  ocr_fallback: true
```

### LLM Router Decision Algorithm
```
attempt_primary():
    → if primary backend healthy → call it
    → if call fails (timeout, rate limit, no internet) → attempt_fallback()

attempt_fallback():
    → if fallback backend healthy → call it
    → if fails → use mock

health_check():
    → run on startup + every 60s in background thread
    → updates backend availability status
    → LogS which backend is active so user knows
```

### What the LLM Receives (Prompt Design)
The LLM always receives:
1. **System prompt**: Jarvis identity + output format instructions
2. **Learned Memory snippet** (RAG from graph — top 4 most relevant paths)
3. **Present Condition** (PerceptionPacket.context_snapshot as text)
4. **The failed/unknown command**

The LLM always returns a **Plan** (list of SkillCalls), not a single JSON action.
This is the key change from v1's single-action response.

---

## Part 4 — The Memory System (Iron Man / JARVIS Level)

### Design Philosophy
Human memory has multiple layers that serve different purposes.
Iron Man's JARVIS knows: how to do things, what happened before, facts about the world,
Tony's preferences, and what tasks are in progress.
Jarvis v2 has the same structure.

### The 5 Memory Layers

```
memory/
├── procedural/     ← HOW to do things (navigation graphs per app)
├── episodic/       ← WHAT happened (session logs, conversation history)
├── semantic/       ← WHAT things ARE (facts: app info, system info)
├── preference/     ← HOW THE USER LIKES THINGS (patterns, favorites)
└── task/           ← WHAT IS IN PROGRESS (multi-step ongoing goals)
```

All 5 layers use the SAME **Directed Graph (DG)** format. Different node/edge types, same parser.
Note: DG allows cycles. This is intentional — real UI navigation has back buttons and cross-links.

---

### Layer 1: Procedural Memory (`memory/procedural/`)

**Purpose**: Knows HOW to navigate to any state in any app.
This is the richest, most-used memory layer.

```
memory/procedural/
└── apps/
    ├── settings/
    │   ├── graph.md       ← navigation DG (Directed Graph)
    │   └── ui_map.md      ← live UI element snapshots per node
    ├── chrome/
    │   ├── graph.md
    │   └── ui_map.md
    ├── explorer/
    │   ├── graph.md
    │   └── ui_map.md
    └── <any_new_app>/     ← auto-created on first visit
        ├── graph.md
        └── ui_map.md
```

**Why the Graph CANNOT Be a Strict Tree or Pure DAG**

Real UI navigation creates the following structures that break a tree / pure DAG:

```
[Back button]    AdvancedDisplay → Display          (reverse edge — creates cycle)
[Cross-link]     AdvancedDisplay → PersonalizeColor (cross-page jump — multi-parent)
[Shared section] Scale&Layout exists in Display AND Personalization (multi-parent)
[Loop]           Settings Home → System → Display → Back → System → Bluetooth (valid repeat)
```

A strict tree allows ONE parent per node. A pure DAG allows NO cycles.
Real UI has BOTH multi-parent nodes AND cycles. Therefore: **Directed Graph (DG)**.

**Node Types (no fixed hierarchy — any type can link to any type)**

```
APP       — root entry for an application (e.g. "settings", "chrome", "explorer")
PAGE      — a distinct full-screen view (e.g. "settings.display", "chrome.settings")
SECTION   — a named group within a page (e.g. "display.scale_and_layout")
ELEMENT   — an individual clickable/interactive control (button, link, combobox, etc.)
DIALOG    — a modal overlay (save dialog, confirm dialog, permission prompt)
SHORTCUT  — a keyboard-only transition (no UI element, just key combo)
```

**Valid Edge Directions (any combination allowed)**

```
APP      → PAGE        forward: enter an app's main page
PAGE     → SECTION     forward: expand a section within a page
PAGE     → ELEMENT     forward: click a control directly visible on the page
SECTION  → ELEMENT     forward: interact with an element inside a section
ELEMENT  → PAGE        forward: clicking an element opens a new page (link, button)
ELEMENT  → DIALOG      forward: clicking triggers a modal dialog
DIALOG   → PAGE        forward/back: dialog closes → return to origin page
PAGE     → PAGE        back: Back button → previous page (creates cycle if bidirectional)
SECTION  → PAGE        cross: a section link navigates to a different page entirely
SECTION  → SECTION     cross: a section contains a link to a different section
```

**Real Example — Windows Settings (Shows Why Cycles Occur)**

```
Settings.home ──forward──► Settings.system
Settings.system ──forward──► Settings.display
Settings.display ──forward──► Settings.display.advanced     [AdvancedDisplay page]
Settings.display.advanced ──back──► Settings.display        ← CYCLE (back button)
Settings.display ──cross──► Settings.personalize.colors     ← CROSS-LINK (Night Light → Personalization)
Settings.display.scale_layout ──shared──► Settings.accessibility.text_size  ← SHARED SECTION concept
```

The graph for Settings is therefore a **Directed Graph with cycles**, not a DAG.

**Full DG Format** (human-readable .md, auto-generated, identical for seeded and learned):

```markdown
# procedural/apps/settings — Navigation Graph (DG)
<!-- Jarvis v2 | Auto-generated | Same format for seeded and learned nodes -->

## Node
- id: settings.home
- type: APP
- label: Windows Settings Home
- entry_strategy: uri
- entry_value: ms-settings:home
- in_edges: []                           ← no predecessors (entry point)
- out_edges: [edge.home_to_system, edge.home_to_bluetooth, edge.home_to_display_fast]

## Node
- id: settings.display
- type: PAGE
- label: Display Settings
- entry_strategy: uri
- entry_value: ms-settings:display
- in_edges: [edge.system_to_display, edge.home_to_display_fast, edge.adv_to_display_back]
- out_edges: [edge.display_to_advanced, edge.display_to_nightlight, edge.display_to_colors_cross]

## Node
- id: settings.display.advanced
- type: PAGE
- label: Advanced Display Settings
- entry_strategy: click
- entry_value: none
- in_edges: [edge.display_to_advanced]
- out_edges: [edge.adv_to_display_back]  ← back edge → creates cycle with settings.display

## Node
- id: settings.display.scale_layout
- type: SECTION
- label: Scale and Layout
- entry_strategy: scroll_into_view
- entry_value: none
- in_edges: [edge.display_to_scale_section]
- out_edges: [edge.scale_to_resolution, edge.scale_to_scale_combo]

## Node
- id: settings.display.resolution_combo
- type: ELEMENT
- label: Display resolution
- control_type: ComboBox
- entry_strategy: click
- entry_value: Display resolution
- in_edges: [edge.scale_to_resolution]
- out_edges: []                          ← leaf node (no outgoing navigation)

## Edge
- id: edge.home_to_display_fast
- from: settings.home
- to: settings.display
- edge_type: FORWARD
- triggers: ["open display settings", "settings display", "go to display"]
- steps: ["click System", "click Display"]
- fast_path: uri
- fast_path_value: ms-settings:display
- confidence: 0.97
- success_count: 7
- fail_count: 0
- last_used: 2026-04-22

## Edge
- id: edge.display_to_advanced
- from: settings.display
- to: settings.display.advanced
- edge_type: FORWARD
- triggers: ["advanced display", "open advanced display"]
- steps: ["scroll down", "click Advanced display"]
- fast_path: none
- confidence: 0.93
- success_count: 2
- fail_count: 0
- last_used: 2026-04-22

## Edge
- id: edge.adv_to_display_back
- from: settings.display.advanced
- to: settings.display
- edge_type: BACK                        ← explicit back edge (creates cycle)
- triggers: ["go back", "back", "back to display"]
- steps: ["click Back"]                  ← or keyboard: Alt+Left
- fast_path: uri
- fast_path_value: ms-settings:display   ← fast-path bypasses back button
- confidence: 0.99
- success_count: 1
- fail_count: 0
- last_used: 2026-04-22

## Edge
- id: edge.display_to_colors_cross
- from: settings.display
- to: settings.personalization.colors
- edge_type: CROSS                       ← cross-page edge (multi-parent target)
- triggers: ["night light colors", "personalize night light"]
- steps: ["click Night light settings", "click Personalization colors"]
- fast_path: uri
- fast_path_value: ms-settings:personalization-colors
- confidence: 0.90
- success_count: 1
- fail_count: 0
- last_used: 2026-04-22
```

**Key Design Decisions (Updated)**

1. **`entry_strategy`** on nodes — how to reach this node from scratch:
   - `uri` — teleport via ms-settings: or ms-edge:// URI
   - `path` — launch via exe path  
   - `search` — Windows Search fallback
   - `click` — click an element (must follow in_edges to get here)
   - `scroll_into_view` — scroll until element is visible then interact
   - `keyboard` — keyboard shortcut (no click needed)

2. **`edge_type`** on edges — the semantic meaning of the transition:
   - `FORWARD` — normal forward navigation
   - `BACK` — back button / undo navigation (creates cycles)
   - `CROSS` — jumps to a node in a different branch (multi-parent)
   - `SHORTCUT` — keyboard shortcut that bypasses UI steps

3. **`in_edges` and `out_edges`** on nodes — explicit adjacency lists.
   A node with multiple `in_edges` = multi-parent node.
   A node with a `BACK` edge pointing to an ancestor = cycle.

4. **`fast_path` on edges** — any edge can have a URI/shortcut that
   bypasses the `steps` list. If fast-path fails, fall back to steps.
   This handles `ms-settings:` as an optimization, not a requirement.

---

### Layer 2: Episodic Memory (`memory/episodic/`)

**Purpose**: Remembers what happened in past sessions.
Like a conversation log that the LLM can read to understand the user's history.

```
memory/episodic/
├── sessions/
│   ├── 2026-04-22_session_001.md    ← per-session log
│   └── 2026-04-20_session_003.md
└── index.md                         ← summary: frequent tasks, last used apps
```

**What gets stored per session**:
- Timestamp, duration, input mode
- List of commands (with success/fail)
- Which apps were used
- Which memory paths were replayed vs. learned fresh
- Any errors or fallbacks triggered

**How the LLM uses it**: When reasoning about "do I know how to do X?",
the LLM sees recent session summaries. If the user ran "open advanced display" 5 times
in the last week, the LLM knows it's commonly used and the procedural graph should have it.

**Retention policy**: Keep last 30 session logs. Compress older ones into `index.md`.

---

### Layer 3: Semantic Memory (`memory/semantic/`)

**Purpose**: Facts about the world. What Jarvis KNOWS, not just what it can DO.

```
memory/semantic/
├── apps/
│   ├── chrome.md          ← facts about Chrome (version, shortcuts, features)
│   ├── vscode.md          ← VS Code keyboard shortcuts, common commands
│   └── settings.md        ← what each Settings page controls
└── system/
    ├── hardware.md         ← user's GPU, RAM, display setup
    └── paths.md            ← important paths on this specific machine
```

**DAG Format for Semantic** (fact nodes):
```markdown
## Node
- id: fact.chrome.shortcut.devtools
- type: FACT
- label: Open Dev Tools in Chrome
- value: F12 or Ctrl+Shift+I
- category: keyboard_shortcut
- source: learned           ← or: seeded | user-defined

## Node
- id: fact.system.gpu
- type: FACT
- label: User's GPU model
- value: NVIDIA RTX [detected from system]
- category: hardware
```

**How it grows**:
- Seeded: known facts about common software
- Learned: every time Jarvis discovers a shortcut works, it records it
- User-defined: user explicitly teaches Jarvis a fact ("my name is X", "my project folder is Y")

---

### Layer 4: Preference Memory (`memory/preference/`)

**Purpose**: Learns what THIS USER likes. Personalizes Jarvis over time.

```
memory/preference/
├── habits.md          ← frequently-used commands, time-of-day patterns
├── favorites.md       ← favorite apps, folders, settings
└── style.md           ← prefers voice confirmation? fast execution? verbose output?
```

**What gets tracked**:
- Command frequency (which commands are used most)
- App usage patterns (Chrome in morning, VS Code in afternoon)
- Error tolerance (does user fix mistakes often? → Jarvis should ask more)
- Speed preference (does user say "yes yes quick" → skip confirmations)

**Algorithm**: After every 10 sessions, a background thread runs frequency analysis
on episodic memory → updates preference nodes. This is entirely automatic.

---

### Layer 5: Task Memory (`memory/task/`)

**Purpose**: Tracks multi-step goals that span sessions.
Iron Man's JARVIS remembers "you were building the suit yesterday, here's where you left off."

```
memory/task/
├── active/
│   └── task_001.md    ← currently in-progress tasks
└── completed/
    └── task_000.md    ← finished tasks (archived)
```

**Task Node Format**:
```markdown
## Node
- id: task.001
- type: TASK
- label: Set up Python dev environment
- status: in_progress        ← or: completed | paused | failed
- steps_total: 5
- steps_done: 2
- next_step: "install pytest"
- created: 2026-04-20
- last_touched: 2026-04-22

## Edge
- from: task.001.step.2
- to: task.001.step.3
- condition: step_2_completed
```

**How it's used**: User says "continue my setup" → Orchestrator checks task memory
→ finds in-progress task → resumes from `next_step`.

---

## Part 5 — Graph Path-Finding Algorithm

### Why Pure Dijkstra Fails on a Cyclic Directed Graph

Standard Dijkstra works on graphs with no negative cycles.
Our graph has cycles (back buttons, cross-links) but all edge weights are positive.
However, without a visited-node guard, Dijkstra can loop forever on cycles.
Solution: **Cycle-Aware Modified Dijkstra with per-search visited tracking.**

### Algorithm: Confidence-Weighted Dijkstra with Cycle Guard

**Problem**: Given the current node in the graph and a target node, find the best path.
"Best" = highest confidence × most successes. Path must not revisit any node.

**Edge Weight Formula**:
```
weight(edge) = 1 / (confidence × log(success_count + 2))
```
- High confidence + many successes → low weight → preferred path
- Low confidence + few successes → high weight → avoided unless no alternative
- `+ 2` in log prevents division by zero for new edges (success_count = 0)
- BACK edges get a weight penalty multiplier (×1.5) to prefer forward routes

**Algorithm Steps**:
```
cycle_aware_dijkstra(graph, start_node, target_node):

  priority_queue = [(cost=0, node=start_node, path=[], visited={start_node})]

  while priority_queue not empty:
    cost, current, path, visited = pop_lowest_cost(priority_queue)

    if current == target_node:
      return path                    ← found: return ordered edge list

    for each out_edge in current.out_edges:
      neighbor = out_edge.to_node

      if neighbor in visited:
        continue                     ← CYCLE GUARD: skip already-visited in this path

      new_cost = cost + weight(out_edge)
      new_visited = visited ∪ {neighbor}
      push(priority_queue, (new_cost, neighbor, path + [out_edge], new_visited))

  return None                        ← no path found → hand to LLM Planner
```

**Key Difference from Standard Dijkstra**: The `visited` set is **per-path**, not global.
This means the graph can have cycles, but any single path through it cannot repeat a node.
Two different paths can visit the same node — they just can't loop within one path.

**Why This Handles All Real UI Cases**:
```
Case 1 — Normal forward nav:  home → system → display
  visited = {home, system, display}  ← no revisit, path terminates

Case 2 — Back button exists:  display → advanced → BACK-edge → display
  When exploring advanced's neighbors, display is already in visited → SKIP
  So the algorithm never loops. It finds the best non-revisiting path.

Case 3 — Cross-link:  display → personalization.colors (multi-parent node)
  personalization.colors is not in visited → explore it → valid path
  The node has multiple parents but the path only enters it once.

Case 4 — No path from current location:
  algorithm exhausts the queue → returns None → LLM Planner takes over
```

**Fast-Path Short-Circuit**:
Before running Dijkstra, check if the target node has `entry_strategy: uri`.
If yes, AND the target is reachable from the current app context:
- Use `os.startfile(entry_value)` to teleport directly
- Skip Dijkstra entirely (O(1) vs O(V+E log V))
- Record as a `SHORTCUT` edge in the graph if not already stored

**Self-Healing**:
- When a step on a traversed edge fails:
  - Decrease that edge's `confidence` by `config.confidence_decay_per_fail`
  - If confidence < `config.min_confidence_threshold` → mark edge as `DEGRADED`
  - On next path-find: Dijkstra naturally avoids DEGRADED edges (high weight)
  - ReactiveLearner: if user manually corrects → save corrected steps as NEW edge
  - Old DEGRADED edge remains in graph (history) but is effectively never chosen

**Node Matching Algorithm (fuzzy trigger + node label matching)**:
```
For user utterance "open wifi settings":

  Phase 1 — Edge trigger matching:
    1. Strip noise words → "wifi settings"
    2. For every edge in current app's graph:
       - trigram_similarity(utterance, trigger_phrase)
       - word_overlap_score(utterance, trigger_phrase)
       - score = max(trigram_sim, word_overlap)
    3. If best edge score ≥ 0.60 → use that edge's to_node as target

  Phase 2 — Node label matching (if Phase 1 fails):
    1. For every node in graph:
       - label_similarity(utterance, node.label)
    2. If best node score ≥ 0.50 → use that node as target

  Phase 3 — LLM fallback:
    If both phases fail → pass utterance + graph context to LLM Planner
    → LLM identifies target node or plans new steps
    → new path saved as new edges
```

---

## Part 6 — App Navigation Strategy

### The Problem (Your Comment)
`ms-settings:` URIs ONLY work for Windows Settings and Microsoft Store.
For Chrome, VS Code, Notepad, Discord, etc., there is no URI scheme.
The navigation strategy must be detected per-app, not assumed.

### The 4 Navigation Strategies

| Strategy | When to use | How it works |
|---|---|---|
| `uri` | Settings, Store, Control Panel, Edge | `os.startfile("ms-settings:display")` or `ms-edge://` etc. |
| `path` | Any Win32 .exe app | `subprocess.Popen(exe_path)` or `os.startfile(exe_path)` |
| `search` | UWP apps where exe path inaccessible | Windows Search box → type name → Enter |
| `graph_traversal` | All in-app navigation (any app) | Walk procedural DAG edges using Dijkstra |

### Strategy Detection (Automatic)
On first open of an unknown app, the system:
1. Checks `memory/procedural/apps/<appname>/graph.md` for known entry strategy
2. If not found: tries path lookup in `memory/procedural/apps/global/apps.md`
3. If not found: tries Windows Search fallback
4. After successful open: detect process type:
   - Is exe in `WindowsApps` folder? → UWP → store as `search` strategy (or tunneled AUMID)
   - Is exe a normal path? → Win32 → store as `path` strategy
   - Does app expose a URI scheme? (check registry) → store as `uri` strategy
5. Save detected strategy as `entry_strategy` in the app's root graph node

### In-App Navigation Strategy (Always `graph_traversal`)
Once an app is open, ALL navigation within it uses the procedural DAG.
Steps on edges can be:
- `click <element_name>` — UI element click
- `keyboard <shortcut>` — keyboard shortcut
- `type <text> in <field>` — type in a field
- `scroll <direction>` — scroll
- `wait_for <element>` — wait for element to appear
- `uri_deep_link <value>` — fast-path URI jump (Settings only)

The strategy is stored on each edge, not globally assumed.

---

## Part 7 — Settings Handler: Deletion and Migration

### What Gets Deleted
- `settings_handler.py` (entire file)
- `ActionType.OPEN_SETTINGS` enum
- `ActionType.CLOSE_SETTINGS` enum
- `SETTINGS_MAP` dict (130 entries)

### What Replaces It

**"open settings wifi"** parses as:
```
NLU:   OPEN_APP("settings") then NAVIGATE_LOCATION("wifi")
       — or —
       OPEN_APP("settings wifi") → Orchestrator sees "wifi" is a location within "settings"
```

**Orchestrator decision**:
1. Open Settings app (entry_strategy: search or uri)
2. Recall procedural graph for `settings` app
3. Find path from `home` to `wifi` node using Dijkstra
4. Execute path steps

### Seeding the Settings Graph
The 130 `ms-settings:` URIs from the old `SETTINGS_MAP` are migrated as:
- 130 graph NODE entries in `memory/procedural/apps/settings/graph.md`
- Each URI becomes a node's `entry_value` with `entry_strategy: uri`
- Each node has a `fast_path` edge from `home` using the URI
- Format is IDENTICAL to what Jarvis would write when it learns a new path
- No distinction between "seeded" and "learned" — same schema, same parser

### Why This Generalizes
Every other app follows the same pattern:
- Chrome → `memory/procedural/apps/chrome/graph.md` (pages = tabs/sections)
- VS Code → `memory/procedural/apps/vscode/graph.md` (pages = panels/menus)
- Explorer → `memory/procedural/apps/explorer/graph.md` (pages = folder locations)
- Any new app → graph auto-created on first interaction

---

## Part 8 — Test Suite Redesign

### Analysis of the 14 Existing Scenarios

| Scenario | Complexity | Redundancy | Decision |
|---|---|---|---|
| 1 — Session Activation | Low | Simple on/off | → **Merge into Scenario 2** |
| 2 — System Controls | Medium | Unique | → **Keep, add session activation** |
| 3 — Notepad + Menu | Medium | Overlaps with 7, 9 | → **Keep as foundation** |
| 4 — Multi-App + Window Mgmt | Medium | Unique | → **Keep** |
| 5 — Explorer Navigation | Medium | Explorer covered in 12 | → **Merge into 12** |
| 6 — Settings Navigation | Medium | Fully covered by 13 | → **Delete** |
| 7 — Keyboard Chain | Medium | Overlaps with 3, 9 | → **Merge into 3** |
| 8 — Full End-to-End Write | High | Unique, complex | → **Keep** |
| 9 — Click UI Elements | Medium | Overlaps with 3 | → **Merge into 3** |
| 10 — Full Stress Test | High | Excellent coverage | → **Keep + expand** |
| 11 — Settings Deep Nav | High | Complex, unique | → **Keep** |
| 12 — Explorer Deep Nav + LLM | High | Complex, unique | → **Keep** |
| 13 — Extensive Settings | High | Best settings test | → **Keep** |
| 14 — Self-Learning Demo | High | Most important | → **Keep + expand** |

### New Test Suite (8 Core Scenarios + 3 New)

```
tests/
├── live/
│   ├── scenario_01_system_and_session.py      (merged: 1+2)
│   ├── scenario_02_notepad_full_lifecycle.py  (merged: 3+7+9 — full app lifecycle)
│   ├── scenario_03_multi_app_window_mgmt.py   (was 4)
│   ├── scenario_04_end_to_end_write.py        (was 8)
│   ├── scenario_05_stress_test.py             (was 10, expanded)
│   ├── scenario_06_settings_deep_nav.py       (was 11)
│   ├── scenario_07_explorer_deep_nav.py       (was 12, merged with 5)
│   ├── scenario_08_settings_extensive.py      (was 13)
│   ├── scenario_09_self_learning_demo.py      (was 14, expanded)
│   │
│   ├── scenario_10_graph_memory.py            ← NEW: save edge → recall → replay
│   ├── scenario_11_llm_router.py              ← NEW: primary fail → fallback → mock
│   └── scenario_12_compound_commands.py       ← NEW: "open notepad and type hello"
│
├── unit/
│   ├── test_dag_pathfinding.py                ← Dijkstra correctness on mock graph
│   ├── test_nlu_parsing.py                    ← Intent engine, all action types
│   ├── test_skill_bus_discovery.py            ← auto-load, priority, dispatch
│   ├── test_memory_graph_rw.py                ← read/write/query DAG files
│   ├── test_llm_router_failover.py            ← primary fail → fallback logic
│   └── test_perception_packet.py              ← snapshot assembly
│
├── integration/
│   ├── test_full_pipeline_mock.py             ← end-to-end with mock skills
│   ├── test_reactive_learner.py               ← save new edge after success
│   └── test_settings_migration.py             ← seeded Settings graph query
│
└── regression/
    ├── crash_detector.py                      ← Exception + timeout + visual guard
    ├── regression_runner.py                   ← all tests → compare baseline
    └── baseline.json                          ← known-good snapshot
```

### Crash Detection Approach
Every live test step is wrapped with:
- **Python exception guard** — catches all unhandled exceptions, records traceback
- **Per-step timeout** (default 30s) — prevents infinite hangs
- **Visual assertion** — screenshot before/after; if expect_visual_change=True and no change → FAIL
- **C-level crash guard** — `faulthandler.enable()` dumps stack on segfault/abort
- **Import guard** — test runner verifies all modules import cleanly before running

### Regression Baseline Strategy
- `baseline.json` stores: per-scenario pass/fail + per-step success/fail
- Saved after every phase that passes all tests
- Compared before every commit / phase start
- Any NEW failure since last baseline = regression = blocked

---

## Part 9 — Detailed Phase Plan

> This is a **design-first plan**. No code is written until Phase 0 is complete.
> Each phase ends with regression baseline check before proceeding.

### Phase 0 — Baseline Capture (Prerequisites)
**Goal**: Establish ground truth. Know exactly what passes today before anything changes.

**Approach**:
- Run all 14 current live scenarios → record pass/fail per step
- Save as `baseline_v1.json`
- Build crash detector logic (approach: exception wrapping + per-step timeout)
- Identify which of the 14 scenarios are currently passing vs. failing
- Only scenarios that PASS today are in the protected baseline

**Algorithm**: One-time run, no changes to source code.

---

### Phase 1 — YAML Config + LLM Router
**Goal**: The system can switch LLM backends without code changes.

**Approach**:
- Define `config.yaml` schema (all keys described in Part 3)
- Build `LLMRouter` class that reads config, health-checks backends, routes requests
- `LLMInterface` abstract class: single method `plan(prompt) → Plan`
- Each backend implements `LLMInterface`: `OpenAILLM`, `LocalLLM`, `TunneledLLM`, `MockLLM`
- Primary/fallback/emergency chain evaluated on every call
- Background health-check thread updates backend availability every 60s
- `MockLLM` always available as emergency fallback — can never be disabled

**Algorithm**: Strategy pattern for backend selection + health monitoring loop.

**Verification**: Unit test `test_llm_router_failover.py` — mock primary to timeout → verify fallback activates.

---

### Phase 2 — DAG Memory Architecture
**Goal**: All memory stored as hierarchical DAG. `MemoryManager` public API unchanged.

**Approach**:
- Define the complete DAG schema (nodes, edges, types) as described in Part 4
- Build `GraphStore` class: reads/writes per-app `graph.md` using the DAG schema
- Build `UIMapStore` class: reads/writes per-app `ui_map.md`
- Build `AppStore` class: reads/writes `memory/procedural/apps/global/apps.md`
- Build confidence-weighted Dijkstra path-finder (operates on in-memory DAG)
- `MemoryManager.recall()` now calls Dijkstra → returns `MemoryPath` (ordered edge list)
- `MemoryManager.save()` now writes Node + Edge to correct app's graph DAG
- Episodic, Semantic, Preference, Task memory: define schemas, stub readers/writers

**Algorithm**: Dijkstra on weighted directed graph. Node matching via trigram + word-overlap.

**Migration**:
- Old `memory/navigation.md` → parsed → split by app → written as DAG edges
- Old `memory/apps.md` → parsed → written as root nodes in DAG
- Old `memory/ui_maps.md` → parsed → written as element nodes in per-app DAGs

**Seed Settings Graph**: All 130 `ms-settings:` entries from `SETTINGS_MAP` migrated
as nodes + edges in `memory/procedural/apps/settings/graph.md`.
Format is identical to what Jarvis learns at runtime.

**Verification**: Unit test `test_dag_pathfinding.py` + `test_memory_graph_rw.py`.

---

### Phase 3 — Delete Settings Handler + Generic Navigation
**Goal**: Settings is just another app. No hardcoded navigation anywhere.

**Approach**:
- Remove `ActionType.OPEN_SETTINGS`, `ActionType.CLOSE_SETTINGS`
- Delete `settings_handler.py`
- NLU changes: `"open settings wifi"` → `OPEN_APP("settings")` + target contains sub-location
- Orchestrator: detect when target contains a sub-location → split into two SkillCalls:
  1. `open_app(settings)`
  2. `navigate_location(wifi)` using Settings DAG
- `AppNavigationStrategy` class: auto-detects `uri | path | search | graph_traversal` per app type
- Settings test scenarios (6, 13 → new 6, 8) pass using graph traversal alone

**Algorithm**: Target decomposition (app + sublocation detection), strategy detection via process inspection.

**Verification**: All settings-related scenarios pass. Regression baseline holds.

---

### Phase 4 — Skill Bus Auto-Discovery
**Goal**: Drop a .py file in skills/ → it auto-loads. Zero changes to any core file.

**Approach**:
- `SkillBus` (replaces `ActionRegistry`) uses `importlib` + `pkgutil.walk_packages()` to scan skills/ and skills_external/
- Any function decorated with `@skill(triggers=[...])` is auto-registered on import
- Registration is idempotent (importing same module twice doesn't double-register)
- Priority: skills_external > skills > built-in (user skills always win)
- `SkillCall` dataclass: skill_name, params, category, source
- `SkillResult` dataclass: success, message, data, action_taken

**Algorithm**: Module walk + decorator registration pattern. Sorted by priority.

**Migration**: Each existing handler is moved to new skill folder. Decorator changes from `@registry.register(actions=[...])` to `@skill(triggers=["open", "launch"])`. Logic is identical.

**Verification**: Unit test `test_skill_bus_discovery.py` — add mock skill file → verify discovered.

---

### Phase 5 — Brain Refactor + PerceptionPacket
**Goal**: Clean orchestration. All data flows as one typed object. Learning is centralized.

**Approach**:
- `PerceptionPacket`: single dataclass built once per utterance, carries all context
  - `raw_text`, `intent`, `context_snapshot`, `memory_recall` (MemoryPath), `timestamp`, `session_id`
- `ContextHarvester` (from `ContextCollector`): returns filled `ContextSnapshot`
  - App classification: NO hardcoded app dict. Uses process name directly.
  - Location extraction: generic — window title, address bar, URL bar, active tab
- `Orchestrator` (from `JarvisEngine`): receives `PerceptionPacket`, returns `Plan`
  - Decision tree: memory hit → known intent → LLM → ask user
- `Planner` (from `LLMFallbackModule`): receives `PerceptionPacket` → returns `Plan`
  - `Plan` = ordered list of `SkillCall`s
  - Supports compound commands: "open notepad and type hello" → 2 SkillCalls
- `ReactiveLearner`: singleton observer of all `SkillResult`s
  - Receives: `PerceptionPacket` + `Plan` + list of `SkillResult`s
  - Decides: what to write to which memory layer
  - All learning logic in ONE class — no more split across the engine
- `Session` (from `Context` + `ContextManager`): merged into one object
  - `is_active`, `is_typing_mode`, `recent_commands`, `active_app` — all in one place

**Algorithm**: Pipeline pattern. Each stage transforms the data object and passes forward.

**Verification**: Integration test `test_full_pipeline_mock.py`.

---

### Phase 6 — Multi-Modal Input
**Goal**: `python main.py --text` or `--voice`. Same engine, different input.

**Approach**:
- `InputAdapter` abstract: `.stream() → Iterator[Utterance]`  
- `Utterance` dataclass: `text`, `confidence`, `source`, `metadata`
- `TextAdapter`: reads from stdin line by line
- `VoiceAdapter`:
  - Uses `faster-whisper` (more efficient than standard Whisper)
  - Listens for wake word ("jarvis") using lightweight keyword detector before activating
  - Transcribes audio chunk → produces Utterance with Whisper confidence score
  - If confidence < threshold (from config.yaml) → Orchestrator asks to confirm
- `main.py`: reads `--text/--voice` arg → selects adapter → feeds to Orchestrator

**Algorithm**: Producer-consumer. Adapter produces Utterances → Orchestrator consumes.

**Verification**: Run both text and voice mode, verify same commands produce same output.

---

### Phase 7 — Iron Man Memory Completion
**Goal**: Episodic, Semantic, Preference, Task memory layers fully active.

**Approach**:
- `EpisodicWriter`: background thread writes session log after each command
- `SemanticStore`: pre-seeded with common software knowledge (VS Code shortcuts, Chrome shortcuts, etc.)
- `PreferenceAnalyzer`: runs every 10 sessions, reads episodic → updates preferences
- `TaskTracker`: Orchestrator checks task memory when command contains "continue" or "resume"
- All layers queryable by LLM (injected into LLM context as relevant snippets via RAG)
- LLM context budget management: allocate token budget per layer (procedural gets most)

**Algorithm**: Background writers, RAG retrieval per layer using trigram similarity.

**Verification**: Scenario 9 (self-learning demo) + Scenario 12 (compound commands).

---

## Part 10 — What Does NOT Change

> These components are already correct. They are moved and/or renamed, not rewritten.

| Component | Current location | New location | Change |
|---|---|---|---|
| `IntentEngine` vocabulary | `core/intent_engine.py` | `perception/nlu.py` | Move only |
| `ActionRegistry` decorator pattern | `core/action_registry.py` | `skills/skill_bus.py` | + auto-discover |
| `AppNavigator` UI automation | `navigator/app_navigator.py` | same | Made singleton |
| `UIFinder` element lookup | `navigator/ui_finder.py` | same | None |
| `OCRClicker` visual fallback | `navigator/ocr_clicker.py` | same | None |
| `UIExtractor` structured extraction | `core/ui_extractor.py` | `jarvis/ui_extractor.py` | Move only |
| `UISpider` background loop | `core/ui_spider.py` | `background/ui_spider.py` | Move only |
| `SystemCrawler` | `core/system_crawler.py` | `background/system_crawler.py` | Move only |
| `.md` file format | `memory/*.md` | `memory/procedural/...` | Extended, not replaced |
| All 14 live scenarios logic | `TEST/live/` | `tests/live/` (pruned to 8+3) | Merged, no logic lost |

---

## Summary: What Makes This Iron Man Level

| Capability | How Achieved |
|---|---|
| Learns from every action automatically | ReactiveLearner + DAG edge writer |
| Remembers what it did in past sessions | Episodic memory layer |
| Knows facts about apps and the system | Semantic memory layer |
| Adapts to the user's patterns | Preference memory layer |
| Tracks multi-step goals across sessions | Task memory layer |
| Finds the best path to any goal | Confidence-weighted Dijkstra on procedural DAG |
| Gets smarter over time without coding | Confidence scores self-adjust on success/fail |
| Works with any app, not just Settings | Generic navigation strategy detection |
| Works with any LLM, swappable in config | 3-backend YAML-configurable LLM router |
| Accepts voice or text | InputAdapter layer |
| Never crashes silently | CrashDetector + regression baseline |
| You can add any new skill instantly | SkillBus auto-discovery |
| Memory is always human-readable | DAG in .md format |
