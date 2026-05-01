"""
OpenAI Cloud LLM Backend
=========================
Supports: OpenAI (GPT-4o-mini), Anthropic (Claude), Azure OpenAI.
Requires: pip install openai
API key via environment variable — never hardcoded.
"""

import json
import logging
import os
from typing import Optional

from jarvis_v2.llm.llm_interface import LLMInterface, Plan, SkillCallSpec

logger = logging.getLogger(__name__)


class OpenAILLM(LLMInterface):
    """
    Cloud LLM backend using the openai SDK.
    Works for OpenAI, Anthropic (via openai-compat), and Azure.
    """

    def __init__(
        self,
        provider: str = "openai",
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        max_tokens: int = 300,
        temperature: float = 0.1,
        timeout: float = 20.0,
    ):
        self._provider = provider
        self._model = model
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._timeout = timeout
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._client = None

    @property
    def name(self) -> str:
        return f"openai/{self._model}"

    def health_check(self) -> bool:
        if not self._api_key:
            logger.debug("[OpenAILLM] No API key configured.")
            return False
        try:
            client = self._get_client()
            # Lightweight check: list available models
            client.models.list()
            return True
        except Exception as e:
            logger.debug(f"[OpenAILLM] Health check failed: {e}")
            return False

    def plan(self, prompt: str, memory_context: str = "") -> Optional[Plan]:
        try:
            client = self._get_client()
            messages = [
                {"role": "system", "content": self.build_system_prompt()},
            ]
            if memory_context.strip():
                messages.append({
                    "role": "system",
                    "content": f"Memory context:\n{memory_context}"
                })
            messages.append({"role": "user", "content": prompt})

            response = client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
                timeout=self._timeout,
            )
            content = response.choices[0].message.content.strip()
            return self._parse_plan(content)
        except Exception as e:
            logger.error(f"[OpenAILLM] Request failed: {e}")
            return None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self._api_key)
            except ImportError:
                raise RuntimeError("openai package not installed. Run: pip install openai")
        return self._client

    def _parse_plan(self, raw: str) -> Optional[Plan]:
        raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        try:
            data = json.loads(raw)
            if not isinstance(data, list):
                data = [data]
            return [
                SkillCallSpec(skill=item["skill"], params=item.get("params", {}))
                for item in data if isinstance(item, dict) and "skill" in item
            ] or None
        except Exception as e:
            logger.warning(f"[OpenAILLM] Plan parse error: {e}")
            return None
