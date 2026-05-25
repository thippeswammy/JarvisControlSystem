"""
Slash Handler
=============
Parses and executes /commands from any channel.
Uses the pluggable SlashRegistry to discover and route commands dynamically.
"""

import asyncio
import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from jarvis.gateway.slash_registry import SlashRegistry

logger = logging.getLogger(__name__)


# ── Registry command handlers ────────────────────────────────

def _cmd_help(args: List[str], session, gateway) -> str:
    commands = SlashRegistry.list_commands()
    resp = ["🤖 **JARVIS Available Commands:**"]
    categories = {}
    for entry in commands.values():
        categories.setdefault(entry.category, []).append(entry)

    for cat in sorted(categories.keys()):
        resp.append(f"\n📂 **{cat.upper()}**")
        for entry in sorted(categories[cat], key=lambda e: e.cmd):
            resp.append(f"  `{entry.cmd}` - {entry.description}")

    # Add agent shorthand note
    resp.append("\n💡 *Tip: You can shorthand execute any agent by typing `/<AgentName> <task>`!*")
    return "\n".join(resp)


def _cmd_status(args: List[str], session, gateway) -> str:
    s = gateway.status()
    channels_str = ", ".join([f"{c['name']} ({c['status']})" for c in s["channels"]])
    return (
        f"🤖 **JARVIS Status**\n"
        f"● Running: {'✅' if s['running'] else '❌'}\n"
        f"● Active Channels: {channels_str}\n"
        f"● Total Sessions: {s['sessions']}\n"
        f"● Memory DB: `{s['memory']}`"
    )


def _cmd_reset(args: List[str], session, gateway) -> str:
    session.episodic.clear()
    return "[OK] Session reset. Episodic memory cleared."


def _cmd_whoami(args: List[str], session, gateway) -> str:
    return f"Session: `{session.id}`\nChannel: `{session.channel}`\nUser: `{session.user_id}`"


def _cmd_memory(args: List[str], session, gateway) -> str:
    if not args:
        return "Usage: `/memory status` or `/memory search <query>`"

    sub = args[0].lower()
    memory = gateway.memory

    if sub == "status":
        stat = memory.get_stats()
        return (
            f"🧠 **Memory Stats**\n"
            f"● Nodes: {stat['nodes']}\n"
            f"● Edges: {stat['edges']}\n"
            f"● Success Rate: {stat['success_rate']}%"
        )
    elif sub == "search":
        query = " ".join(args[1:])
        if not query:
            return "Usage: `/memory search <query>`"
        results = memory.search_edges(query, limit=5)
        if not results:
            return f"No memory found for `{query}`"

        resp = [f"🔍 **Results for '{query}':**"]
        for edge, score in results:
            resp.append(f"● `{edge.id}` (Conf: {edge.confidence:.2f}, Score: {score})")
        return "\n".join(resp)
    else:
        return f"Unknown memory subcommand: `{sub}`"


def _cmd_logs(args: List[str], session, gateway) -> str:
    from pathlib import Path
    from jarvis.cli.commands.logs_cmd import LogAnalyzer

    log_path = Path("logs/jarvis.log")
    analyzer = LogAnalyzer(str(log_path))

    if not args or args[0].lower() == "tail":
        n = 10
        if len(args) > 1:
            try:
                n = int(args[1])
            except ValueError:
                pass

        lines = analyzer.tail(n=n, color=False)
        return "📋 **Recent Logs:**\n```\n" + "\n".join(lines) + "\n```"

    elif args[0].lower() == "analyze":
        stats = analyzer.analyze()
        if "error" in stats:
            return f"❌ ERR: {stats['error']}"

        resp = [
            "📊 **Log Analysis (Last 1h)**",
            f"● Total Lines: {stats['total_lines']}",
            f"● Errors: {stats['levels'].get('ERROR', 0)}",
            f"● Warnings: {stats['levels'].get('WARNING', 0)}",
            f"● LLM Hits: {stats['ollama_hits']} (Ollama) / {stats['mock_hits']} (Mock)",
        ]
        return "\n".join(resp)
    else:
        return "Usage: `/logs tail [n]` or `/logs analyze`"


def _cmd_skills(args: List[str], session, gateway) -> str:
    bus = gateway.bus
    if not bus:
        return "❌ SkillBus not configured."
    skills = bus.list_skills()
    resp = ["🛠️ **Available Skills:**"]
    for s in skills:
        entry = bus.get_skill(s)
        doc = entry.fn.__doc__ or "No description."
        doc = doc.strip().split("\n")[0]
        resp.append(f"● `{s}` - {doc}")
    return "\n".join(resp)


def _cmd_agents(args: List[str], session, gateway) -> str:
    agent_bus = getattr(gateway, "agent_bus", None)
    if not agent_bus:
        return "❌ AgentBus not configured."
    agents = sorted(agent_bus._registry.keys())
    resp = ["🤖 **Registered Agents:**"]
    for a in agents:
        agent = agent_bus._registry[a]
        desc = getattr(agent, "description", "")
        if not desc and agent.__doc__:
            desc = agent.__doc__.strip().split("\n")[0]
        safe = "Concurrently" if agent.parallel_safe else "Sequentially"
        resp.append(f"● `{a}` - {desc} ({safe})")
    return "\n".join(resp)


def _cmd_mcp(args: List[str], session, gateway) -> str:
    mcp_bus = getattr(gateway, "mcp_bus", None)
    if not mcp_bus:
        return "❌ MCPBus not configured."
    servers = mcp_bus.list_servers()
    if not servers:
        return "ℹ️ No MCP servers registered."

    resp = ["🔌 **Registered MCP Servers & Tools:**"]
    for s in servers:
        adapter = mcp_bus._registry[s]
        status = "🟢 healthy" if adapter.health_check() else "🔴 offline/unreachable"
        resp.append(f"\n🖥️ **{s.upper()}** ({status})")
        tools = adapter.list_tools()
        for t in tools:
            params_str = ", ".join(t.get("params", {}).get("properties", {}).keys())
            resp.append(f"  ● `{t['name']}({params_str})` - {t.get('description', '')}")
    return "\n".join(resp)


def _cmd_spin(args: List[str], session, gateway) -> str:
    if not args or len(args) < 2:
        return "Usage: `/spin <agent> <task>`"

    agent_name = args[0]
    task = " ".join(args[1:])

    agent_bus = getattr(gateway, "agent_bus", None)
    if not agent_bus:
        return "❌ AgentBus not configured."

    logger.info(f"[SlashHandler] Spawning agent '{agent_name}' for task: {task!r}")
    res = agent_bus.run_single(agent_name, task, {"router": gateway.router, "agent_bus": agent_bus})
    status = "✅ Success" if res.success else "❌ Failed"
    return f"**Agent Execution Result:**\n● Agent: `{agent_name}`\n● Status: {status}\n● Output: {res.output}"


def _cmd_multiagents(args: List[str], session, gateway) -> str:
    if not args or "--" not in args:
        return "Usage: `/multiagents <agent1> <agent2> ... -- <task>`"

    split_idx = args.index("--")
    agents = args[:split_idx]
    task = " ".join(args[split_idx + 1:])

    if not agents or not task:
        return "Usage: `/multiagents <agent1> <agent2> ... -- <task>`"

    agent_bus = getattr(gateway, "agent_bus", None)
    if not agent_bus:
        return "❌ AgentBus not configured."

    from jarvis.skills.builtins.plugin_skill import _run_async_in_thread

    tasks = [(a, task) for a in agents]
    logger.info(f"[SlashHandler] Spawning {len(agents)} agents in parallel: {agents}")
    coro = agent_bus.run_parallel(tasks, {"router": gateway.router, "agent_bus": agent_bus})
    results = _run_async_in_thread(coro)

    resp = ["👥 **Parallel Agents Execution Results:**"]
    for r in results:
        status = "✅ Success" if r.success else "❌ Failed"
        resp.append(f"\n● **{r.agent_name}** ({status}):\n{r.output}")
    return "\n".join(resp)


def _cmd_tool(args: List[str], session, gateway) -> str:
    if len(args) < 2:
        return "Usage: `/tool <server> <tool> [params_json_or_key=val]`"

    server = args[0]
    tool = args[1]
    params = {}

    if len(args) > 2:
        params_str = " ".join(args[2:]).strip()
        if params_str.startswith("{"):
            try:
                params = json.loads(params_str)
            except Exception as exc:
                return f"❌ Invalid JSON params: {exc}"
        else:
            for kv in params_str.split():
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    params[k] = v

    mcp_bus = getattr(gateway, "mcp_bus", None)
    if not mcp_bus:
        return "❌ MCPBus not configured."

    logger.info(f"[SlashHandler] Directly calling MCP tool {server}/{tool} with {params}")
    res = mcp_bus.call(server, tool, params)
    if "error" in res:
        return f"❌ **Error calling MCP Tool {server}/{tool}:**\n{res['error']}"
    return f"🟢 **MCP Tool {server}/{tool} Result:**\n{res.get('result', res)}"


def _cmd_reload(args: List[str], session, gateway) -> str:
    bus = gateway.bus
    agent_bus = getattr(gateway, "agent_bus", None)
    mcp_bus = getattr(gateway, "mcp_bus", None)

    msg = []
    if bus:
        bus._registry.clear()
        bus._discovered = False
        bus.discover()
        msg.append(f"● Skills reloaded (Total: {len(bus._registry)})")

    if agent_bus:
        agent_bus._registry.clear()
        agent_bus._discovered = False
        agent_bus.discover()
        msg.append(f"● Agents reloaded (Total: {len(agent_bus._registry)})")

    if mcp_bus:
        mcp_bus.shutdown_all()
        mcp_bus._registry.clear()
        mcp_bus._discovered = False
        mcp_bus.discover()
        msg.append(f"● MCP servers reloaded (Total: {len(mcp_bus._registry)})")

    return "🔄 **System Hot-Reload Complete:**\n" + "\n".join(msg)


def _cmd_new_session(args: List[str], session, gateway) -> str:
    """
    /new_session  — Wipe all agent memory and start a 100% clean session.

    Workflow:
      1. Flush + close the current MemoryManager DB connection.
      2. Archive jarvis.db (+ WAL/SHM) and the episodic/ folder into
         memory/archive/<timestamp>/.
      3. Delete the live DB files.
      4. Re-initialise MemoryManager on the gateway so new queries get
         a fresh SQLite file.
      5. Kill every existing session so the next message creates a blank one.
      6. Return a summary of what was archived/deleted.
    """
    memory = getattr(gateway, "memory", None)
    if not memory:
        return "❌ MemoryManager is not initialised — cannot reset."

    # ── 1. Determine paths ──────────────────────────────────────────
    try:
        live_db_path = Path(memory.get_db_path())
    except Exception as exc:
        return f"❌ Could not resolve DB path: {exc}"

    memory_dir = live_db_path.parent          # e.g. .../memory/
    episodic_dir = memory_dir / "episodic"    # e.g. .../memory/episodic/

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_dir = memory_dir / "archive" / ts
    archive_dir.mkdir(parents=True, exist_ok=True)

    archived: list[str] = []
    deleted: list[str] = []
    errors: list[str] = []

    # ── 2. Close the live DB to release file locks ──────────────────
    try:
        memory.close()
        logger.info("[/new_session] MemoryManager DB closed.")
    except Exception as exc:
        errors.append(f"DB close warning: {exc}")

    # ── 3. Archive + delete DB files (db, wal, shm) ─────────────────
    for suffix in ["", "-wal", "-shm"]:
        candidate = Path(str(live_db_path) + suffix)
        if candidate.exists():
            dest = archive_dir / candidate.name
            try:
                shutil.copy2(str(candidate), str(dest))
                archived.append(candidate.name)
                os.remove(str(candidate))
                deleted.append(candidate.name)
                logger.info(f"[/new_session] Archived & deleted: {candidate.name}")
            except Exception as exc:
                errors.append(f"Could not archive {candidate.name}: {exc}")

    # ── 4. Archive + delete episodic memory folder ──────────────────
    if episodic_dir.exists() and any(episodic_dir.iterdir()):
        dest_ep = archive_dir / "episodic"
        try:
            shutil.copytree(str(episodic_dir), str(dest_ep))
            shutil.rmtree(str(episodic_dir))
            episodic_dir.mkdir(exist_ok=True)   # recreate empty dir
            archived.append("episodic/")
            deleted.append("episodic/")
            logger.info("[/new_session] Episodic memory archived & cleared.")
        except Exception as exc:
            errors.append(f"Could not archive episodic: {exc}")

    # ── 5. Re-initialise MemoryManager with a fresh DB ──────────────
    try:
        from jarvis.memory.memory_manager import MemoryManager
        from jarvis.memory.layers.procedural import ProceduralMemory

        new_memory = MemoryManager(db_path=str(live_db_path))
        gateway.memory = new_memory

        # Re-seed procedural memory (settings graph etc.)
        proc = ProceduralMemory(new_memory.get_db())
        proc.seed_settings_graph()

        # Propagate new memory to SessionManager and AgentBus
        if gateway.session_mgr:
            gateway.session_mgr._memory = new_memory
        agent_bus = getattr(gateway, "agent_bus", None)
        if agent_bus:
            agent_bus._memory = new_memory

        logger.info("[/new_session] Fresh MemoryManager initialised.")
    except Exception as exc:
        errors.append(f"MemoryManager re-init failed: {exc}")
        logger.exception("[/new_session] MemoryManager re-init error")

    # ── 6. Kill all existing sessions ───────────────────────────────
    killed_sessions = 0
    if gateway.session_mgr:
        for sess in list(gateway.session_mgr.list_sessions()):
            gateway.session_mgr.kill(sess.id)
            killed_sessions += 1
        logger.info(f"[/new_session] Killed {killed_sessions} session(s).")

    # ── 7. Build response ────────────────────────────────────────────
    lines = [
        "🧹 **New Session Started — Memory Wiped!**",
        f"📁 Archive: `memory/archive/{ts}/`",
        f"● Archived: {', '.join(archived) or 'nothing'}",
        f"● Deleted:  {', '.join(deleted) or 'nothing'}",
        f"● Sessions killed: {killed_sessions}",
        "● Fresh DB seeded with procedural memory.",
    ]
    if errors:
        lines.append("\n⚠️ **Warnings:**")
        for err in errors:
            lines.append(f"  • {err}")
    lines.append("\n✅ Send your next message to begin a completely fresh context!")
    return "\n".join(lines)


# ── Register Core Commands ──────────────────────────────────

SlashRegistry.register("/help", _cmd_help, "Show this help catalog message", "general")
SlashRegistry.register("/status", _cmd_status, "Show system health and active sessions", "general")
SlashRegistry.register("/reset", _cmd_reset, "Reset current session and episodic memory", "general")
SlashRegistry.register("/whoami", _cmd_whoami, "Show current session information", "general")
SlashRegistry.register("/memory", _cmd_memory, "status | search <query> - Search long-term memory", "general")
SlashRegistry.register("/logs", _cmd_logs, "tail [n] | analyze - Check logs", "general")

SlashRegistry.register("/skills", _cmd_skills, "List all available skills", "plugin")
SlashRegistry.register("/agents", _cmd_agents, "List all registered autonomous agents", "plugin")
SlashRegistry.register("/mcp", _cmd_mcp, "List all registered MCP servers and tools", "plugin")
SlashRegistry.register("/spin", _cmd_spin, "<agent> <task> - Execute a single agent", "plugin")
SlashRegistry.register("/agent", _cmd_spin, "<agent> <task> - Alias for /spin", "plugin")
SlashRegistry.register("/multiagents", _cmd_multiagents, "<a1> <a2> ... -- <task> - Execute agents in parallel", "plugin")
SlashRegistry.register("/tool", _cmd_tool, "<server> <tool> [params] - Direct call to MCP tool", "plugin")
SlashRegistry.register("/reload", _cmd_reload, "Hot-reload skills, agents, and MCP configs", "plugin")
SlashRegistry.register("/new_session", _cmd_new_session, "Wipe all memory & start 100% clean session", "general")


class SlashHandler:
    """Handles parsing and routing of /commands from TUI, Telegram, or CLI."""

    def __init__(self, session, gateway) -> None:
        self._session = session
        self._gateway = gateway

    def is_slash(self, text: str) -> bool:
        return text.strip().startswith("/")

    def handle(self, text: str) -> Optional[str]:
        if not self.is_slash(text):
            return None

        parts = text.strip().split()
        cmd = parts[0].lower()
        args = parts[1:]

        logger.info(f"[SlashHandler] Dispatching command {cmd} for session {self._session.id}")

        # 1. Try Registry
        res = SlashRegistry.handle(cmd, args, self._session, self._gateway)
        if res is not None:
            return res

        # 2. Try Agent Name Shorthand: /<agent_name> <task>
        agent_name = cmd[1:]
        agent_bus = getattr(self._gateway, "agent_bus", None)
        if agent_bus and agent_name in agent_bus._registry:
            task = " ".join(args)
            return _cmd_spin([agent_name, task], self._session, self._gateway)

        return f"Unknown command: `{cmd}`. Type `/help` for list."
