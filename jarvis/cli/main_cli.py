import argparse
import sys
import logging
from pathlib import Path

# Add project root to path so we can import jarvis modules
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from jarvis.main import build_orchestrator

logger = logging.getLogger("jarvis.cli")

def cli_main():
    parser = argparse.ArgumentParser(
        description="Jarvis v2.1 — Iron Man Architecture CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  jarvis tui
  jarvis status
  jarvis memory status
  jarvis gateway start
        """
    )
    
    parser.add_argument("--dev", action="store_true", help="Enable development mode")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="Set logging level")
    parser.add_argument("--no-color", action="store_true", help="Disable color output")
    parser.add_argument("--profile", default="default", help="Configuration profile to use")
    parser.add_argument("-V", "--version", action="version", version="Jarvis v2.1.0")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # --- Setup ---
    subparsers.add_parser("setup", help="First-run wizard")

    # --- Config ---
    config_parser = subparsers.add_parser("config", help="Configuration management")
    config_subs = config_parser.add_subparsers(dest="subcommand")
    config_subs.add_parser("get", help="Get a config value").add_argument("key")
    config_subs.add_parser("set", help="Set a config value").add_argument("key"); config_subs.add_parser("set").add_argument("value")
    config_subs.add_parser("unset", help="Unset a config value").add_argument("key")
    config_subs.add_parser("file", help="Print config file path")
    config_subs.add_parser("validate", help="Validate config schema")

    # --- Status/Health ---
    subparsers.add_parser("status", help="Show system snapshot")
    subparsers.add_parser("health", help="Check subsystem health")
    subparsers.add_parser("doctor", help="Diagnose and fix issues")

    # --- Gateway/Daemon ---
    gateway_parser = subparsers.add_parser("gateway", help="Gateway management")
    gateway_subs = gateway_parser.add_subparsers(dest="subcommand")
    for cmd in ["start", "stop", "restart", "status", "logs"]:
        gateway_subs.add_parser(cmd)

    daemon_parser = subparsers.add_parser("daemon", help="Daemon management")
    daemon_subs = daemon_parser.add_subparsers(dest="subcommand")
    for cmd in ["install", "uninstall", "start", "stop", "restart", "status"]:
        daemon_subs.add_parser(cmd)

    # --- Channels ---
    channels_parser = subparsers.add_parser("channels", help="Channel management")
    channels_subs = channels_parser.add_subparsers(dest="subcommand")
    channels_subs.add_parser("list")
    channels_subs.add_parser("status").add_argument("name")
    channels_subs.add_parser("add").add_argument("name")
    channels_subs.add_parser("remove").add_argument("name")
    channels_subs.add_parser("logs").add_argument("name")

    # --- Sessions ---
    sessions_parser = subparsers.add_parser("sessions", help="Session management")
    sessions_subs = sessions_parser.add_subparsers(dest="subcommand")
    sessions_subs.add_parser("list")
    sessions_subs.add_parser("cleanup")
    sessions_subs.add_parser("kill").add_argument("id")

    # --- Models ---
    models_parser = subparsers.add_parser("models", help="Model management")
    models_subs = models_parser.add_subparsers(dest="subcommand")
    models_subs.add_parser("list")
    models_subs.add_parser("status")
    models_subs.add_parser("set").add_argument("name")
    models_subs.add_parser("scan")

    # --- Memory ---
    memory_parser = subparsers.add_parser("memory", help="Memory management")
    memory_subs = memory_parser.add_subparsers(dest="subcommand")
    memory_subs.add_parser("status")
    memory_subs.add_parser("search").add_argument("query")
    memory_subs.add_parser("remove").add_argument("id")
    memory_subs.add_parser("prune")
    memory_subs.add_parser("analyze")
    memory_subs.add_parser("export")
    memory_subs.add_parser("index")

    # --- Logs ---
    logs_parser = subparsers.add_parser("logs", help="Log management")
    logs_subs = logs_parser.add_subparsers(dest="subcommand")
    logs_subs.add_parser("tail").add_argument("n", type=int, default=50, nargs='?')
    logs_subs.add_parser("analyze")
    logs_subs.add_parser("export")
    logs_subs.add_parser("clear")

    # --- Skills ---
    skills_parser = subparsers.add_parser("skills", help="Skill management")
    skills_subs = skills_parser.add_subparsers(dest="subcommand")
    skills_subs.add_parser("list")
    skills_subs.add_parser("info").add_argument("name")
    skills_subs.add_parser("enable").add_argument("name")
    skills_subs.add_parser("disable").add_argument("name")
    skills_subs.add_parser("run").add_argument("name"); skills_subs.add_parser("run").add_argument("params", nargs='?')

    # --- Cron ---
    cron_parser = subparsers.add_parser("cron", help="Cron management")
    cron_subs = cron_parser.add_subparsers(dest="subcommand")
    cron_subs.add_parser("list")
    cron_subs.add_parser("add").add_argument("cron_expr"); cron_subs.add_parser("add").add_argument("command")
    cron_subs.add_parser("rm").add_argument("id")
    cron_subs.add_parser("enable").add_argument("id")
    cron_subs.add_parser("disable").add_argument("id")
    cron_subs.add_parser("run").add_argument("id")

    # --- TUI ---
    subparsers.add_parser("tui", help="Launch interactive TUI")
    subparsers.add_parser("chat", help="Launch interactive TUI (alias)")

    args = parser.parse_args()

    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    if not args.command:
        parser.print_help()
        return

    from jarvis.gateway.gateway import GatewayDaemon
    gateway = GatewayDaemon(profile=args.profile)

    # Bootstrap gateway for commands that need system access
    if args.command not in ["tui", "chat", "config", "setup"]:
        try:
            gateway.bootstrap()
        except Exception as e:
            if args.command != "gateway":
                logger.warning(f"⚠️ Gateway bootstrap failed: {e}. Some data may be unavailable.")

    # Basic command routing
    if args.command in ["tui", "chat"]:
        from jarvis.tui.tui_app import main as tui_main
        tui_main()
    
    elif args.command == "gateway":
        if args.subcommand == "start":
            print("🛰 Starting Jarvis Gateway...")
            gateway.bootstrap()
            gateway.start()
        elif args.subcommand == "status":
            stat = gateway.status()
            print(f"🛰 Gateway Status: {'✅ Running' if stat['running'] else '❌ Stopped'}")
            print(f"  Sessions: {stat['sessions']}")
            print(f"  Memory: {stat['memory']}")
            print("  Channels:")
            for ch in stat['channels']:
                icon = "✅" if ch['status'] == "running" else "⚪"
                print(f"    {icon} {ch['name']} ({ch['status']})")
        else:
            print(f"Gateway subcommand '{args.subcommand}' not yet implemented.")

    elif args.command == "status":
        stat = gateway.status()
        print("📊 Jarvis System Snapshot:")
        print(f"  Gateway: {'✅ Running' if stat['running'] else '❌ Offline'}")
        print(f"  Active Sessions: {stat['sessions']}")
        print(f"  Active Channels: {len([c for c in stat['channels'] if c['status'] == 'running'])}")
    
    elif args.command == "memory":
        from rich.table import Table
        from rich.panel import Panel
        
        if not gateway.memory:
            print("❌ Error: Memory system not initialized. Check your configuration.")
            return

        if args.subcommand == "status":
            stat = gateway.memory.get_stats()
            table = Table(title="🧠 Memory System Status", border_style="cyan")
            table.add_column("Metric", style="bold")
            table.add_column("Value")
            
            table.add_row("Nodes", str(stat["nodes"]))
            table.add_row("Edges (Paths)", str(stat["edges"]))
            table.add_row("Apps Registered", str(stat["apps"]))
            table.add_row("Total Executions", str(stat["total_runs"]))
            table.add_row("Success Rate", f"{stat['success_rate']}%")
            table.add_row("DB Size", f"{stat['db_size_kb']} KB")
            table.add_row("DB Path", stat["db_path"])
            
            from rich import print as rprint
            rprint(Panel(table, border_style="cyan"))

        elif args.subcommand == "search":
            results = gateway.memory.search_edges(args.query)
            if not results:
                rprint(f"❌ No memory hits for '{args.query}'")
                return
            
            table = Table(title=f"🔍 Memory Search: '{args.query}'", border_style="green")
            table.add_column("ID", style="dim")
            table.add_column("Triggers")
            table.add_column("Confidence", justify="right")
            table.add_column("Score", justify="right", style="bold yellow")
            
            for edge, score in results:
                trigs = ", ".join(edge.triggers)
                conf_color = "green" if edge.confidence > 0.7 else "yellow" if edge.confidence > 0.4 else "red"
                table.add_row(
                    edge.id, 
                    trigs, 
                    f"[{conf_color}]{edge.confidence:.2f}[/{conf_color}]", 
                    str(score)
                )
            
            rprint(table)

        elif args.subcommand == "remove":
            if gateway.memory.remove_edge(args.id):
                rprint(f"✅ Removed edge: {args.id}")
            else:
                rprint(f"❌ Edge not found: {args.id}")

        elif args.subcommand == "prune":
            count = gateway.memory.prune_edges(min_confidence=0.3)
            rprint(f"🧹 Pruned {count} low-confidence edges from memory.")

        elif args.subcommand == "analyze":
            health = gateway.memory.analyze_health()
            rprint(Panel(
                f"Low Confidence: [bold yellow]{health['low_confidence_count']}[/bold yellow]\n"
                f"High Failure: [bold red]{health['high_failure_count']}[/bold red]\n"
                f"Orphan Nodes: [bold cyan]{health['orphan_nodes_count']}[/bold cyan]\n\n"
                "Suggestions:\n" + "\n".join([f" • {s}" for s in health['suggestions'] if s]),
                title="🩺 Memory Health Analysis",
                border_style="magenta"
            ))

        else:
            print(f"Memory subcommand '{args.subcommand}' not yet implemented.")

    elif args.command == "logs":
        if args.subcommand == "tail":
            log_file = _PROJECT_ROOT / "logs" / "jarvis.log"
            if not log_file.exists():
                print(f"❌ Log file not found: {log_file}")
                return
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines[-args.n:]:
                    print(line.strip())
        else:
            print(f"Logs subcommand '{args.subcommand}' not yet implemented.")

    elif args.command == "health":
        print("🏥 Jarvis Health Check:")
        print("  Checking subsystems...")
    
    else:
        print(f"Command '{args.command}' is registered but not yet implemented in this phase.")

if __name__ == "__main__":
    cli_main()
