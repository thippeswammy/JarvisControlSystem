"""
Tunneled LLM Backend
====================
Connects to a self-hosted model exposed via a tunnel (ngrok, cloudflared, bore.pub).
The tunnel endpoint must expose an OpenAI-compatible /v1/chat/completions API.

Setup:
    export JARVIS_TUNNEL_URL=https://abc123.ngrok.io/v1
    export JARVIS_TUNNEL_KEY=your-optional-key
    export JARVIS_TUNNEL_MODEL=qwen2.5:0.5b-instruct

This is functionally identical to LocalLLM but uses a remote URL.
"""

import json
import logging
import os
from typing import Optional

import requests

from jarvis.llm.llm_interface import LLMInterface, Plan, SkillCallSpec

logger = logging.getLogger(__name__)


class TunneledLLM(LLMInterface):
    """HTTP client for a self-hosted OpenAI-compatible model endpoint."""

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 300,
        temperature: float = 0.1,
        timeout: float = 10.0,
    ):
        self._api_url = (api_url or os.environ.get("JARVIS_TUNNEL_URL", "")).rstrip("/")
        self._api_key = api_key or os.environ.get("JARVIS_TUNNEL_KEY", "")
        self._model = model or os.environ.get("JARVIS_TUNNEL_MODEL", "qwen2.5:0.5b-instruct")
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._timeout = timeout

    @property
    def name(self) -> str:
        return f"tunneled/{self._model}"

    def health_check(self) -> bool:
        if not self._api_url:
            return False
        try:
            resp = requests.get(
                f"{self._api_url}/models",
                headers=self._headers(),
                timeout=3,
            )
            return resp.status_code == 200
        except Exception as e:
            logger.debug(f"[TunneledLLM] Health check failed: {e}")
            return False

    def plan(self, prompt: str, memory_context: str = "") -> Optional[Plan]:
        if not self._api_url:
            return None

        messages = [{"role": "system", "content": self.build_system_prompt()}]
        if memory_context.strip():
            messages.append({"role": "system", "content": f"Memory:\n{memory_context}"})
        messages.append({"role": "user", "content": prompt})

        try:
            resp = requests.post(
                f"{self._api_url}/chat/completions",
                headers=self._headers(),
                json={
                    "model": self._model,
                    "messages": messages,
                    "max_tokens": self._max_tokens,
                    "temperature": self._temperature,
                    "stream": False,
                },
                timeout=self._timeout,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()
            return self._parse_plan(content)
        except requests.exceptions.Timeout:
            logger.warning(f"[TunneledLLM] Timeout after {self._timeout}s")
            return None
        except Exception as e:
            logger.error(f"[TunneledLLM] Request failed: {e}")
            return None

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self._api_key:
            h["Authorization"] = f"Bearer {self._api_key}"
        return h

    def _parse_plan(self, raw: str) -> Optional[Plan]:
        raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        try:
            data = json.loads(raw)
            if not isinstance(data, list):
                data = [data]
            return [
                SkillCallSpec(skill=d["skill"], params=d.get("params", {}))
                for d in data if isinstance(d, dict) and "skill" in d
            ] or None
        except Exception as e:
            logger.warning(f"[TunneledLLM] Plan parse error: {e}")
            return None
