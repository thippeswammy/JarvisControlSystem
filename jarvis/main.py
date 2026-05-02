"""
Jarvis v2 — Main Entry Point
=============================
Wires all components and starts the input loop.

Usage:
    python -m jarvis.main            # CLI text mode
    python -m jarvis.main --voice    # Voice mode (requires faster-whisper)
    python -m jarvis.main --help
"""

import argparse
import logging
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent

# ── Ensure logs dir exists ────────────────────────────────
(_PROJECT_ROOT / "logs").mkdir(exist_ok=True)

# ── Ensure UTF-8 console output (Windows fix) ─────────────
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# ── Logging setup ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(_PROJECT_ROOT / "logs" / "jarvis.log"), encoding="utf-8"),
    ],
)
logger = logging.getLogger("jarvis.main")


def build_orchestrator(config_path: str = ""):
    """
    Wire all components and return a ready Orchestrator.
    Imports deferred to keep startup fast when only testing.
    """
    import yaml

    config_file = config_path or str(
        _PROJECT_ROOT / "jarvis" / "config" / "config.yaml"
    )
    with open(config_file, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # ── Memory ────────────────────────────────────────────────
    from jarvis.memory.memory_manager import MemoryManager
    db_path = cfg.get("memory", {}).get("graph_db", {}).get(
        "path", str(_PROJECT_ROOT / "memory" / "jarvis.db")
    )
    memory = MemoryManager(db_path=str(_PROJECT_ROOT / db_path))

    # ── LLM Router ────────────────────────────────────────────
    from jarvis.llm.llm_router import LLMRouter
    router = LLMRouter.from_config(config_path=config_file)

    # ── Skill Bus ─────────────────────────────────────────────
    from jarvis.skills.skill_bus import SkillBus
    bus = SkillBus()

    # ── Orchestrator ──────────────────────────────────────────
    from jarvis.brain.orchestrator import Orchestrator
    orch = Orchestrator(memory=memory, router=router, bus=bus)

    # ── Verification Loop ─────────────────────────────────────
    from jarvis.memory.state_harvester import StateHarvester
    from jarvis.memory.state_comparator import StateComparator
    from jarvis.brain.recovery import RecoveryStrategies
    from jarvis.brain.verification_loop import VerificationLoop

    harvester = StateHarvester()
    comparator = StateComparator()
    recovery = RecoveryStrategies(bus)
    vloop = VerificationLoop(harvester, comparator, recovery)
    orch.set_verification_loop(vloop)

    # ── Boot ──────────────────────────────────────────────────
    orch.boot()

    # ── Seed settings graph (idempotent) ─────────────────────
    from jarvis.memory.layers.procedural import ProceduralMemory
    proc = ProceduralMemory(memory.get_db())
    seeded = proc.seed_settings_graph()
    if seeded:
        logger.info(f"[main] Seeded {seeded} settings nodes")

    return orch


def main():
    parser = argparse.ArgumentParser(description="Jarvis v2 Control System")
    parser.add_argument("--voice",    action="store_true", help="Enable voice input")
    parser.add_argument("--telegram", action="store_true", help="Enable Telegram bot input")
    parser.add_argument("--config",   default="",          help="Path to config.yaml")
    parser.add_argument("--command", default="",          help="Run a single command and exit")
    parser.add_argument("--debug",   action="store_true", help="Enable DEBUG logging")
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)


    logger.info("=" * 55)
    logger.info("  JARVIS v2.1 — Iron Man Architecture  ")
    logger.info("=" * 55)

    orch = build_orchestrator(config_path=args.config)

    # ── Single command mode ───────────────────────────────────
    if args.command:
        result = orch.process(args.command)
        status = "✅" if result.success else "❌"
        print(f"{status} {result.message or result.action_taken}")
        return

    # ── Voice mode ────────────────────────────────────────────
    if args.voice:
        from jarvis.input.adapters import VoiceAdapter
        adapter = VoiceAdapter()
        if not adapter.is_available():
            print("❌ faster-whisper not installed. Run: pip install faster-whisper")
            sys.exit(1)
        print("🎙 Voice mode active. Say 'Jarvis <command>' or Ctrl+C to quit.")
        for utterance in adapter.stream():
            result = orch.process(
                utterance.text,
                source="voice",
                confidence=utterance.confidence,
            )
            print(f"  Jarvis: {result.message or result.action_taken}")
        return

    # ── Telegram mode ─────────────────────────────────────────
    if args.telegram:
        import yaml
        config_file = args.config or str(_PROJECT_ROOT / "jarvis" / "config" / "config.yaml")
        with open(config_file, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        
        tel_cfg = cfg.get("telegram", {})
        if not tel_cfg.get("enabled"):
            print("❌ Telegram input is disabled in config.yaml. Set telegram.enabled: true")
            sys.exit(1)

        from jarvis.input.adapters import TelegramAdapter
        
        # Resolve token (expand ${ENV_VAR})
        token = tel_cfg.get("token", "")
        if token.startswith("${") and token.endswith("}"):
            import os
            token = os.environ.get(token[2:-1], "")
            
        adapter = TelegramAdapter(
            token=token,
            allowed_chat_ids=tel_cfg.get("allowed_chat_ids", [])
        )
        
        if not adapter.is_available():
            print("❌ Telegram token missing or invalid. Check config.yaml or set TELEGRAM_TOKEN env var.")
            sys.exit(1)
            
        print(f"🤖 Telegram bot active. Send messages to your bot or Ctrl+C to quit.")
        for utterance in adapter.stream():
            result = orch.process(utterance.text, source="telegram")
            status = "✅" if result.success else "❌"
            print(f"  Jarvis (@{utterance.source}): {status} {result.message or result.action_taken}")
        return

    # ── Text / CLI mode ───────────────────────────────────────
    from jarvis.input.adapters import TextAdapter
    adapter = TextAdapter(prompt="Jarvis> ")
    print("💬 Text mode. Type a command or 'exit' to quit.")
    for utterance in adapter.stream():
        result = orch.process(utterance.text, source="text")
        status = "✅" if result.success else "❌"
        print(f"  Jarvis: {status} {result.message or result.action_taken}")


if __name__ == "__main__":
    main()
