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
  jarvis memory search "open notepad"
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

    # Basic command routing (to be expanded in further phases)
    if args.command in ["tui", "chat"]:
        print("🚀 Launching Jarvis TUI... (Not yet implemented)")
        # In later phases, this will call jarvis.tui.tui_app.main()
    elif args.command == "status":
        print("📊 Jarvis System Status:")
        print("  - Gateway: Offline")
        print("  - Channels: None")
        print("  - Models: Unknown")
    elif args.command == "health":
        print("🏥 Jarvis Health Check:")
        print("  Checking subsystems...")
    else:
        print(f"Command '{args.command}' is registered but not yet implemented in this phase.")

if __name__ == "__main__":
    cli_main()
