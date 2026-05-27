"""
NVIDIA Cloud LLM Backend
==========================
Uses NVIDIA's OpenAI-compatible API (integrate.api.nvidia.com).
Supports any model hosted on NVIDIA NIM, e.g. qwen/qwen3-coder-480b-a35b-instruct.
API key via system environment variable NVIDIA_API_KEY — never hardcoded.

Usage (standalone):
    from jarvis.llm.backends.nvidia_llm import NvidiaLLM
    llm = NvidiaLLM(model="qwen/qwen3-coder-480b-a35b-instruct")
    plan = llm.plan("open notepad")
"""

import json
import logging
import os
import re
from typing import Optional

from jarvis.llm.llm_interface import LLMInterface, Plan, SkillCallSpec, LLMDecision, ClosedLoopDecision

logger = logging.getLogger(__name__)

# Default NVIDIA NIM endpoint
_DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1"


class NvidiaLLM(LLMInterface):
    """
    Cloud LLM backend using NVIDIA's OpenAI-compatible API.

    Mirrors the interface of OpenAILLM so it can be used as a drop-in
    replacement via the LLM router.
    """

    def __init__(
        self,
        model: str = "qwen/qwen3-coder-480b-a35b-instruct",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        top_p: float = 0.8,
        timeout: float = 30.0,
    ):
        self._model = model
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._top_p = top_p
        self._timeout = timeout
        self._base_url = base_url or _DEFAULT_BASE_URL
        self._api_key = api_key or os.environ.get("NVIDIA_API_KEY", "")
        self._client = None

        logger.debug(
            "[NvidiaLLM] Initialized — model=%s  base_url=%s  key_set=%s",
            self._model,
            self._base_url,
            bool(self._api_key),
        )

    # ── LLMInterface properties ──────────────────────────────

    @property
    def name(self) -> str:
        return f"nvidia/{self._model}"

    # ── Health check ─────────────────────────────────────────

    def health_check(self) -> bool:
        if not self._api_key:
            logger.debug("[NvidiaLLM] No API key configured (NVIDIA_API_KEY).")
            return False
        try:
            client = self._get_client()
            # Lightweight probe — small completion with 1 token
            client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=5,
                temperature=0.0,
            )
            return True
        except Exception as e:
            logger.debug(f"[NvidiaLLM] Health check failed: {e}")
            return False

    # ── plan() ───────────────────────────────────────────────

    def plan(self, prompt: str, memory_context: str = "") -> Optional[Plan]:
        try:
            client = self._get_client()
            messages = [
                {"role": "system", "content": self.build_system_prompt()},
            ]
            if memory_context.strip():
                messages.append({
                    "role": "system",
                    "content": f"Memory context:\n{memory_context}",
                })
            messages.append({"role": "user", "content": prompt})

            response = client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
                top_p=self._top_p,
                timeout=self._timeout,
            )
            content = response.choices[0].message.content.strip()
            self.last_raw_response = content
            return self._parse_plan(content)
        except Exception as e:
            logger.error(f"[NvidiaLLM] plan() request failed: {e}")
            return None

    # ── decide() ─────────────────────────────────────────────

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
                "META-RULES FOR CONTENT DELIVERY:\n"
                "- If the user intent is content generation (explaining, summarizing, drafting code/text, jokes) AND a destination application is specified OR active, you MUST use 'plan' and deliver the content via a 'type_text' skill call.\n"
                "- Do NOT put the primary payload (the explanation/summary/code) in the 'message' field if it belongs in an app.\n"
                "- Use the 'Active App Context' provided in the context to determine if a content generation request should be typed into the current window.\n"
                "\n"
                "CRITICAL RULES:\n"
                "- Only use skills listed in the [Available Skills] section of the context.\n"
                "- Output valid JSON only.\n"
            )

            messages = [
                {"role": "system", "content": sys_prompt},
                {"role": "system", "content": context},
                {"role": "user", "content": prompt},
            ]

            response = client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=self._max_tokens,
                temperature=0.4,
                top_p=self._top_p,
                timeout=self._timeout,
            )
            content = response.choices[0].message.content.strip()
            self.last_raw_response = content
            return self._parse_decision(content)
        except Exception as e:
            logger.error(f"[NvidiaLLM] decide() request failed: {e}")
            return None
    # ── decide_closed_loop() ─────────────────────────────────

    def decide_closed_loop(self, prompt: str, context: str = "") -> Optional[ClosedLoopDecision]:
        try:
            from jarvis.brain.closed_loop_prompt import build_closed_loop_system_prompt
            client = self._get_client()
            sys_prompt = build_closed_loop_system_prompt()
            messages = [
                {"role": "system", "content": sys_prompt},
                {"role": "system", "content": context},
                {"role": "user", "content": prompt},
            ]
            response = client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=self._max_tokens,
                temperature=0.3,
                top_p=self._top_p,
                timeout=self._timeout,
            )
            content = response.choices[0].message.content.strip()
            self.last_raw_response = content
            return self._parse_closed_loop_decision(content)
        except Exception as e:
            logger.error(f"[NvidiaLLM] decide_closed_loop() failed: {e}")
            return None

    def _parse_closed_loop_decision(self, raw: str) -> Optional[ClosedLoopDecision]:
        cleaned = re.sub(r"```(?:json)?\s*", "", raw, flags=re.IGNORECASE).strip()
        cleaned = cleaned.replace("```", "").strip()
        obj_match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
        candidate = obj_match.group(1) if obj_match else cleaned
        try:
            data = json.loads(candidate)
        except Exception:
            return None
        if not isinstance(data, dict) or "status" not in data:
            return None
        actions = []
        if "actions" in data and isinstance(data["actions"], list):
            for item in data["actions"]:
                if isinstance(item, dict) and "skill" in item:
                    actions.append(SkillCallSpec(skill=item["skill"], params=item.get("params", {})))
        return ClosedLoopDecision(
            status=data.get("status", "blocked"),
            reasoning=data.get("reasoning", ""),
            actions=actions,
            summary=data.get("summary"),
            block_reason=data.get("block_reason"),
        )

    # ── Private helpers ──────────────────────────────────────

    def _get_client(self):
        """Lazily create the OpenAI client pointed at the NVIDIA endpoint."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self._api_key,
                    base_url=self._base_url,
                    max_retries=0,
                )
            except ImportError:
                raise RuntimeError(
                    "openai package not installed. Run: pip install openai"
                )
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
            logger.warning(f"[NvidiaLLM] Plan parse error: {e}")
            return None

    def _parse_decision(self, raw: str) -> Optional[LLMDecision]:
        cleaned = re.sub(r"```(?:json)?\s*", "", raw, flags=re.IGNORECASE).strip()
        cleaned = cleaned.replace("```", "").strip()

        obj_match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
        candidate = obj_match.group(1) if obj_match else cleaned

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
                question=data.get("question"),
            )
        except Exception as e:
            logger.warning(
                f"[NvidiaLLM] Failed to parse decision JSON.\nRaw: {raw[:300]}\nError: {e}"
            )
            return None
