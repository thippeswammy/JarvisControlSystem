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

from jarvis.llm.llm_interface import LLMInterface, Plan, SkillCallSpec, LLMDecision, ClosedLoopDecision

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
            self.last_raw_response = content
            return self._parse_plan(content)
        except requests.exceptions.Timeout:
            logger.warning(f"[TunneledLLM] Timeout after {self._timeout}s")
            return None
        except Exception as e:
            logger.error(f"[TunneledLLM] Request failed: {e}")
            return None

    def decide(self, prompt: str, context: str = "") -> Optional[LLMDecision]:
        if not self._api_url:
            return None

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
            {"role": "user", "content": prompt}
        ]

        for attempt in range(3):
            try:
                resp = requests.post(
                    f"{self._api_url}/chat/completions",
                    headers=self._headers(),
                    json={
                        "model": self._model,
                        "messages": messages,
                        "max_tokens": self._max_tokens + 200,
                        "temperature": 0.4 if attempt == 0 else 0.1,  # Lower temperature on retry
                        "stream": False,
                    },
                    timeout=self._timeout,
                )
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"].strip()
                self.last_raw_response = content
                
                is_valid, error_msg = self._is_valid_json_decision(content)
                if is_valid:
                    return self._parse_decision(content)
                
                if attempt < 2:
                    logger.warning(f"[TunneledLLM] JSON parse failure on attempt {attempt+1}: {error_msg}. Retrying self-correction...")
                    messages.append({"role": "assistant", "content": content})
                    messages.append({"role": "user", "content": f"Your response was not valid JSON. Parse error: {error_msg}. Please fix the JSON and return ONLY the valid JSON object matching the schema."})
                else:
                    logger.error(f"[TunneledLLM] JSON self-correction exhausted all attempts.")
                    return self._parse_decision(content)
            except Exception as e:
                logger.error(f"[TunneledLLM] Decide request failed on attempt {attempt+1}: {e}")
                if attempt == 2:
                    return None

    def decide_closed_loop(self, prompt: str, context: str = "") -> Optional[ClosedLoopDecision]:
        if not self._api_url:
            return None

        from jarvis.brain.closed_loop_prompt import build_closed_loop_system_prompt
        sys_prompt = build_closed_loop_system_prompt()

        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "system", "content": context},
            {"role": "user", "content": prompt}
        ]

        for attempt in range(3):
            try:
                resp = requests.post(
                    f"{self._api_url}/chat/completions",
                    headers=self._headers(),
                    json={
                        "model": self._model,
                        "messages": messages,
                        "max_tokens": self._max_tokens + 200,
                        "temperature": 0.3 if attempt == 0 else 0.1,
                        "stream": False,
                    },
                    timeout=self._timeout,
                )
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"].strip()
                self.last_raw_response = content

                decision = self._parse_closed_loop_decision(content)
                if decision:
                    return decision

                if attempt < 2:
                    logger.warning(f"[TunneledLLM] Closed-loop JSON parse failure on attempt {attempt+1}. Retrying...")
                    messages.append({"role": "assistant", "content": content})
                    messages.append({"role": "user", "content": (
                        "Your response was not valid JSON for the closed-loop schema. "
                        'Return ONLY: {"status": "in_progress"|"done"|"blocked", "reasoning": "...", "actions": [...]}'
                    )})
                else:
                    logger.error("[TunneledLLM] Closed-loop JSON self-correction exhausted.")
                    return ClosedLoopDecision(status="blocked", reasoning="JSON parse failure", block_reason="JSON parse failure")
            except Exception as e:
                logger.error(f"[TunneledLLM] Closed-loop request failed attempt {attempt+1}: {e}")
                if attempt == 2:
                    return None

    def _parse_closed_loop_decision(self, raw: str) -> Optional[ClosedLoopDecision]:
        import re
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

    def _is_valid_json_decision(self, content: str) -> tuple[bool, Optional[str]]:
        import json
        import re
        cleaned = re.sub(r"```(?:json)?\s*", "", content, flags=re.IGNORECASE).strip()
        cleaned = cleaned.replace("```", "").strip()
        obj_match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
        candidate = obj_match.group(1) if obj_match else cleaned
        try:
            data = json.loads(candidate)
            if isinstance(data, dict) and "type" in data:
                return True, None
            return False, "JSON does not contain a 'type' field"
        except Exception as e:
            return False, str(e)

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

    def _parse_decision(self, raw: str) -> Optional[LLMDecision]:
        import re
        cleaned = re.sub(r"```(?:json)?\s*", "", raw, flags=re.IGNORECASE).strip()
        cleaned = cleaned.replace("```", "").strip()

        obj_match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
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
            logger.warning(f"[TunneledLLM] Failed to parse decision JSON.\nRaw: {raw[:300]}\nError: {e}")
            return None
