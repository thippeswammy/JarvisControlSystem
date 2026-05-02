"""
Local LLM Backend — Ollama
===========================
Uses Ollama's OpenAI-compatible REST API to run qwen2.5:1.5b-instruct
locally. Ollama handles CUDA, cuBLAS, cuDNN — no manual setup needed.

Setup:
    1. Install Ollama: https://ollama.com/download
    2. ollama pull qwen2.5:1.5b-instruct
    3. ollama serve   (starts on localhost:11434 automatically on Windows)

Why qwen2.5:1.5b-instruct:
    - 1.5B parameters → ~900MB VRAM (well within 4GB limit)
    - Instruction-tuned: follows JSON output format reliably
    - 32k context window: fits full RAG memory injection
    - Fallback: qwen2.5:0.5b-instruct (0.5B, ~400MB VRAM)
"""

import json
import logging
import subprocess
import time
from typing import Optional

import requests

from jarvis.llm.llm_interface import LLMInterface, Plan, SkillCallSpec

logger = logging.getLogger(__name__)


class LocalLLM(LLMInterface):
    """
    Ollama HTTP client. Connects to the locally running Ollama server.

    Integration:
        LocalLLM → HTTP POST → Ollama /v1/chat/completions
                             → GPU inference (qwen2.5:1.5b-instruct, Q4_K_M)
                             → JSON Plan response
    """

    def __init__(
        self,
        api_url: str = "http://localhost:11434/v1",
        model: str = "qwen2.5:1.5b-instruct",
        fallback_model: str = "qwen2.5:0.5b-instruct",
        max_tokens: int = 300,
        temperature: float = 0.1,
        timeout: float = 15.0,
        auto_pull: bool = True,
    ):
        self._api_url = api_url.rstrip("/")
        self._model = model
        self._fallback_model = fallback_model
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._timeout = timeout
        self._auto_pull = auto_pull
        self._active_model: Optional[str] = None  # resolved on first health check

    @property
    def name(self) -> str:
        return f"local/ollama({self._active_model or self._model})"

    def health_check(self) -> bool:
        """
        Ping Ollama tags endpoint. Verify at least one of our models is present.
        If auto_pull=True and model is missing, trigger pull (non-blocking).
        """
        try:
            resp = requests.get(
                f"{self._api_url.replace('/v1', '')}/api/tags",
                timeout=3,
            )
            if resp.status_code != 200:
                return False

            tags = resp.json()
            loaded_models = {m["name"].split(":")[0] for m in tags.get("models", [])}
            loaded_full = {m["name"] for m in tags.get("models", [])}

            # Check primary model
            primary_base = self._model.split(":")[0]
            if self._model in loaded_full or primary_base in loaded_models:
                self._active_model = self._model
                return True

            # Check fallback model
            fallback_base = self._fallback_model.split(":")[0]
            if self._fallback_model in loaded_full or fallback_base in loaded_models:
                self._active_model = self._fallback_model
                logger.info(f"[LocalLLM] Using fallback model: {self._fallback_model}")
                return True

            # Neither present — auto-pull if enabled
            if self._auto_pull:
                self._pull_model_async(self._model)
            return False

        except requests.exceptions.ConnectionError:
            logger.debug("[LocalLLM] Ollama not running or unreachable.")
            return False
        except Exception as e:
            logger.debug(f"[LocalLLM] Health check error: {e}")
            return False

    def plan(self, prompt: str, memory_context: str = "") -> Optional[Plan]:
        """
        Send prompt to Ollama. Parse JSON Plan from response.

        Technique: Chain-of-thought suppressed via temperature=0.1 + JSON-only
        system instruction. Model outputs structured plan directly.
        """
        model = self._active_model or self._model

        messages = [
            {"role": "system", "content": self.build_system_prompt()},
        ]

        if memory_context and memory_context.strip():
            messages.append({
                "role": "system",
                "content": f"Relevant memory from past sessions:\n{memory_context}"
            })

        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
            "stream": False,
        }
        # Debug: Print lengths
        logger.info(f"[LocalLLM] System prompt len: {len(messages[0]['content'])}")
        logger.info(f"[LocalLLM] Sending prompt: {messages[-1]['content'][:100]}...")
        logger.debug(f"[LocalLLM] Full messages: {messages}")

        try:
            resp = requests.post(
                f"{self._api_url}/chat/completions",
                json=payload,
                timeout=self._timeout,
            )
            logger.info(f"[LocalLLM] Response status: {resp.status_code}")
            resp.raise_for_status()
            data = resp.json()
            logger.info(f"[LocalLLM] Raw Response: {data}")
            content = data["choices"][0]["message"]["content"].strip()
            return self._parse_plan(content)

        except requests.exceptions.Timeout:
            logger.warning(f"[LocalLLM] Request timed out after {self._timeout}s")
            return None
        except Exception as e:
            logger.error(f"[LocalLLM] Request failed: {e}")
            return None

    # ── Private ──────────────────────────────────

    def _parse_plan(self, raw: str) -> Optional[Plan]:
        """Extract JSON array from LLM response and convert to Plan."""
        # Strip markdown code fences if present
        raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()

        try:
            data = json.loads(raw)
            if not isinstance(data, list):
                data = [data]
            plan = []
            for item in data:
                if isinstance(item, dict) and "skill" in item:
                    plan.append(SkillCallSpec(
                        skill=item["skill"],
                        params=item.get("params", {}),
                    ))
            return plan if plan else None
        except json.JSONDecodeError as e:
            logger.warning(f"[LocalLLM] Failed to parse plan JSON: {e}\nRaw: {raw[:200]}")
            return None

    def _pull_model_async(self, model: str) -> None:
        """Non-blocking model pull via subprocess."""
        def _pull():
            logger.info(f"[LocalLLM] Pulling model: {model} (background)...")
            try:
                subprocess.run(["ollama", "pull", model], timeout=300, check=True)
                logger.info(f"[LocalLLM] Model {model} ready.")
            except Exception as e:
                logger.error(f"[LocalLLM] Pull failed for {model}: {e}")

        import threading
        threading.Thread(target=_pull, daemon=True).start()
