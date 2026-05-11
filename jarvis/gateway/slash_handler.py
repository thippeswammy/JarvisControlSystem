"""
Slash Handler
=============
Parses and executes /commands from any channel.
Shared logic between TUI, Telegram, and CLI.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

class SlashHandler:
    """
    Handles /status, /reset, /memory, /logs etc.
    Each Session owns one instance of this.
    """
    def __init__(self, session, gateway):
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
        
        logger.info(f"[SlashHandler] Executing {cmd} for session {self._session.id}")
        
        if cmd == "/help":
            return self._cmd_help()
        elif cmd == "/status":
            return self._cmd_status()
        elif cmd == "/reset":
            return self._cmd_reset()
        elif cmd == "/whoami":
            return f"Session: `{self._session.id}`\nChannel: `{self._session.channel}`\nUser: `{self._session.user_id}`"
        elif cmd == "/memory":
            return self._cmd_memory(args)
        elif cmd == "/logs":
            return self._cmd_logs(args)
        else:
            return f"Unknown command: `{cmd}`. Type `/help` for list."

    def _cmd_help(self) -> str:
        return (
            "Available commands:\n"
            "  /status  - Show system status\n"
            "  /reset   - Reset current session\n"
            "  /memory  - status | search <q>\n"
            "  /logs    - tail [n] | analyze\n"
            "  /whoami  - Show session info\n"
            "  /help    - Show this message"
        )

    def _cmd_status(self) -> str:
        s = self._gateway.status()
        channels_str = ", ".join([f"{c['name']} ({c['status']})" for c in s['channels']])
        return (
            f"🤖 **JARVIS Status**\n"
            f"● Running: {'✅' if s['running'] else '❌'}\n"
            f"● Active Channels: {channels_str}\n"
            f"● Total Sessions: {s['sessions']}\n"
            f"● Memory DB: `{s['memory']}`"
        )

    def _cmd_reset(self) -> str:
        self._session.episodic.clear()
        return "✅ Session reset. Episodic memory cleared."

    def _cmd_memory(self, args) -> str:
        if not args:
            return "Usage: `/memory status` or `/memory search <query>`"
        
        sub = args[0].lower()
        mem = self._session.episodic._MEMORY_ROOT.parent # This is a bit hacky, better to use self._gateway.session_mgr.memory
        # Actually, SlashHandler has access to self._gateway
        memory = self._gateway.session_mgr.memory
        
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
            if not query: return "Usage: `/memory search <query>`"
            results = memory.search_edges(query, limit=5)
            if not results: return f"No memory found for `{query}`"
            
            resp = [f"🔍 **Results for '{query}':**"]
            for edge, score in results:
                resp.append(f"● `{edge.id}` (Conf: {edge.confidence:.2f}, Score: {score})")
            return "\n".join(resp)
        else:
            return f"Unknown memory subcommand: `{sub}`"

    def _cmd_logs(self, args) -> str:
        from jarvis.cli.commands.logs_cmd import LogAnalyzer
        from pathlib import Path
        
        log_path = Path("logs/jarvis.log")
        analyzer = LogAnalyzer(str(log_path))
        
        if not args or args[0].lower() == "tail":
            n = 10
            if len(args) > 1:
                try: n = int(args[1])
                except: pass
            
            lines = analyzer.tail(n=n, color=False)
            return "📋 **Recent Logs:**\n```\n" + "\n".join(lines) + "\n```"
        
        elif args[0].lower() == "analyze":
            stats = analyzer.analyze()
            if "error" in stats: return f"❌ {stats['error']}"
            
            resp = [
                "📊 **Log Analysis (Last 1h)**",
                f"● Total Lines: {stats['total_lines']}",
                f"● Errors: {stats['levels'].get('ERROR', 0)}",
                f"● Warnings: {stats['levels'].get('WARNING', 0)}",
                f"● LLM Hits: {stats['ollama_hits']} (Ollama) / {stats['mock_hits']} (Mock)"
            ]
            return "\n".join(resp)
        else:
            return "Usage: `/logs tail [n]` or `/logs analyze`"
