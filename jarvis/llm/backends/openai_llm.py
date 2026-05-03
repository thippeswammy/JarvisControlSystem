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

from jarvis.llm.llm_interface import LLMInterface, Plan, SkillCallSpec, LLMDecision

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

    def decide(self, prompt: str, context: str = "") -> Optional[LLMDecision]:
        try:
            client = self._get_client()
            
            sys_prompt = (
                "You are JARVIS, an advanced AI desktop assistant.\n"
                "You must ALWAYS return a SINGLE valid JSON object and absolutely nothing else. No markdown, no explanations.\n"
                "Your JSON object must exactly match one of these 4 formats:\n"
                '1. Chat only (for greetings, general talk): {"type": "chat", "message": "your reply here"}\n'
                '2. Plan only (for pure actions): {"type": "plan", "steps": [{"skill": "skill_name", "params": {}}]}\n'
                '3. Mixed (talk AND act): {"type": "mixed", "message": "your reply", "steps": [{"skill": "skill_name", "params": {}}]}\n'
                '4. Clarify (ask user for missing info): {"type": "clarify", "question": "your question"}\n'
                "\n"
                "CRITICAL RULES:\n"
                "- Only use skills listed in the [Available Skills] section of the context.\n"
                "- Output valid JSON only.\n"
            )
            
            messages = [
                {"role": "system", "content": sys_prompt},
                {"role": "system", "content": context},
                {"role": "user", "content": prompt}
            ]

            response = client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=self._max_tokens + 200,
                temperature=0.4,
                timeout=self._timeout,
            )
            content = response.choices[0].message.content.strip()
            return self._parse_decision(content)
        except Exception as e:
            logger.error(f"[OpenAILLM] Decide request failed: {e}")
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

    def _parse_decision(self, raw: str) -> Optional[LLMDecision]:
        import re
        cleaned = re.sub(r"```(?:json)?\s*", "", raw, flags=re.IGNORECASE).strip()
        cleaned = cleaned.replace("```", "").strip()

        obj_match = re.search(r"(\{.*?\})", cleaned, re.DOTALL)
        if obj_match:
            candidate = obj_match.group(1)
        else:
            candidate = cleaned
            
        try:
            data = json.loads(candidate)
            if not isinstance(data, dict):
                raise ValueError("Decision must be a JSON object")
                
            dec_type = data.get("type", "chat")
            
            steps = None
            if "steps" in data and isinstance(data["steps"], list):
                steps = []
                for item in data["steps"]:
                    if isinstance(item, dict) and "skill" in item:
                        steps.append(SkillCallSpec(
                            skill=item["skill"],
                            params=item.get("params", {}),
                        ))
            
            return LLMDecision(
                type=dec_type,
                message=data.get("message"),
                steps=steps,
                question=data.get("question")
            )
        except Exception as e:
            logger.warning(f"[OpenAILLM] Failed to parse decision JSON.\nRaw: {raw[:300]}\nError: {e}")
            return None
