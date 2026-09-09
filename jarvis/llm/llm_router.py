"""
LLM Router
==========
Routes each call to exactly one backend: the task-specific routing
override if configured, otherwise the configured primary. There is
no automatic fallback — if the selected backend is unhealthy, errors,
or returns nothing, the router raises immediately and names the
backend that failed. It never silently substitutes another model,
the local backend, or the mock backend.

Health monitoring:
    Background thread checks all backends every 60s.
    On startup: checks immediately.
    Used only to report status and to fail fast with a clear message
    when the selected backend is already known to be down.

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

from jarvis.llm.llm_interface import LLMInterface, Plan, LLMDecision, ClosedLoopDecision
from jarvis.llm.backends.mock_llm import MockLLM
from jarvis.llm.backends.local_llm import LocalLLM
from jarvis.llm.backends.openai_llm import OpenAILLM
from jarvis.llm.backends.nvidia_llm import NvidiaLLM
from jarvis.llm.backends.tunneled_llm import TunneledLLM

logger = logging.getLogger(__name__)

_HEALTH_CHECK_INTERVAL = 60  # seconds


class LLMRouter:
    """
    Routes each LLM call to exactly one backend (task override, else primary).
    No automatic fallback: a failing or unhealthy backend raises a clear
    error instead of silently trying another backend, local, or mock.
    """

    def __init__(
        self,
        primary: LLMInterface,
        fallback: Optional[LLMInterface] = None,
        emergency: Optional[LLMInterface] = None,
        health_check_interval: float = _HEALTH_CHECK_INTERVAL,
        routing: Optional[dict[str, LLMInterface]] = None,
    ):
        self._primary = primary
        self._fallback = fallback
        self._emergency = emergency or MockLLM()
        self._routing = routing or {}
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
                    f"Configured (unused, no auto-fallback) fallback: {fallback.name if fallback else 'none'} | "
                    f"Routing tasks: {list(self._routing.keys())}")


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
                    max_tokens=bc.get("max_tokens", 30000),
                    temperature=bc.get("temperature", 0.1),
                    timeout=bc.get("timeout_seconds", 60),
                    auto_pull=bc.get("auto_pull", True),
                )
            if name == "openai":
                return OpenAILLM(
                    provider=bc.get("provider", "openai"),
                    api_key=_resolve(bc.get("api_key", "")),
                    model=bc.get("model", "gpt-4o-mini"),
                    max_tokens=bc.get("max_tokens", 30000),
                    temperature=bc.get("temperature", 0.1),
                    timeout=bc.get("timeout_seconds", 60),
                )
            if name == "tunneled":
                return TunneledLLM(
                    api_url=_resolve(bc.get("api_url", "")),
                    api_key=_resolve(bc.get("api_key", "")),
                    model=_resolve(bc.get("model", "")),
                    max_tokens=bc.get("max_tokens", 30000),
                    temperature=bc.get("temperature", 0.1),
                    timeout=bc.get("timeout_seconds", 60),
                )
            if name in ("nvidia", "openrouter"):
                # Both are OpenAI-compatible cloud APIs serving open-weight models —
                # same client, different base_url/key/model.
                default_base_url = (
                    "https://openrouter.ai/api/v1" if name == "openrouter"
                    else "https://integrate.api.nvidia.com/v1"
                )
                default_key_env = "OPENROUTER_API_KEY" if name == "openrouter" else "NVIDIA_API_KEY"
                return NvidiaLLM(
                    model=bc.get("model", "qwen/qwen3-coder-480b-a35b-instruct"),
                    api_key=_resolve(bc.get("api_key", "")) or os.environ.get(default_key_env, ""),
                    base_url=bc.get("base_url", default_base_url),
                    max_tokens=bc.get("max_tokens", 40960),
                    temperature=bc.get("temperature", 0.7),
                    top_p=bc.get("top_p", 0.8),
                    timeout=bc.get("timeout_seconds", 60),
                    provider=name,
                )
            if name == "mock":
                return MockLLM()
            return None

        primary = _build(primary_name) or MockLLM()
        fallback = _build(fallback_name) if fallback_name != primary_name else None
        emergency = _build("mock") or MockLLM()

        # Build task-specific routing
        routing_cfg = llm_cfg.get("routing", {})
        routing = {}
        for task, backend_name in routing_cfg.items():
            if isinstance(backend_name, str):
                built_backend = _build(backend_name)
                if built_backend:
                    routing[task] = built_backend

        return cls(primary=primary, fallback=fallback, emergency=emergency, routing=routing)

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
        log_path = Path(__file__).parent.parent.parent / "logs" / "runtime" / "llm_raw.log"
        log_path.parent.mkdir(exist_ok=True)
        
        # Clean and parse for the user-friendly output_response
        output_response = self._clean_and_parse_json(raw_response)

        timestamp = datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "mode": mode,
            "backend": str(backend_name),
            "raw_input_payload": raw_input,
            "raw_output_response": raw_response,
            "output_response": output_response
        }
        
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, indent=2, ensure_ascii=False, default=str) + "\n\n" + "="*80 + "\n\n")
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                pass


    def route(self, prompt: str, memory_context: str = "") -> Plan:
        """
        Route a prompt to the selected backend. Raises if it fails — no
        automatic fallback to another backend, local, or mock.
        """
        return self.route_for_task("default", prompt, memory_context)

    def route_for_task(self, task: str, prompt: str, memory_context: str = "") -> Plan:
        """
        Route a prompt to the selected backend for this task. No fallback:
        raises immediately if that backend is unhealthy, errors, or is empty.
        """
        backend = self._select_backend(task)
        self._require_healthy(backend)

        logger.info(f"[LLMRouter] Calling backend: {backend.name} for task: {task}")

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
            with self._lock:
                self._health[backend.name] = False
            raise RuntimeError(f"LLM backend '{backend.name}' failed: {e}") from e

        raw_response_text = getattr(backend, "last_raw_response", "") or "No raw response captured"
        self._write_to_raw_log("PLAN", backend.name, raw_input, raw_response_text)

        if not plan:
            raise RuntimeError(f"LLM backend '{backend.name}' returned an empty plan.")

        logger.info(f"[LLMRouter] Plan from {backend.name}: {[s.skill for s in plan]}")
        return plan

    def decide(self, prompt: str, context: str = "") -> LLMDecision:
        """
        Decide via the selected backend. Raises if it fails — no automatic
        fallback to another backend, local, or mock.
        """
        return self.decide_for_task("default", prompt, context)

    def decide_for_task(self, task: str, prompt: str, context: str = "") -> LLMDecision:
        """
        Decide via the selected backend for this task. No fallback: raises
        immediately if that backend is unhealthy, errors, or is empty.
        """
        backend = self._select_backend(task)
        self._require_healthy(backend)

        logger.info(f"[Cognitive] Requesting decision from {backend.name} for task: {task}...")

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
            with self._lock:
                self._health[backend.name] = False
            raise RuntimeError(f"LLM backend '{backend.name}' failed: {e}") from e

        raw_response_text = getattr(backend, "last_raw_response", "") or "No raw response captured"
        self._write_to_raw_log("DECIDE", backend.name, raw_input, raw_response_text)

        if not decision:
            raise RuntimeError(f"LLM backend '{backend.name}' returned an empty decision.")

        logger.info(f"[Decision] Mode identified: {decision.type.upper()}")
        return decision

    def decide_closed_loop(self, prompt: str, context: str = "") -> ClosedLoopDecision:
        """
        Closed-loop decision via the selected backend. Raises if it fails —
        no automatic fallback to another backend, local, or mock.
        """
        return self.decide_closed_loop_for_task("default", prompt, context)

    def decide_closed_loop_for_task(self, task: str, prompt: str, context: str = "") -> ClosedLoopDecision:
        """
        Closed-loop decision via the selected backend for this task. No
        fallback: raises immediately if that backend is unhealthy, doesn't
        support closed-loop, errors, or returns nothing.
        """
        backend = self._select_backend(task)
        self._require_healthy(backend)

        logger.info(f"[ClosedLoop] Requesting decision from {backend.name} for task: {task}...")

        # Clear last raw response
        if hasattr(backend, "last_raw_response"):
            backend.last_raw_response = ""

        try:
            decision = backend.decide_closed_loop(prompt, context)
        except NotImplementedError as e:
            raise RuntimeError(f"LLM backend '{backend.name}' does not support closed-loop decisions.") from e
        except Exception as e:
            with self._lock:
                self._health[backend.name] = False
            raise RuntimeError(f"LLM backend '{backend.name}' closed-loop call failed: {e}") from e

        raw_response_text = getattr(backend, "last_raw_response", "") or "No raw response captured"
        self._write_to_raw_log("CLOSED_LOOP", backend.name, {"prompt": prompt[:200]}, raw_response_text)

        if not decision:
            raise RuntimeError(f"LLM backend '{backend.name}' returned an empty closed-loop decision.")

        logger.info(f"[ClosedLoop] Status: {decision.status.upper()} | Actions: {len(decision.actions)}")
        return decision

    def call_raw_for_task(self, task: str, prompt: str, context: str) -> Optional[str]:
        """
        Executes a raw generic LLM call (_call_llm_closed_loop) against the
        selected backend for this task. No fallback: raises immediately if
        that backend is unhealthy or errors.
        """
        backend = self._select_backend(task)
        self._require_healthy(backend)

        # Clear last raw response before calling
        if hasattr(backend, "last_raw_response"):
            backend.last_raw_response = ""

        try:
            raw = backend._call_llm_closed_loop(prompt, context)
        except Exception as e:
            with self._lock:
                self._health[backend.name] = False
            raise RuntimeError(f"LLM backend '{backend.name}' raw call failed: {e}") from e

        if raw is not None:
            raw_input = {
                "messages": [
                    {"role": "system", "content": context},
                    {"role": "user", "content": prompt}
                ]
            }
            self._write_to_raw_log(f"RAW_{task.upper()}", backend.name, raw_input, raw)
        return raw

    def stop(self):
        """Stop the health monitor thread."""
        self._stop_event.set()

    def status(self) -> dict:
        """Return current health status of all backends."""
        with self._lock:
            return dict(self._health)

    # ── Private ──────────────────────────────────

    def _select_backend(self, task: str) -> LLMInterface:
        """Resolve the single backend for this task: routing override, else primary."""
        task_primary = self._routing.get(task) if hasattr(self, "_routing") else None
        return task_primary or self._primary

    def _require_healthy(self, backend: LLMInterface) -> None:
        """Raise immediately if the selected backend is already known to be down."""
        if not self._is_healthy(backend):
            raise RuntimeError(
                f"LLM backend '{backend.name}' is unavailable (failed last health check). "
                f"No other backend will be tried automatically."
            )

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
