# Jarvis Ecosystem — Full Implementation Plan (v2)
## OpenClaw-Inspired, Jarvis-Native

---

## Decisions Locked (from your feedback)

| Decision | Answer |
|---|---|
| Multiple agents in parallel | ⏸ **Hold — next phase** |
| Gateway daemon | ✅ Yes |
| `rich` + `prompt_toolkit` packages | ✅ Yes, needed |
| Slash commands session-scoped? | ✅ Yes for TUI **and also** for Telegram/other channels |
| `pip install -e .` / pyproject.toml | ⏸ **Next phase** — use `jarvis.bat` wrapper for now |
| Named agent personas | ⏸ **Next phase** |
| Memory isolation per channel | ✅ Share procedural/skills; isolate episodic per channel |

---

## Critical Design Clarification — Skills vs OpenClaw Skills

> [!IMPORTANT]
> **Jarvis Skills ≠ OpenClaw Skills**
>
> OpenClaw "skills" are **markdown files (SKILL.md)** injected into the LLM system prompt — they teach the model *when and how* to use tools.
>
> **Jarvis Skills are Python `@skill`-decorated ACTION functions** — they are the tools themselves. They execute real OS operations (open apps, type text, press keys, navigate windows, etc.). The SkillBus auto-discovers and dispatches them.
>
> **Do NOT mix these concepts.** In Jarvis:
> - `@skill` functions = executable actions (OpenClaw equivalent of "tools")
> - The LLM/Planner decides WHICH skills to call — that is the "teaching" layer
> - There is no SKILL.md concept in Jarvis
>
> The CLI `jarvis skills list/info/enable/disable` manages **Jarvis action skills**, not markdown docs.

---

## Architecture Overview

```
jarvis.bat
    └─► jarvis/cli/main_cli.py  ← Full CLI command tree
            ├── jarvis tui       ← Interactive TUI (rich + prompt_toolkit)
            ├── jarvis gateway   ← Daemon management
            ├── jarvis channels  ← Channel management
            ├── jarvis memory    ← Memory inspection + management
            ├── jarvis logs      ← Log tail + analysis
            ├── jarvis skills    ← Skill registry management
            ├── jarvis models    ← LLM backend management
            ├── jarvis status    ← System health snapshot
            └── jarvis config    ← Config read/write

Gateway Daemon (jarvis/gateway/)
    ├── ChannelManager
    │     ├── CLIAdapter          ← Thread A
    │     ├── TelegramAdapter     ← Thread B  (real)
    │     └── MockTelegramAdapter ← Thread C  (test)
    ├── SessionManager
    │     └── Session(channel, user) → isolated Orchestrator
    └── CronScheduler

Per-Session Slash Command Handler (jarvis/tui/slash_handler.py)
    └── /status /agent /model /session /reset /memory /logs ...
         ↑ same handler used by TUI, Telegram, and future channels
```

---

## Phase 1 — Entry Point & Full CLI Command Tree

### [NEW] `jarvis/cli/__init__.py`
Empty init.

### [NEW] `jarvis/cli/main_cli.py`
Top-level CLI with `argparse` subcommands. Full command tree:

```
jarvis [--dev] [--log-level DEBUG|INFO|WARNING] [--no-color] [--profile <name>]

  setup          First-run wizard
  config         get / set / unset / file / validate
  status         Full system snapshot (gateway, channels, models, memory)
  health         Ping all subsystems (Ollama, DB, channels)
  doctor         Diagnose and auto-fix common problems
  gateway        start / stop / restart / status / logs
  daemon         install / uninstall / start / stop / restart / status
  channels       list / status / add / remove / logs <n>
  sessions       list / cleanup / kill <id>
  models         list / status / set <name> / scan
  memory         status / search <q> / remove <id> / prune / analyze / export / index
  logs           tail <n> / analyze / export / clear
  skills         list / info <name> / enable <name> / disable <name> / run <name>
  cron           list / add / rm / enable / disable / run <id>
  tui            Launch interactive TUI
  chat           Alias for tui
  version        Print version
  -V             Alias for version
```

### [MODIFY] `jarvis/main.py`
- Keep `build_orchestrator()` as the programmatic wiring function
- Replace `main()` argparse block with a thin shim that calls `cli_main()`
- All channel start logic moves to `gateway/channel_manager.py`

### [NEW] `jarvis.bat` (project root)
```batch
@echo off
python -m jarvis.cli.main_cli %*
```

---

## Phase 2 — Gateway Daemon & Channel Manager

### [NEW] `jarvis/gateway/__init__.py`

### [NEW] `jarvis/gateway/gateway.py`
Central daemon. Starts all enabled channels in parallel threads. Manages sessions.

```python
class GatewayDaemon:
    def __init__(config_path)
    def start()        # boots ChannelManager, SessionManager, CronScheduler
    def stop()
    def restart()
    def status() -> GatewayStatus
    def get_logs(n=100) -> list[str]
```

`GatewayStatus` contains:
- uptime, active channels, session count, model health, memory stats

### [NEW] `jarvis/gateway/channel_manager.py`
```python
class ChannelManager:
    def add_channel(name, adapter)
    def start_all()             # spawns threads for all enabled channels
    def stop_channel(name)
    def restart_channel(name)
    def list_channels() -> list[ChannelStatus]
    def channel_logs(name, n) -> list[str]
    def _run_channel_loop(name, adapter, session_mgr)  # per-thread loop
```

Each channel thread:
1. Reads utterances from its adapter
2. Gets-or-creates a Session from SessionManager
3. Calls `session.orchestrator.process(text)`
4. Calls `adapter.send(session_id, reply)`

### [NEW] `jarvis/gateway/session_manager.py`
```python
@dataclass
class Session:
    id: str                        # "{channel}:{user_id}"
    channel: str                   # "cli" | "telegram" | "telegram-test"
    user_id: str
    created_at: datetime
    last_active: datetime
    orchestrator: Orchestrator     # isolated per session
    episodic: EpisodicMemory       # isolated per channel (per your decision)
    slash_handler: SlashHandler    # shared command handler
    model_override: Optional[str]  # set by /model slash command

class SessionManager:
    def get_or_create(channel, user_id) -> Session
    def list_sessions() -> list[Session]
    def cleanup_idle(max_age_minutes=60)
    def kill(session_id)
    def get(session_id) -> Optional[Session]
```

**Memory isolation rule (your decision):**
- `EpisodicMemory` → new instance per channel (saves to `memory/episodic/{channel}/sessions/`)
- `MemoryManager` (procedural/skills/macros) → single shared instance across all channels

---

## Phase 3 — Unified Channel Adapter Layer

### [MODIFY] `jarvis/input/adapters.py`
Add `ChannelAdapter` abstract base class:

```python
class ChannelAdapter(ABC):
    name: str                             # "cli" | "telegram" | "telegram-test" | "voice"

    @abstractmethod
    def stream(self) -> Iterator[Utterance]: ...

    @abstractmethod
    def send(self, session_id: str, text: str) -> None: ...

    @abstractmethod
    def is_available(self) -> bool: ...

    def start_typing(self, session_id: str) -> None: pass  # optional
    def on_ready(self) -> None: pass                        # called on gateway start
    def on_stop(self) -> None: pass                         # called on gateway stop
```

**Concrete adapters updated to implement `ChannelAdapter`:**
- `TextAdapter` → renamed `CLIAdapter`, implements base
- `TelegramAdapter` → implements base
- `MockTelegramAdapter` → implements base
- `VoiceAdapter` → implements base

**Stubs for future channels:**
- `jarvis/input/channels/discord_adapter.py` *(stub)*
- `jarvis/input/channels/webhook_adapter.py` *(stub)*
- `jarvis/input/channels/whatsapp_adapter.py` *(stub)*

---

## Phase 4 — Per-Session Slash Command Handler

> [!IMPORTANT]
> The slash command handler is **not TUI-only**. It is a shared `SlashHandler` class used by ALL channels — TUI, Telegram, and future ones. When a Telegram user sends `/status`, it hits the same handler as the TUI `/status`.

### [NEW] `jarvis/tui/slash_handler.py`
```python
class SlashHandler:
    """
    Parses and executes /commands from any channel.
    Each Session owns one SlashHandler instance.
    """
    def __init__(session: Session, gateway: GatewayDaemon)
    def handle(text: str) -> Optional[str]  # returns reply text or None (not a slash command)
    def is_slash(text: str) -> bool
```

Full slash command table:

| Command | Scope | Description |
|---|---|---|
| `/help` | all | Show slash command help |
| `/commands` | all | List all slash commands |
| `/status` | all | Gateway + channels + session + model status |
| `/health` | all | Ping LLM backends + memory DB |
| `/session [key]` | all | Show or switch session |
| `/sessions` | all | List all active sessions |
| `/model [provider/model]` | session | Set model for this session only |
| `/models` | all | List available LLM backends + health |
| `/agent [name]` | session | Switch agent *(placeholder — full impl next phase)* |
| `/agents` | all | List available agents |
| `/think <off\|low\|medium\|high>` | session | Set LLM thinking level |
| `/fast <on\|off>` | session | Toggle fast/low-token mode |
| `/verbose <on\|off>` | session | Toggle verbose logging |
| `/usage` | session | Show token usage for this session |
| `/new` or `/reset` | session | Reset session (clear episodic context) |
| `/abort` | session | Abort current in-progress run |
| `/settings` | all | Show current config values |
| `/exit` or `/quit` | tui only | Exit TUI |
| `/skill <name> [params]` | all | Run a named Jarvis action skill directly |
| `/skills` | all | List all registered action skills |
| `/memory status` | all | Show memory DB stats |
| `/memory search <q>` | all | Search procedural memory |
| `/memory remove <id>` | all | Delete an edge/macro by ID |
| `/memory prune` | all | Remove low-confidence/stale edges |
| `/memory analyze` | all | Analyze memory health + suggest cleanup |
| `/memory export` | all | Export graph DB to JSON |
| `/memory index` | all | Re-index semantic embedding cache |
| `/logs [n]` | all | Tail last N lines of jarvis.log |
| `/logs analyze` | all | Parse log file for errors + warnings |
| `/logs export` | all | Export logs to file |
| `/channels` | all | List active channels + status |
| `/cron list` | all | List scheduled cron jobs |
| `/compact` | session | Compact session episodic context |
| `/whoami` | all | Show session ID + channel + user |
| `/export` | session | Export current session to markdown |
| `/debug <on\|off>` | session | Toggle debug logging |
| `/kill <session_id>` | all | Kill a session |
| `/restart` | gateway | Restart gateway daemon |
| `/send <channel> <message>` | all | Cross-channel message send |

---

## Phase 5 — TUI Application

### [NEW] `jarvis/tui/__init__.py`

### [NEW] `jarvis/tui/tui_app.py`
Interactive TUI using `rich` (layout, panels, live) + `prompt_toolkit` (input, history, tab-complete).

**Layout:**
```
╔══════════════════════════════════════════════════════════════════════╗
║  JARVIS v2  ●  Session: cli-default  ●  Model: local/gemma3:4b      ║
║  Channels: cli✅  telegram✅  telegram-test✅  ●  Uptime: 00:12:34   ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  [14:01:23]  You: open notepad                                       ║
║  [14:01:24]  Jarvis: ✅ Opened Notepad                               ║
║  [14:01:30]  You: /status                                            ║
║  [14:01:30]  Jarvis: [status panel]                                  ║
║                                                                      ║
╠══════════════════════════════════════════════════════════════════════╣
║  Jarvis›  _                           [Tab: complete] [↑: history]  ║
╚══════════════════════════════════════════════════════════════════════╝
```

Features:
- `rich.Live` + `rich.Layout` for live status bar
- `prompt_toolkit.PromptSession` with history file + tab-completion for `/` commands
- Slash command auto-complete (type `/me` → suggests `/memory`, `/models`)
- Status bar refreshes every 5s: shows channel states, active model, session ID
- Streaming output: LLM responses print token-by-token if streaming enabled
- Color-coded messages: user (cyan), Jarvis (green), errors (red), slash output (yellow)

### [NEW] `jarvis/tui/completer.py`
`prompt_toolkit` completer for slash commands + skill names.

### [NEW] `jarvis/tui/history.py`
`prompt_toolkit` file history stored in `~/.jarvis_history`.

### [NEW] `jarvis/tui/status_bar.py`
`rich` live status bar widget. Pulls data from `GatewayDaemon.status()`.

---

## Phase 6 — Memory Management CLI + Analysis

The `jarvis memory` subcommand tree — full inspection and management of all memory layers.

### [NEW] `jarvis/cli/commands/memory_cmd.py`

```
jarvis memory status
  → Prints:
      GraphDB: nodes=142, edges=87, macros=23
      Episodic: sessions=15, commands=432, success_rate=91%
      Semantic cache: 87 embeddings warmed
      Procedural: 34 rules seeded
      DB path: memory/jarvis.db  (2.4 MB)

jarvis memory search <query>
  → Fuzzy + semantic search across all edge triggers
  → Shows: trigger, skill, confidence, last_used, app

jarvis memory remove <edge_id>
  → Delete specific edge/macro by ID
  → Asks confirmation: "Remove edge 'edge.macro_abc123'? [y/N]"

jarvis memory prune [--min-confidence 0.4] [--max-age-days 30]
  → Remove edges below confidence threshold OR older than N days
  → Shows count of edges to prune, asks confirmation

jarvis memory analyze
  → Analysis report:
      ● Low-confidence edges: 12 (below 0.4)
      ● Stale edges (>30 days unused): 5
      ● Orphan nodes (no edges): 3
      ● Most-used macros: [list top 5]
      ● Least-used macros: [list bottom 5]
      ● Suggested prune: run 'jarvis memory prune'

jarvis memory export [--output memory_backup.json]
  → Full graph DB export to JSON (nodes + edges + episodic index)

jarvis memory index
  → Re-warm all semantic embedding vectors into RAM cache

jarvis memory clear-episodic [--channel telegram] [--confirm]
  → Delete episodic session logs for a specific channel (or all)
```

### [MODIFY] `jarvis/memory/memory_manager.py`
Add methods:
- `search(query, limit=20) -> list[GraphEdge]`
- `remove_edge(edge_id) -> bool`
- `prune(min_confidence, max_age_days) -> int` (returns count pruned)
- `analyze() -> MemoryAnalysisReport`
- `export(path) -> None`
- `stats() -> MemoryStats`

### [MODIFY] `jarvis/memory/layers/episodic.py`
- Add `channel` param to `__init__` for per-channel session dirs
- Add `clear(channel)` classmethod to delete session files

---

## Phase 7 — Log Analysis CLI

### [NEW] `jarvis/cli/commands/logs_cmd.py`

```
jarvis logs [--n 50]
  → Tail last N lines of logs/jarvis.log (default 50)
  → Color-coded: ERROR=red, WARNING=yellow, INFO=default

jarvis logs analyze [--level ERROR] [--since 1h]
  → Parse log file and summarize:
      ● Total lines: 1,243
      ● ERRORs: 3  → [list with line numbers]
      ● WARNINGs: 12
      ● LLM backend used: local/gemma3:4b (87%), mock (13%)
      ● Skills called: open_app×45, type_text×23, chat_reply×67...
      ● Avg response time: ~2.3s (estimated from timestamps)

jarvis logs export [--output jarvis_logs_20260511.txt]
  → Copy current log to output file

jarvis logs clear [--confirm]
  → Archive current log + start fresh

jarvis logs watch
  → Live tail (like 'tail -f'), color-coded, Ctrl+C to exit
```

**Also accessible as `/logs` and `/logs analyze` slash commands in TUI/Telegram.**

---

## Phase 8 — Config, Models, Channels, Skills, Cron Commands

### [NEW] `jarvis/cli/commands/config_cmd.py`
```
jarvis config get <key>            → Print value (e.g. jarvis config get llm.primary)
jarvis config set <key> <value>    → Write to config.yaml
jarvis config unset <key>          → Remove key
jarvis config file                 → Print path to config.yaml
jarvis config validate             → Check schema + required keys
jarvis config show                 → Pretty-print full config (secrets masked)
```

### [NEW] `jarvis/cli/commands/setup_cmd.py`
First-run interactive wizard:
1. Check Python version + dependencies
2. Check Ollama installed + running
3. Pull default LLM model (`gemma3:4b`)
4. Check/configure Telegram token
5. Seed memory graph (procedural)
6. Run `jarvis doctor` at end

### [NEW] `jarvis/cli/commands/models_cmd.py`
```
jarvis models list       → All backends (local, openai, tunneled, mock) + health
jarvis models status     → Active primary/fallback/emergency
jarvis models set <name> → Update config.yaml llm.primary
jarvis models scan       → Re-run health checks on all backends
```

### [NEW] `jarvis/cli/commands/channels_cmd.py`
```
jarvis channels list              → All channels + status (enabled/disabled/running)
jarvis channels status <name>     → Detailed channel status
jarvis channels logs <name> [n]   → Last N messages through a channel
jarvis channels add <name>        → Interactive setup wizard for a new channel
jarvis channels remove <name>     → Disable + remove from config
jarvis channels restart <name>    → Restart single channel thread
```

### [NEW] `jarvis/cli/commands/skills_cmd.py`
```
jarvis skills list               → All @skill-decorated functions with category + description
jarvis skills info <name>        → Full detail: params, triggers, category, is_cognitive
jarvis skills enable <name>      → Re-enable a disabled skill
jarvis skills disable <name>     → Disable (won't be dispatched)
jarvis skills run <name> [json]  → Directly execute a skill with params JSON
```

> [!NOTE]
> `jarvis skills` manages **Jarvis action skills** (Python `@skill` functions that execute OS operations). This is NOT the same as OpenClaw's markdown SKILL.md files.

### [NEW] `jarvis/cli/commands/cron_cmd.py`
```
jarvis cron list
jarvis cron add "<cron_expr>" "<jarvis_command>"
jarvis cron rm <id>
jarvis cron enable <id> / disable <id>
jarvis cron run <id>        → Manual trigger
jarvis cron status          → Next run times for all jobs
```

### [NEW] `jarvis/gateway/cron_scheduler.py`
Uses `APScheduler` (already approved as dependency). Stores jobs in `config.yaml` under `cron.jobs`.

### [NEW] `jarvis/cli/commands/doctor_cmd.py`
```
jarvis doctor
  Checking Python...       ✅ 3.11.x
  Checking Ollama...       ✅ running (gemma3:4b loaded)
  Checking memory DB...    ✅ jarvis.db 2.4MB, 142 nodes
  Checking log file...     ✅ logs/jarvis.log 512KB
  Checking config...       ✅ config.yaml valid
  Checking Telegram...     ⚠️  token not set (telegram disabled)
  Checking dependencies... ✅ all packages present
  Recommendations:
    → Run 'jarvis memory prune' (12 low-confidence edges)
    → Set TELEGRAM_TOKEN to enable Telegram channel
```

---

## Phase 9 — Gateway Config Updates

### [MODIFY] `jarvis/config/config.yaml`
Add new sections:

```yaml
gateway:
  host: 127.0.0.1
  port: 18789
  log_level: INFO

channels:
  cli:
    enabled: true
  telegram:
    enabled: false
    token: ${TELEGRAM_TOKEN}
    allowed_chat_ids: []
  telegram_test:
    enabled: false
  voice:
    enabled: false

memory:
  episodic_per_channel: true      # isolate episodic by channel
  episodic_dir: memory/episodic
  prune_age_days: 30
  prune_min_confidence: 0.4

cron:
  enabled: false
  jobs: []
```

---

## New Dependencies (`requirements.txt`)

```
rich>=13.0               # TUI rendering, panels, tables, live output
prompt_toolkit>=3.0      # Input history, tab-completion, async prompts
apscheduler>=3.10        # Cron scheduler
```

---

## File Change Summary

| File | Action | Phase |
|---|---|---|
| `jarvis.bat` | NEW | 1 |
| `jarvis/cli/__init__.py` | NEW | 1 |
| `jarvis/cli/main_cli.py` | NEW | 1 |
| `jarvis/cli/commands/config_cmd.py` | NEW | 8 |
| `jarvis/cli/commands/setup_cmd.py` | NEW | 8 |
| `jarvis/cli/commands/channels_cmd.py` | NEW | 8 |
| `jarvis/cli/commands/models_cmd.py` | NEW | 8 |
| `jarvis/cli/commands/skills_cmd.py` | NEW | 8 |
| `jarvis/cli/commands/memory_cmd.py` | NEW | 6 |
| `jarvis/cli/commands/logs_cmd.py` | NEW | 7 |
| `jarvis/cli/commands/cron_cmd.py` | NEW | 8 |
| `jarvis/cli/commands/doctor_cmd.py` | NEW | 8 |
| `jarvis/gateway/__init__.py` | NEW | 2 |
| `jarvis/gateway/gateway.py` | NEW | 2 |
| `jarvis/gateway/channel_manager.py` | NEW | 2 |
| `jarvis/gateway/session_manager.py` | NEW | 2 |
| `jarvis/gateway/cron_scheduler.py` | NEW | 8 |
| `jarvis/input/adapters.py` | MODIFY | 3 |
| `jarvis/input/channels/discord_adapter.py` | NEW stub | 3 |
| `jarvis/input/channels/webhook_adapter.py` | NEW stub | 3 |
| `jarvis/tui/__init__.py` | NEW | 5 |
| `jarvis/tui/tui_app.py` | NEW | 5 |
| `jarvis/tui/slash_handler.py` | NEW | 4 |
| `jarvis/tui/completer.py` | NEW | 5 |
| `jarvis/tui/status_bar.py` | NEW | 5 |
| `jarvis/tui/history.py` | NEW | 5 |
| `jarvis/memory/memory_manager.py` | MODIFY | 6 |
| `jarvis/memory/layers/episodic.py` | MODIFY | 6 |
| `jarvis/main.py` | MODIFY | 1 |
| `jarvis/config/config.yaml` | MODIFY | 9 |
| `requirements.txt` | MODIFY | all |

---

## Build Order & Execution Sequence

```
Phase 1  →  jarvis.bat + CLI skeleton (main_cli.py + subcommand stubs)
Phase 2  →  Gateway + ChannelManager + SessionManager
Phase 3  →  ChannelAdapter base class + update all adapters
Phase 4  →  SlashHandler (shared across all channels)
Phase 5  →  TUI (rich + prompt_toolkit)
Phase 6  →  Memory CLI (status/search/remove/analyze/export)
Phase 7  →  Log CLI (tail/analyze/watch)
Phase 8  →  Config/Models/Channels/Skills/Cron/Doctor commands
Phase 9  →  Config YAML updates + cron scheduler
```

---

## Verification Plan

### Phase 1
```bash
jarvis --help
jarvis version
jarvis status
```

### Phase 2 + 3
```bash
jarvis gateway start
jarvis channels list
# CLI + Telegram + Telegram-test all running in parallel
```

### Phase 4 (Slash in Telegram)
```
# Send "/status" in Telegram → same output as TUI /status
# Send "/memory search open notepad" → returns memory hits
# Send "/logs 10" → returns last 10 log lines
```

### Phase 5 (TUI)
```bash
jarvis tui
# /status → shows all 3 channels
# /model → model picker
# /memory analyze → memory health report
# /logs analyze → log error summary
# /reset → new session
# /exit
```

### Phase 6 (Memory CLI)
```bash
jarvis memory status
jarvis memory search "open notepad"
jarvis memory analyze
jarvis memory prune --min-confidence 0.3
jarvis memory export ./backup.json
```

### Phase 7 (Log CLI)
```bash
jarvis logs --n 20
jarvis logs analyze --level ERROR
jarvis logs watch
```

### Phase 8 (Skills CLI)
```bash
jarvis skills list
jarvis skills info open_app
jarvis skills run chat_reply '{"message": "hello"}'
jarvis doctor
```
