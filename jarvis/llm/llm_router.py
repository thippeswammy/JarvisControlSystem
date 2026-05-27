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
from jarvis.llm.backends.nvidia_llm import NvidiaLLM
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
        logger.debug(f"[LLMRouter] Initialized. Primary: {primary.name} | "
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
                    model=bc.get("model", "gemma3:4b"),
                    fallback_model=bc.get("fallback_model", "gemma3:4b"),
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
            if name == "nvidia":
                return NvidiaLLM(
                    model=bc.get("model", "qwen/qwen3-coder-480b-a35b-instruct"),
                    api_key=_resolve(bc.get("api_key", "")),
                    base_url=bc.get("base_url", "https://integrate.api.nvidia.com/v1"),
                    max_tokens=bc.get("max_tokens", 4096),
                    temperature=bc.get("temperature", 0.7),
                    top_p=bc.get("top_p", 0.8),
                    timeout=bc.get("timeout_seconds", 30),
                )
            if name == "mock":
                return MockLLM()
            return None

        primary = _build(primary_name) or MockLLM()
        fallback = _build(fallback_name) if fallback_name != primary_name else None
        emergency = _build("mock") or MockLLM()

        return cls(primary=primary, fallback=fallback, emergency=emergency)

    def _clean_and_parse_json(self, raw_text: str):
        import json
        import re
        # Strip markdown braces if present
        candidate = re.sub(r"```(?:json)?\s*", "", raw_text, flags=re.IGNORECASE).strip()
        candidate = candidate.replace("```", "").strip()
        
        # Try parsing directly first
        try:
            return json.loads(candidate)
        except Exception:
            pass
            
        # Find JSON structure (starts with { or [)
        obj_match = re.search(r"(\{.*\}|\[.*\])", candidate, re.DOTALL)
        if obj_match:
            json_str = obj_match.group(1)
            # Try parsing this structure
            try:
                return json.loads(json_str)
            except Exception:
                pass
                
            # If it failed, maybe there are extra closing braces at the end.
            if json_str.startswith("{") and json_str.endswith("}"):
                temp = json_str
                for _ in range(20):
                    if temp.endswith("}"):
                        temp = temp[:-1].rstrip()
                        try:
                            return json.loads(temp)
                        except Exception:
                            pass
                    else:
                        break
                        
            # Brace counting heuristic
            if json_str.startswith("{"):
                brace_count = 0
                in_string = False
                escape = False
                for idx, char in enumerate(json_str):
                    if escape:
                        escape = False
                        continue
                    if char == '\\':
                        escape = True
                        continue
                    if char == '"':
                        in_string = not in_string
                        continue
                    if not in_string:
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                candidate_substring = json_str[:idx+1]
                                try:
                                    return json.loads(candidate_substring)
                                except Exception:
                                    pass
        return candidate

    def _write_to_raw_log(self, mode: str, backend_name: str, raw_input: dict, raw_response: str):
        import json
        import os
        from datetime import datetime
        log_path = Path(__file__).parent.parent.parent / "logs" / "llm_raw.log"
        log_path.parent.mkdir(exist_ok=True)
        
        # Clean and parse for the user-friendly output_response
        output_response = self._clean_and_parse_json(raw_response)

        timestamp = datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "mode": mode,
            "backend": backend_name,
            "raw_input_payload": raw_input,
            "raw_output_response": raw_response,
            "output_response": output_response
        }
        
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, indent=2, ensure_ascii=False) + "\n\n" + "="*80 + "\n\n")
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                pass

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
            
            # Reconstruct raw system prompt payload
            system_instructions = backend.build_system_prompt()
            raw_input = {
                "messages": [
                    {"role": "system", "content": system_instructions},
                    {"role": "system", "content": f"Relevant memory from past sessions:\n{memory_context}"} if memory_context.strip() else None,
                    {"role": "user", "content": prompt}
                ]
            }
            raw_input["messages"] = [m for m in raw_input["messages"] if m is not None]

            # Clear last raw response before calling
            if hasattr(backend, "last_raw_response"):
                backend.last_raw_response = ""

            try:
                plan = backend.plan(prompt, memory_context)
            except Exception as e:
                logger.error(f"[LLMRouter] {backend.name} raised: {e} — trying next.")
                with self._lock:
                    self._health[backend.name] = False
                continue

            raw_response_text = getattr(backend, "last_raw_response", "") or "No raw response captured"
            self._write_to_raw_log("PLAN", backend.name, raw_input, raw_response_text)

            if plan:
                logger.info(f"[LLMRouter] Plan from {backend.name}: {[s.skill for s in plan]}")
                return plan
            else:
                logger.warning(f"[LLMRouter] {backend.name} returned empty plan — trying next.")

        # Final fallback: mock always works
        logger.warning("[LLMRouter] All backends failed. Using mock emergency fallback.")
        return self._emergency.plan(prompt, memory_context) or []

    def decide(self, prompt: str, context: str = "") -> LLMDecision:
        """
        New unified LLM router path. Tries primary → fallback → emergency mock.
        Never crashes — mock is the safety net.
        """
        for backend in [self._primary, self._fallback, self._emergency]:
            if not backend:
                continue
            if not self._is_healthy(backend):
                logger.info(f"[LLMRouter] Skipping unhealthy backend: {backend.name}")
                continue

            logger.info(f"[Cognitive] Requesting decision from {backend.name}...")

            # Reconstruct raw system prompt payload
            sys_prompt = (
                "You are JARVIS, an advanced AI desktop assistant.\n"
                "You must ALWAYS return a SINGLE valid JSON object and absolutely nothing else. No markdown, no explanations.\n"
                "If you just want to talk (greetings, quick help), return a 'chat' type JSON.\n"
                "Your JSON object must exactly match one of these 4 formats:\n"
                "1. Chat only: {\"type\": \"chat\", \"message\": \"your reply here\"}\n"
                "2. Plan only: {\"type\": \"plan\", \"steps\": [{\"skill\": \"skill_name\", \"params\": {}}]}\n"
                "3. Mixed (talk AND act): {\"type\": \"mixed\", \"message\": \"your reply\", \"steps\": [{\"skill\": \"skill_name\", \"params\": {}}]}\n"
                "4. Clarify (ask user): {\"type\": \"clarify\", \"question\": \"your question\"}"
            )
            raw_input = {
                "messages": [
                    {"role": "system", "content": sys_prompt},
                    {"role": "system", "content": context},
                    {"role": "user", "content": prompt}
                ]
            }

            # Clear last raw response before calling
            if hasattr(backend, "last_raw_response"):
                backend.last_raw_response = ""

            try:
                decision = backend.decide(prompt, context)
            except Exception as e:
                logger.error(f"[LLMRouter] {backend.name} raised: {e} — trying next.")
                with self._lock:
                    self._health[backend.name] = False
                continue

            raw_response_text = getattr(backend, "last_raw_response", "") or "No raw response captured"
            self._write_to_raw_log("DECIDE", backend.name, raw_input, raw_response_text)

            if decision:
                logger.info(f"[Decision] Mode identified: {decision.type.upper()}")
                return decision
            else:
                logger.warning(f"[LLMRouter] {backend.name} returned empty decision — trying next.")

        # Final fallback (should never be reached as emergency is always healthy)
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
                status = "healthy" if ok else "unavailable"
                logger.debug(f"[LLMRouter] {backend.name}: {status}")

            except Exception as e:
                with self._lock:
                    self._health[backend.name] = False
                logger.warning(f"[LLMRouter] Health check error for {backend.name}: {e}")

    def _health_monitor_loop(self, interval: float):
        while not self._stop_event.wait(timeout=interval):
            logger.debug("[LLMRouter] Running periodic health check...")
            self._check_all_backends()
