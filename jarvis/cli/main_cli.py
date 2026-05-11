import argparse
import sys
import logging
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

# Add project root to path so we can import jarvis modules
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from jarvis.main import build_orchestrator

logger = logging.getLogger("jarvis.cli")

def cli_main():
    parser = argparse.ArgumentParser(
        description="Jarvis — Iron Man Architecture CLI",
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
    parser.add_argument("-V", "--version", action="store_true", help="Show Jarvis version info and exit")


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
    config_subs.add_parser("show", help="Show current configuration")

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
    analyze_parser = logs_subs.add_parser("analyze")
    analyze_parser.add_argument("--since", default="1h", help="Time window (e.g. 1h, 30m, 1d)")
    logs_subs.add_parser("export").add_argument("output", help="Output file path")
    logs_subs.add_parser("clear")
    logs_subs.add_parser("watch")

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

    # --- System ---
    subparsers.add_parser("status", help="Show system snapshot")
    subparsers.add_parser("monitor", help="Live system resource monitor")
    subparsers.add_parser("version", help="Show Jarvis version info")
    subparsers.add_parser("health", help="Check subsystem health")
    subparsers.add_parser("doctor", help="Diagnose and fix issues")

    # --- TUI ---
    subparsers.add_parser("tui", help="Launch interactive TUI")
    subparsers.add_parser("chat", help="Launch interactive TUI (alias)")


    args = parser.parse_args()

    def show_version_info():
        from jarvis import __version__
        import platform
        
        table = Table(show_header=False, border_style="bold magenta")
        table.add_row("Jarvis Version", f"[bold cyan]v{__version__}[/bold cyan]")
        table.add_row("Codename", "Iron Man Architecture")
        table.add_row("Python", sys.version.split()[0])
        table.add_row("OS Platform", platform.platform())
        table.add_row("Architecture", platform.machine())
        table.add_row("Project Root", str(_PROJECT_ROOT))
        
        rprint(Panel(table, title="🛰 Jarvis Core Information", subtitle="Google DeepMind Advanced Agentic Coding", border_style="bold magenta"))

    if args.version:
        show_version_info()
        return

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

    elif args.command == "config":
        from jarvis.config.config_manager import ConfigManager
        cm = ConfigManager(gateway._config_path)
        
        if args.subcommand == "get":
            val = cm.get(args.key)
            if val is not None:
                rprint(f"[bold cyan]{args.key}[/bold cyan] = {val}")
            else:
                rprint(f"❌ Key '[bold]{args.key}[/bold]' not found.")
                
        elif args.subcommand == "set":
            cm.set(args.key, args.value)
            rprint(f"✅ Set [bold cyan]{args.key}[/bold cyan] to [bold]{args.value}[/bold]")
            
        elif args.subcommand == "unset":
            if cm.unset(args.key):
                rprint(f"✅ Unset [bold cyan]{args.key}[/bold cyan]")
            else:
                rprint(f"❌ Key '[bold]{args.key}[/bold]' not found.")
                
        elif args.subcommand == "file":
            rprint(f"📁 Config File: [bold yellow]{cm.path}[/bold yellow]")
            
        elif args.subcommand == "validate":
            issues = cm.validate()
            if not issues:
                rprint("✅ Config is valid.")
            else:
                rprint("⚠️  [bold yellow]Config Issues found:[/bold yellow]")
                for issue in issues:
                    rprint(f"  • {issue}")
                    
        elif args.subcommand == "show":
            full_cfg = cm.show(mask_secrets=True)
            # Use yaml for pretty print
            import yaml
            rprint(Panel(
                yaml.dump(full_cfg, sort_keys=False),
                title=f"⚙️  Current Config: {cm.path.name}",
                border_style="cyan"
            ))
        else:
            print(f"Config subcommand '{args.subcommand}' not yet implemented.")

    elif args.command == "models":
        if not gateway.router:
            rprint("❌ Error: LLM Router not initialized.")
            return
            
        if args.subcommand == "list":
            table = Table(title="🤖 LLM Backends", border_style="magenta")
            table.add_column("Name", style="bold")
            table.add_column("Type")
            table.add_column("Status")
            
            health = gateway.router.status()
            
            # Primary
            p = gateway.router._primary
            table.add_row(p.name, "Primary", "[green]✅ healthy[/green]" if health.get(p.name) else "[red]❌ unavailable[/red]")
            
            # Fallback
            f = gateway.router._fallback
            if f:
                table.add_row(f.name, "Fallback", "[green]✅ healthy[/green]" if health.get(f.name) else "[red]❌ unavailable[/red]")
                
            # Emergency
            e = gateway.router._emergency
            table.add_row(e.name, "Emergency", "[green]✅ healthy[/green]" if health.get(e.name) else "[red]❌ unavailable[/red]")
            
            rprint(table)
            
        elif args.subcommand == "status":
            health = gateway.router.status()
            active = "Mock (Safety Net)"
            if health.get(gateway.router._primary.name):
                active = gateway.router._primary.name
            elif gateway.router._fallback and health.get(gateway.router._fallback.name):
                active = gateway.router._fallback.name
                
            rprint(f"📡 Active Model: [bold green]{active}[/bold green]")
            
        elif args.subcommand == "scan":
            rprint("[dim]Scanning all backends...[/dim]")
            gateway.router._check_all_backends()
            rprint("✅ Scan complete.")
            
        elif args.subcommand == "set":
            # Update config
            from jarvis.config.config_manager import ConfigManager
            cm = ConfigManager(gateway._config_path)
            cm.set("llm.primary", args.name)
            rprint(f"✅ Set primary model to [bold]{args.name}[/bold]. Restart gateway to apply.")
        else:
            print(f"Models subcommand '{args.subcommand}' not yet implemented.")

    elif args.command == "channels":
        if not gateway.channel_mgr:
            rprint("❌ Error: Channel Manager not initialized.")
            return
            
        if args.subcommand == "list":
            table = Table(title="📡 Communication Channels", border_style="green")
            table.add_column("Channel", style="bold")
            table.add_column("Status")
            
            for channel in gateway.channel_mgr.list_channels():
                status_color = "green" if channel["status"] == "running" else "yellow" if channel["status"] == "stopped" else "red"
                table.add_row(channel["name"], f"[{status_color}]{channel['status']}[/{status_color}]")
            
            rprint(table)
            
        elif args.subcommand == "status":
            chan_name = args.name
            # Find channel status
            status = next((c for c in gateway.channel_mgr.list_channels() if c["name"] == chan_name), None)
            if not status:
                rprint(f"❌ Channel '[bold]{chan_name}[/bold]' not found.")
                return
            
            rprint(Panel(
                f"Name: [bold]{chan_name}[/bold]\n"
                f"Status: {status['status']}\n"
                f"Threads: 1 (active)",
                title=f"Channel: {chan_name}",
                border_style="green"
            ))
        else:
            print(f"Channels subcommand '{args.subcommand}' not yet implemented.")

    elif args.command == "skills":
        if not gateway.bus:
            rprint("❌ Error: Skill Bus not initialized.")
            return
            
        if args.subcommand == "list":
            table = Table(title="🛠️  Jarvis Action Skills", border_style="yellow")
            table.add_column("Skill Name", style="bold cyan")
            table.add_column("Category")
            table.add_column("Triggers")
            
            for skill in gateway.bus.get_all_skills():
                trigs = ", ".join(skill.triggers[:3]) + ("..." if len(skill.triggers) > 3 else "")
                table.add_row(skill.name, skill.category, trigs)
            
            rprint(table)
            
        elif args.subcommand == "info":
            skill = gateway.bus.get_skill(args.name)
            if not skill:
                rprint(f"❌ Skill '[bold]{args.name}[/bold]' not found.")
                return
            
            rprint(Panel(
                f"Name: [bold cyan]{skill.name}[/bold cyan]\n"
                f"Category: {skill.category}\n"
                f"Cognitive: {'✅' if skill.is_cognitive else '❌'}\n"
                f"Triggers: {', '.join(skill.triggers)}\n"
                f"Settle Time: {skill.settle_ms}ms\n"
                f"Docstring: {skill.fn.__doc__.strip() if skill.fn.__doc__ else 'No description'}",
                title=f"Skill: {skill.name}",
                border_style="yellow"
            ))
        else:
            print(f"Skills subcommand '{args.subcommand}' not yet implemented.")

    elif args.command == "status":
        stat = gateway.status()
        table = Table(show_header=False, border_style="cyan")
        table.add_row("🛰 Gateway", "[green]✅ Running[/green]" if stat['running'] else "[red]❌ Offline[/red]")
        table.add_row("💬 Sessions", str(stat['sessions']))
        table.add_row("🧠 Memory", stat['memory'])
        
        active_channels = len([c for c in stat['channels'] if c['status'] == 'running'])
        table.add_row("📡 Channels", f"{active_channels} active")
        
        rprint(Panel(table, title="📊 Jarvis System Snapshot", border_style="cyan"))

    elif args.command == "monitor":
        import psutil
        import time
        from rich.live import Live
        
        def make_monitor_table():
            table = Table(title="🛰 Jarvis Live Monitor", border_style="spring_green3")
            table.add_column("Subsystem", style="bold")
            table.add_column("Status / Usage")
            
            # Resource usage
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent
            table.add_row("💻 CPU Usage", f"{cpu}%")
            table.add_row("📟 RAM Usage", f"{ram}%")
            
            # Gateway
            stat = gateway.status()
            table.add_row("🛰 Gateway Daemon", "[green]Online[/green]" if stat['running'] else "[red]Offline[/red]")
            table.add_row("👥 Active Sessions", str(stat['sessions']))
            
            # Channels
            for chan in stat['channels']:
                status = "[green]RUNNING[/green]" if chan['status'] == "running" else "[yellow]STOPPED[/yellow]"
                table.add_row(f"  └ {chan['name']}", status)
            
            return table

        rprint("[dim]Starting monitor (Ctrl+C to exit)...[/dim]")
        try:
            with Live(make_monitor_table(), refresh_per_second=2) as live:
                while True:
                    time.sleep(0.5)
                    live.update(make_monitor_table())
        except KeyboardInterrupt:
            rprint("\n[dim]Monitor stopped.[/dim]")

    elif args.command == "version":
        show_version_info()


    
    elif args.command == "memory":
        if not gateway.memory:
            rprint("❌ Error: Memory system not initialized. Check your configuration.")
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
        from jarvis.cli.commands.logs_cmd import LogAnalyzer
        
        analyzer = LogAnalyzer(_PROJECT_ROOT / "logs" / "jarvis.log")
        
        if args.subcommand == "tail":
            lines = analyzer.tail(n=args.n)
            for line in lines:
                rprint(line)
        
        elif args.subcommand == "analyze":
            stats = analyzer.analyze(since=args.since)
            if "error" in stats:
                rprint(f"❌ {stats['error']}")
                return
            
            table = Table(title="📊 Log Analysis", border_style="blue")
            table.add_column("Metric", style="bold")
            table.add_column("Value")
            
            table.add_row("Total Lines", str(stats["total_lines"]))
            table.add_row("LLM: Ollama Hits", str(stats["ollama_hits"]))
            table.add_row("LLM: Mock Hits", str(stats["mock_hits"]))
            
            # Subsystems
            sub_str = "\n".join([f"{k}: {v}" for k, v in stats["subsystems"].most_common(5)])
            table.add_row("Top Subsystems", sub_str)
            
            # Levels
            level_str = "\n".join([f"{k}: {v}" for k, v in stats["levels"].items()])
            table.add_row("Log Levels", level_str)
            
            rprint(Panel(table, border_style="blue"))
            
            if stats["errors"]:
                rprint(Panel("\n".join(stats["errors"][:10]), title="❌ Recent Errors", border_style="red"))

        elif args.subcommand == "export":
            import shutil
            try:
                shutil.copy(_PROJECT_ROOT / "logs" / "jarvis.log", args.output)
                rprint(f"✅ Logs exported to [bold]{args.output}[/bold]")
            except Exception as e:
                rprint(f"❌ Export failed: {e}")

        elif args.subcommand == "clear":
            if analyzer.clear():
                rprint("✅ Logs cleared.")
            else:
                rprint("❌ Failed to clear logs.")

        elif args.subcommand == "watch":
            rprint("[dim]Starting live log watch (Ctrl+C to exit)...[/dim]")
            import time
            log_file = _PROJECT_ROOT / "logs" / "jarvis.log"
            if not log_file.exists():
                rprint(f"❌ Log file not found: {log_file}")
                return
            
            with open(log_file, "r", encoding="utf-8") as f:
                f.seek(0, 2) # Go to end
                try:
                    while True:
                        line = f.readline()
                        if not line:
                            time.sleep(0.1)
                            continue
                        # Use rich for coloring
                        from rich.text import Text
                        text = Text(line.strip())
                        if "[ERROR]" in line: text.stylize("bold red")
                        elif "[WARNING]" in line: text.stylize("yellow")
                        rprint(text)
                except KeyboardInterrupt:
                    rprint("\n[dim]Watch stopped.[/dim]")
        else:
            print(f"Logs subcommand '{args.subcommand}' not yet implemented.")

    elif args.command == "doctor":
        from jarvis.cli.commands.doctor_cmd import run_doctor
        run_doctor(gateway)
    
    elif args.command == "cron":
        rprint("[yellow]Cron scheduler is coming in Phase 9.[/yellow]")
        
    elif args.command == "health":
        print("🏥 Jarvis Health Check:")
        print("  Checking subsystems...")
    
    else:
        print(f"Command '{args.command}' is registered but not yet implemented in this phase.")

if __name__ == "__main__":
    cli_main()
