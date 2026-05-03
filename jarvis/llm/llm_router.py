"""
LLM Router
==========
Implements the primary → fallback → emergency_fallback chain.
Reads backend config from config.yaml.

Decision algorithm:
    attempt_primary()  → healthy? → call it
                       → fail/timeout → attempt_fallback()
    attempt_fallback() → healthy? → call it
                       → fail → use mock
    mock              → always returns (cannot be disabled)

Health monitoring:
    Background thread checks all backends every 60s.
    On startup: checks immediately.
    Logs which backend is currently active so user knows.

Usage:
    router = LLMRouter.from_config("jarvis/config/config.yaml")
    plan = router.route("open display settings", memory_context="...")
"""

import logging
import os
import threading
import time
from pathlib import Path
from typing import Optional

import yaml

from jarvis.llm.llm_interface import LLMInterface, Plan, LLMDecision
from jarvis.llm.backends.mock_llm import MockLLM
from jarvis.llm.backends.local_llm import LocalLLM
from jarvis.llm.backends.openai_llm import OpenAILLM
from jarvis.llm.backends.tunneled_llm import TunneledLLM

logger = logging.getLogger(__name__)

_HEALTH_CHECK_INTERVAL = 60  # seconds


class LLMRouter:
    """
    Routes LLM calls through: primary → fallback → emergency mock.
    Never crashes — mock is always the safety net.
    """

    def __init__(
        self,
        primary: LLMInterface,
        fallback: Optional[LLMInterface] = None,
        emergency: Optional[LLMInterface] = None,
        health_check_interval: float = _HEALTH_CHECK_INTERVAL,
    ):
        self._primary = primary
        self._fallback = fallback
        self._emergency = emergency or MockLLM()
        self._health: dict[str, bool] = {}
        self._lock = threading.Lock()

        # Initial health check
        self._check_all_backends()

        # Background health monitor thread
        self._stop_event = threading.Event()
        self._monitor = threading.Thread(
            target=self._health_monitor_loop,
            args=(health_check_interval,),
            daemon=True,
            name="LLMHealthMonitor",
        )
        self._monitor.start()
        logger.info(f"[LLMRouter] Initialized. Primary: {primary.name} | "
                    f"Fallback: {fallback.name if fallback else 'none'} | "
                    f"Emergency: {self._emergency.name}")

    @classmethod
    def from_config(cls, config_path: Optional[str] = None) -> "LLMRouter":
        """Build LLMRouter from config.yaml. Resolves env vars automatically."""
        if config_path is None:
            config_path = str(Path(__file__).parent.parent / "config" / "config.yaml")

        with open(config_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        llm_cfg = cfg.get("llm", {})
        backends_cfg = llm_cfg.get("backends", {})

        primary_name = llm_cfg.get("primary", "mock")
        fallback_name = llm_cfg.get("fallback", "mock")

        def _resolve(s: str) -> str:
            """Expand ${ENV_VAR} tokens."""
            if isinstance(s, str) and s.startswith("${") and s.endswith("}"):
                return os.environ.get(s[2:-1], "")
            return s or ""

        def _build(name: str) -> Optional[LLMInterface]:
            bc = backends_cfg.get(name, {})
            if not bc:
                return None
            if name == "local":
                return LocalLLM(
                    api_url=bc.get("api_url", "http://localhost:11434/v1"),
                    model=bc.get("model", "qwen2.5:0.5b-instruct"),
                    fallback_model=bc.get("fallback_model", "qwen2.5:0.5b-instruct"),
                    max_tokens=bc.get("max_tokens", 300),
                    temperature=bc.get("temperature", 0.1),
                    timeout=bc.get("timeout_seconds", 15),
                    auto_pull=bc.get("auto_pull", True),
                )
            if name == "openai":
                return OpenAILLM(
                    provider=bc.get("provider", "openai"),
                    api_key=_resolve(bc.get("api_key", "")),
                    model=bc.get("model", "gpt-4o-mini"),
                    max_tokens=bc.get("max_tokens", 300),
                    temperature=bc.get("temperature", 0.1),
                    timeout=bc.get("timeout_seconds", 20),
                )
            if name == "tunneled":
                return TunneledLLM(
                    api_url=_resolve(bc.get("api_url", "")),
                    api_key=_resolve(bc.get("api_key", "")),
                    model=_resolve(bc.get("model", "")),
                    max_tokens=bc.get("max_tokens", 300),
                    temperature=bc.get("temperature", 0.1),
                    timeout=bc.get("timeout_seconds", 10),
                )
            if name == "mock":
                return MockLLM()
            return None

        primary = _build(primary_name) or MockLLM()
        fallback = _build(fallback_name) if fallback_name != primary_name else None
        emergency = MockLLM()

        return cls(primary=primary, fallback=fallback, emergency=emergency)

    def route(self, prompt: str, memory_context: str = "") -> Plan:
        """
        Route a prompt through the backend chain.
        Always returns a Plan (uses mock as last resort — never None).
        """
        backends = [b for b in [self._primary, self._fallback, self._emergency] if b]

        for backend in backends:
            if not self._is_healthy(backend):
                logger.info(f"[LLMRouter] Skipping unhealthy backend: {backend.name}")
                continue

            logger.info(f"[LLMRouter] Trying backend: {backend.name}")
            try:
                plan = backend.plan(prompt, memory_context)
                if plan:
                    logger.info(f"[LLMRouter] Plan from {backend.name}: {[s.skill for s in plan]}")
                    return plan
                else:
                    logger.warning(f"[LLMRouter] {backend.name} returned empty plan — trying next.")
            except Exception as e:
                logger.error(f"[LLMRouter] {backend.name} raised: {e} — trying next.")
                with self._lock:
                    self._health[backend.name] = False

        # Final fallback: mock always works
        logger.warning("[LLMRouter] All backends failed. Using mock emergency fallback.")
        return self._emergency.plan(prompt, memory_context) or []

    def decide(self, prompt: str, context: str = "") -> LLMDecision:
        """
        New unified LLM router path. Tries primary → fallback.
        Falls back to emergency mock chat if everything fails.
        """
        for backend in [self._primary, self._fallback]:
            if not backend:
                continue
            if not self._is_healthy(backend):
                logger.info(f"[LLMRouter] Skipping unhealthy backend: {backend.name}")
                continue

            logger.info(f"[LLMRouter] Trying decide() on backend: {backend.name}")
            try:
                decision = backend.decide(prompt, context)
                if decision:
                    logger.info(f"[LLMRouter] Decision from {backend.name}: {decision.type}")
                    return decision
                else:
                    logger.warning(f"[LLMRouter] {backend.name} returned empty decision — trying next.")
            except Exception as e:
                logger.error(f"[LLMRouter] {backend.name} raised: {e} — trying next.")
                with self._lock:
                    self._health[backend.name] = False

        # Final fallback
        logger.warning("[LLMRouter] All backends failed. Returning emergency offline chat.")
        return LLMDecision(type="chat", message="Sorry, my cognitive core is currently offline.")

    def stop(self):
        """Stop the health monitor thread."""
        self._stop_event.set()

    def status(self) -> dict:
        """Return current health status of all backends."""
        with self._lock:
            return dict(self._health)

    # ── Private ──────────────────────────────────

    def _is_healthy(self, backend: LLMInterface) -> bool:
        with self._lock:
            return self._health.get(backend.name, True)  # Assume healthy if not checked yet

    def _check_all_backends(self):
        backends = [b for b in [self._primary, self._fallback, self._emergency] if b]
        for backend in backends:
            try:
                ok = backend.health_check()
                with self._lock:
                    self._health[backend.name] = ok
                status = "✅ healthy" if ok else "❌ unavailable"
                logger.info(f"[LLMRouter] {backend.name}: {status}")
            except Exception as e:
                with self._lock:
                    self._health[backend.name] = False
                logger.warning(f"[LLMRouter] Health check error for {backend.name}: {e}")

    def _health_monitor_loop(self, interval: float):
        while not self._stop_event.wait(timeout=interval):
            logger.debug("[LLMRouter] Running periodic health check...")
            self._check_all_backends()
