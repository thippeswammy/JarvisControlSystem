# Jarvis Ecosystem — Full Implementation Plan
## Inspired by OpenClaw Architecture

Build Jarvis into a **production-grade, multi-channel AI agent system** with a rich CLI, a `--tui` interactive terminal, parallel agent sessions, a unified channel adapter layer, and a persistent gateway daemon.

---

## Background

Current state:
- `python -m jarvis.main` with flat flags: `--voice`, `--telegram`, `--telegram-test`, `--ollama`, `--command`
- Single agent, single channel at a time
- Memory: graph DB + episodic, no export/search CLI
- Skills: 10 builtins, no plugin system
- LLM: local (Ollama) → tunneled → openai → mock fallback chain

Target state (OpenClaw-inspired):
- `jarvis <command>` full CLI tree (like `openclaw <command>`)
- `jarvis tui` — interactive TUI with slash commands (`/status`, `/agent`, `/model`, `/session`, etc.)
- Multiple channels running **in parallel**: CLI + Telegram + Telegram-Test + future (Discord, WhatsApp, etc.)
- Multiple agents running in parallel with session isolation
- Gateway daemon managing all channel listeners
- Enhanced memory: `/memory search`, `/memory status`, `/memory index`
- Skills as loadable plugins
- Cron scheduler for recurring tasks

---

## User Review Required

> [!IMPORTANT]
> **Parallel channels** means the Gateway daemon will spin up all configured channels simultaneously. Each channel runs in its own thread/async task and routes through the same Orchestrator but in **isolated sessions**. Confirm this is what you want vs. a single active channel at a time.

> [!WARNING]
> The `jarvis tui` command will require `rich` and `prompt_toolkit` Python packages. These are not currently in requirements. Approve adding them.

> [!IMPORTANT]
> The **slash command system** in TUI is session-scoped. `/agent`, `/model`, `/session` changes apply only to the current TUI session, not to the running daemon/Telegram channels. Is this the correct behavior?

---

## Open Questions

> [!IMPORTANT]
> **Entry point name**: Should the CLI be invoked as `jarvis` (requires installing the package with `pip install -e .` and a `pyproject.toml` entry point) OR keep `python -m jarvis.main` and add a thin `jarvis.bat`/`jarvis.sh` wrapper script? Recommendation: `jarvis.bat` wrapper for zero-install friction on Windows.

> [!NOTE]
> **Agent definitions**: In OpenClaw, agents are named personas with different system prompts and model assignments. Do you want Jarvis to support **named agents** (e.g., `jarvis-coder`, `jarvis-researcher`) switchable at runtime via `/agent`? Or is there a single "JARVIS" persona?

> [!NOTE]
> **Memory persistence per channel**: Should Telegram sessions and CLI sessions share the same episodic + procedural memory, or be isolated? Current code shares one DB. Recommendation: share procedural (skills/macros) but isolate episodic per channel.

---

## Proposed Changes

### Phase 1 — Entry Point & CLI Command Tree

Build the `jarvis` CLI that mirrors the `openclaw <command>` tree.

---

#### [NEW] `jarvis/cli/__init__.py`
Empty init.

#### [NEW] `jarvis/cli/main_cli.py`
Top-level CLI entry point using `argparse` subcommands. Provides the full command tree:

```
jarvis [--dev] [--profile <name>] [--log-level] [--no-color] <command>

  setup          First-run wizard (config, Ollama pull, etc.)
  config         get / set / unset / file / validate
  status         Show gateway + channel + agent status
  health         Health check all backends (LLM, memory, channels)
  doctor         Diagnose common issues
  gateway        start / stop / restart / status / logs
  daemon         install / uninstall / start / stop / restart / status
  channels       list / status / add / remove / logs
  agents         list / add / delete / set-model
  agent          Switch active agent
  sessions       list / cleanup
  models         list / status / set / scan
  memory         status / search / index / export
  skills         list / info / enable / disable
  cron           list / add / rm / enable / disable / run
  logs           Tail gateway logs
  tui            Launch interactive TUI (alias: chat)
  chat           Alias for tui
  nodes          list / status / describe (future: mobile/remote nodes)
  version / -V   Print version
```

#### [MODIFY] `jarvis/main.py`
- Keep as the **programmatic wiring** module (`build_orchestrator`)
- Remove flat `argparse` from `main()` — delegate to `jarvis/cli/main_cli.py`
- `main()` becomes a thin shim that calls `cli_main()`

#### [NEW] `jarvis.bat` (project root)
```batch
@echo off
python -m jarvis.cli.main_cli %*
```
Zero-install launcher for Windows.

---

### Phase 2 — Gateway Daemon & Channel Manager

A persistent **Gateway** manages all channel listeners. Channels run in parallel threads.

---

#### [NEW] `jarvis/gateway/__init__.py`

#### [NEW] `jarvis/gateway/gateway.py`
```
GatewayDaemon
  ├── ChannelManager   — starts/stops channel threads
  ├── SessionManager   — one Session per channel+user pair
  ├── AgentRegistry    — named agents with model + system prompt
  └── CronScheduler    — recurring task runner
```

Key design:
- One `Orchestrator` instance per **session** (not per channel)
- Sessions are keyed by `(channel_id, user_id)`
- Gateway exposes internal WebSocket API on `localhost:18789` (matching OpenClaw default) for the TUI to connect to

#### [NEW] `jarvis/gateway/channel_manager.py`
```python
class ChannelManager:
    def start_channel(name, adapter, session_manager) -> thread
    def stop_channel(name)
    def list_channels() -> list[ChannelStatus]
    def channel_logs(name, n) -> list[str]
```

#### [NEW] `jarvis/gateway/session_manager.py`
```python
class Session:
    id: str
    channel: str
    user_id: str
    agent_name: str
    model_override: Optional[str]
    created_at: datetime
    orchestrator: Orchestrator   # isolated per session

class SessionManager:
    def get_or_create(channel, user_id) -> Session
    def list_sessions() -> list[Session]
    def cleanup_idle(max_age_minutes=60)
    def kill(session_id)
```

#### [NEW] `jarvis/gateway/agent_registry.py`
```python
@dataclass
class AgentDefinition:
    name: str
    system_prompt: str
    model: Optional[str]   # overrides router primary
    description: str

class AgentRegistry:
    def list() -> list[AgentDefinition]
    def get(name) -> AgentDefinition
    def register(agent: AgentDefinition)
    def set_active(session_id, agent_name)
```

Default agents loaded from `jarvis/config/agents.yaml`:
```yaml
agents:
  - name: jarvis
    description: "Default JARVIS assistant"
    model: null  # uses router default
  - name: jarvis-coder
    description: "Code-focused agent"
    model: openai/gpt-4o
  - name: jarvis-researcher
    description: "Deep research agent"
    model: local/ollama
```

---

### Phase 3 — Unified Channel Adapter Layer

Refactor all adapters behind a common interface so the Gateway can manage them uniformly.

---

#### [MODIFY] `jarvis/input/adapters.py`
Add base class and make all adapters conform:

```python
class ChannelAdapter(ABC):
    name: str                        # "cli", "telegram", "telegram-test"
    @abstractmethod
    def stream(self) -> Iterator[Utterance]: ...
    @abstractmethod
    def send(self, session_id: str, text: str): ...
    @abstractmethod
    def is_available(self) -> bool: ...
    def start_typing(self, session_id: str): pass   # optional
    def on_ready(self): pass                         # called after gateway starts
```

Existing adapters to update:
- `TextAdapter` → `CLIAdapter` (rename, implements `ChannelAdapter`)
- `TelegramAdapter` → implements `ChannelAdapter`
- `MockTelegramAdapter` → implements `ChannelAdapter`
- `VoiceAdapter` → implements `ChannelAdapter`

#### [NEW] `jarvis/input/channels/discord_adapter.py` *(stub)*
#### [NEW] `jarvis/input/channels/webhook_adapter.py` *(stub)*

---

### Phase 4 — TUI with Slash Commands

Interactive terminal UI using `rich` + `prompt_toolkit`.

---

#### [NEW] `jarvis/tui/__init__.py`

#### [NEW] `jarvis/tui/tui_app.py`
Main TUI application. Layout:

```
┌─────────────────────────────────────────────────────┐
│  JARVIS v2 ● Session: cli-default ● Agent: jarvis   │
│  Model: local/gemma3:4b ● Channels: 3 active        │
├─────────────────────────────────────────────────────┤
│  [conversation history — scrollable]                 │
│  > You: open notepad                                 │
│  > Jarvis: ✅ Opened Notepad                         │
├─────────────────────────────────────────────────────┤
│  Jarvis> _                                           │
└─────────────────────────────────────────────────────┘
```

Features:
- `rich.Live` for streaming output
- `prompt_toolkit` for input with history, tab-completion
- Slash command parser
- Status bar auto-refreshes every 5s

#### [NEW] `jarvis/tui/slash_commands.py`
Full slash command registry:

| Command | Description |
|---|---|
| `/help` | Show slash command help |
| `/status` | Show gateway + channel + session status |
| `/agent [name]` | Switch agent or open picker |
| `/agents` | List all agents |
| `/session [key]` | Switch session or open picker |
| `/sessions` | List all sessions |
| `/model [provider/model]` | Set model for this session |
| `/models` | List available models |
| `/think <off\|low\|medium\|high>` | Set thinking level |
| `/fast <on\|off>` | Toggle fast mode |
| `/verbose <on\|off>` | Toggle verbose logging |
| `/usage` | Show token usage for this session |
| `/new` or `/reset` | Reset the current session |
| `/abort` | Abort active run |
| `/settings` | Open config in editor |
| `/exit` or `/quit` | Exit TUI |
| `/commands` | List all slash commands |
| `/skill <name>` | Run a skill by name |
| `/memory search <query>` | Search procedural memory |
| `/memory status` | Show memory DB stats |
| `/export` | Export session to HTML |
| `/whoami` | Show session ID + channel |
| `/channels` | List active channels |
| `/logs [n]` | Tail last N gateway log lines |
| `/cron list` | List scheduled jobs |
| `/compact` | Compact session context |
| `/kill [session_id]` | Kill a session |
| `/subagents` | List parallel running subagents |
| `/debug` | Toggle debug logging |
| `/restart` | Restart gateway |

#### [NEW] `jarvis/tui/session_picker.py`
Interactive picker for `/sessions` and `/agents` using `rich` table selection.

#### [NEW] `jarvis/tui/model_picker.py`
Interactive picker for `/models` — queries LLM router for available backends.

---

### Phase 5 — Parallel Multi-Agent Support

Allow multiple agent runs concurrently within a session.

---

#### [NEW] `jarvis/brain/subagent_runner.py`
```python
class SubagentRun:
    id: str
    session_id: str
    prompt: str
    status: Literal["running", "done", "failed", "killed"]
    result: Optional[list[SkillResult]]
    thread: threading.Thread

class SubagentManager:
    def spawn(session_id, prompt, orchestrator) -> SubagentRun
    def list(session_id) -> list[SubagentRun]
    def kill(run_id)
    def steer(run_id, guidance: str)   # inject mid-run guidance
    def logs(run_id) -> list[str]
```

The TUI `/subagents` command interfaces with this.

---

### Phase 6 — Enhanced Memory CLI

Surface memory operations as first-class CLI commands.

---

#### [MODIFY] `jarvis/cli/commands/memory_cmd.py` *(new file)*
```
jarvis memory status       → DB stats: node count, edge count, macro count
jarvis memory search <q>   → Fuzzy search procedural memory
jarvis memory index        → Re-index semantic encoder
jarvis memory export       → Dump graph to JSON/YAML
jarvis memory prune        → Remove stale/low-confidence edges
```

#### [MODIFY] `jarvis/memory/memory_manager.py`
- Add `search(query) -> list[GraphNode]`
- Add `export(path)` method
- Add `prune(min_confidence, max_age_days)` method

---

### Phase 7 — Config & Setup Commands

---

#### [NEW] `jarvis/cli/commands/config_cmd.py`
```
jarvis config get <key>       → Print config value
jarvis config set <key> <val> → Persist to config.yaml
jarvis config file            → Print path to config.yaml
jarvis config validate        → Validate schema
```

#### [NEW] `jarvis/cli/commands/setup_cmd.py`
First-run wizard:
1. Check Ollama installed + running
2. Pull default model
3. Check/set Telegram token
4. Seed memory graph
5. Run `jarvis health` at end

#### [NEW] `jarvis/cli/commands/channels_cmd.py`
```
jarvis channels list          → Show all configured channels + status
jarvis channels status <name> → Detailed status for one channel
jarvis channels logs <name>   → Tail channel logs
jarvis channels add <name>    → Interactive wizard to add a channel
jarvis channels remove <name> → Disable + remove channel config
```

#### [NEW] `jarvis/cli/commands/models_cmd.py`
```
jarvis models list            → List all LLM backends + health
jarvis models status          → Show active primary/fallback
jarvis models set <name>      → Change primary in config.yaml
jarvis models scan            → Re-run health checks
```

#### [NEW] `jarvis/cli/commands/cron_cmd.py`
```
jarvis cron list
jarvis cron add "<cron_expr>" "<command>"
jarvis cron rm <id>
jarvis cron enable/disable <id>
jarvis cron run <id>          → Manual trigger
```

#### [NEW] `jarvis/gateway/cron_scheduler.py`
Uses APScheduler or simple threading with cron expressions.

---

### Supporting Infrastructure

#### [NEW] `jarvis/config/agents.yaml`
Default agent definitions (JARVIS, JARVIS-Coder, JARVIS-Researcher).

#### [MODIFY] `jarvis/config/config.yaml`
Add sections:
```yaml
gateway:
  host: 127.0.0.1
  port: 18789

channels:
  cli:
    enabled: true
  telegram:
    enabled: false
    token: ${TELEGRAM_TOKEN}
    allowed_chat_ids: []
  telegram_test:
    enabled: false

agents:
  default: jarvis

memory:
  episodic_per_channel: true   # isolate episodic by channel
  prune_age_days: 30
  prune_min_confidence: 0.4

cron:
  enabled: false
  jobs: []
```

#### [NEW] `requirements.txt` additions
```
rich>=13.0
prompt_toolkit>=3.0
apscheduler>=3.10   # for cron
```

---

## File Change Summary

| File | Action | Phase |
|---|---|---|
| `jarvis/cli/__init__.py` | NEW | 1 |
| `jarvis/cli/main_cli.py` | NEW | 1 |
| `jarvis/cli/commands/config_cmd.py` | NEW | 7 |
| `jarvis/cli/commands/setup_cmd.py` | NEW | 7 |
| `jarvis/cli/commands/channels_cmd.py` | NEW | 7 |
| `jarvis/cli/commands/models_cmd.py` | NEW | 7 |
| `jarvis/cli/commands/memory_cmd.py` | NEW | 6 |
| `jarvis/cli/commands/cron_cmd.py` | NEW | 7 |
| `jarvis.bat` | NEW | 1 |
| `jarvis/gateway/__init__.py` | NEW | 2 |
| `jarvis/gateway/gateway.py` | NEW | 2 |
| `jarvis/gateway/channel_manager.py` | NEW | 2 |
| `jarvis/gateway/session_manager.py` | NEW | 2 |
| `jarvis/gateway/agent_registry.py` | NEW | 2 |
| `jarvis/gateway/cron_scheduler.py` | NEW | 7 |
| `jarvis/input/adapters.py` | MODIFY | 3 |
| `jarvis/input/channels/discord_adapter.py` | NEW (stub) | 3 |
| `jarvis/input/channels/webhook_adapter.py` | NEW (stub) | 3 |
| `jarvis/tui/__init__.py` | NEW | 4 |
| `jarvis/tui/tui_app.py` | NEW | 4 |
| `jarvis/tui/slash_commands.py` | NEW | 4 |
| `jarvis/tui/session_picker.py` | NEW | 4 |
| `jarvis/tui/model_picker.py` | NEW | 4 |
| `jarvis/brain/subagent_runner.py` | NEW | 5 |
| `jarvis/memory/memory_manager.py` | MODIFY | 6 |
| `jarvis/main.py` | MODIFY | 1 |
| `jarvis/config/agents.yaml` | NEW | 2 |
| `jarvis/config/config.yaml` | MODIFY | 2 |

---

## Verification Plan

### After Phase 1
```bash
jarvis --help
jarvis status
jarvis health
jarvis doctor
```

### After Phase 2 + 3
```bash
jarvis gateway start
jarvis channels list
# Telegram + CLI both active in parallel
```

### After Phase 4 (TUI)
```bash
jarvis tui
# Inside TUI:
# /status → shows channels
# /models → picks model
# /agent jarvis-coder → switches agent
# /reset → new session
# /exit
```

### After Phase 5 (Parallel agents)
```python
# TUI: run two commands back-to-back without waiting
# /subagents → shows both running
```

### After Phase 6 (Memory CLI)
```bash
jarvis memory status
jarvis memory search "open notepad"
jarvis memory export ./backup.json
```
