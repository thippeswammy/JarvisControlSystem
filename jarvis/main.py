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


def build_orchestrator(config_path: str = "", use_ollama: bool = False):
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

    # ── Ensure Ollama is running ──────────────────────────────
    if use_ollama:
        from jarvis.utils.ollama_utils import enable_auto_start, ensure_ollama_running
        enable_auto_start(True)
        ensure_ollama_running()

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
    from jarvis.cli.main_cli import cli_main
    cli_main()


if __name__ == "__main__":
    main()
