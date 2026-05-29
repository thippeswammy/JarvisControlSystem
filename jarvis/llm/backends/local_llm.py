"""
Local LLM Backend — Ollama
===========================
Uses Ollama's OpenAI-compatible REST API to run gemma3:4b
locally. Ollama handles CUDA, cuBLAS, cuDNN — no manual setup needed.

Setup:
    1. Install Ollama: https://ollama.com/download
    2. ollama pull gemma3:4b
    3. ollama serve   (starts on localhost:11434 automatically on Windows)

Why gemma3:4b:
    - 4B parameters → ~3GB VRAM (fits within 4GB limit)
    - Instruction-tuned: follows JSON output format reliably
    - 128k context window: fits full RAG memory injection
    - Fallback: gemma3:4b
"""

import json
import logging
import subprocess
import time
from typing import Optional

import requests

from jarvis.utils.ollama_utils import ensure_ollama_running
from jarvis.llm.llm_interface import LLMInterface, Plan, SkillCallSpec, LLMDecision, ClosedLoopDecision

logger = logging.getLogger(__name__)
_DEFAULT_MODEL = "gemma3:4b"


class LocalLLM(LLMInterface):
    """
    Ollama HTTP client. Connects to the locally running Ollama server.

    Integration:
        LocalLLM → HTTP POST → Ollama /v1/chat/completions
                             → GPU inference (gemma3:4b, Q4_K_M)
                             → JSON Plan response
    """

    def __init__(
        self,
        api_url: str = "http://localhost:11434/v1",
        model: str = _DEFAULT_MODEL,
        fallback_model: str = _DEFAULT_MODEL,
        max_tokens: int = 30000,
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
            logger.debug("[LocalLLM] Ollama not running or unreachable. Attempting auto-start.")
            ensure_ollama_running(url=self._api_url.replace("/v1", ""))
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
            self.last_raw_response = content
            return self._parse_plan(content)

        except requests.exceptions.Timeout:
            logger.warning(f"[LocalLLM] Request timed out after {self._timeout}s")
            return None
        except Exception as e:
            logger.error(f"[LocalLLM] Request failed: {e}")
            return None

    def decide(self, prompt: str, context: str = "") -> Optional[LLMDecision]:
        model = self._active_model or self._model

        sys_prompt = (
            "You are JARVIS, an advanced AI desktop assistant.\n"
            "You must ALWAYS return a SINGLE valid JSON object and absolutely nothing else. No markdown, no explanations.\n"
            "If you just want to talk (greetings, quick help), return a 'chat' type JSON.\n"
            "\n"
            "Your JSON object must exactly match one of these 4 formats:\n"
            '1. Chat only: {"type": "chat", "message": "your reply here"}\n'
            '2. Plan only: {"type": "plan", "steps": [{"skill": "skill_name", "params": {}}]}\n'
            '3. Mixed (talk AND act): {"type": "mixed", "message": "your reply", "steps": [{"skill": "skill_name", "params": {}}]}\n'
            '4. Clarify (ask user): {"type": "clarify", "question": "your question"}\n'
            "\n"
            "META-RULES FOR CONTENT DELIVERY:\n"
            "- If the user intent is content generation (explaining, summarizing, drafting code/text, jokes) AND a destination application is specified OR active, you MUST use 'plan' and deliver the content via a 'type_text' skill call.\n"
            "- Do NOT put the primary payload (the explanation/summary/code) in the 'message' field if it belongs in an app.\n"
            "- Use the 'Active App Context' provided in the context to determine if a content generation request should be typed into the current window.\n"
            "\n"
            "CRITICAL RULES:\n"
            "- Only use skills listed in the [Available Skills] section.\n"
            "- If the user says 'hello' or generic talk, use type 'chat'.\n"
            "- If the user asks to do something, use 'plan' or 'mixed'.\n"
            "- Output valid JSON only.\n"
        )

        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "system", "content": context},
            {"role": "user", "content": prompt}
        ]

        for attempt in range(3):
            payload = {
                "model": model,
                "messages": messages,
                "max_tokens": self._max_tokens + 200,
                "temperature": 0.4 if attempt == 0 else 0.1,  # Lower temperature on retry
                "stream": False,
            }

            try:
                resp = requests.post(
                    f"{self._api_url}/chat/completions",
                    json=payload,
                    timeout=self._timeout,
                )
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"].strip()
                self.last_raw_response = content
                
                is_valid, error_msg = self._is_valid_json_decision(content)
                if is_valid:
                    return self._parse_decision(content)
                
                if attempt < 2:
                    logger.warning(f"[LocalLLM] JSON parse failure on attempt {attempt+1}: {error_msg}. Retrying self-correction...")
                    messages.append({"role": "assistant", "content": content})
                    messages.append({"role": "user", "content": f"Your response was not valid JSON. Parse error: {error_msg}. Please fix the JSON and return ONLY the valid JSON object matching the schema."})
                else:
                    logger.error(f"[LocalLLM] JSON self-correction exhausted all attempts.")
                    return self._parse_decision(content)
            except Exception as e:
                logger.error(f"[LocalLLM] Decide request failed on attempt {attempt+1}: {e}")
                if attempt == 2:
                    return None

    def _call_llm_closed_loop(self, prompt: str, context: str) -> Optional[str]:
        """
        Native closed-loop LLM call. Returns raw response text.
        Uses 3-attempt self-correction for JSON issues.
        Parsing is handled by the base class _parse_closed_loop_decision().
        """
        from jarvis.brain.closed_loop_prompt import build_closed_loop_system_prompt

        model = self._active_model or self._model
        sys_prompt = build_closed_loop_system_prompt()

        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "system", "content": context},
            {"role": "user", "content": prompt}
        ]

        for attempt in range(3):
            payload = {
                "model": model,
                "messages": messages,
                "max_tokens": self._max_tokens + 200,
                "temperature": 0.3 if attempt == 0 else 0.1,
                "stream": False,
            }
            try:
                resp = requests.post(
                    f"{self._api_url}/chat/completions",
                    json=payload,
                    timeout=self._timeout,
                )
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"].strip()
                self.last_raw_response = content

                # Check if parseable by base class
                if self._parse_closed_loop_decision(content):
                    return content

                if attempt < 2:
                    logger.warning(f"[LocalLLM] Closed-loop JSON parse failure on attempt {attempt+1}. Retrying...")
                    messages.append({"role": "assistant", "content": content})
                    messages.append({"role": "user", "content": (
                        "Your response was not valid JSON for the closed-loop schema. "
                        'Return ONLY: {"status": "in_progress"|"done"|"blocked", "reasoning": "...", "actions": [...]}'
                    )})
                else:
                    logger.error("[LocalLLM] Closed-loop JSON self-correction exhausted.")
                    return content  # Return raw; base class will fallback to decide() wrapper
            except Exception as e:
                logger.error(f"[LocalLLM] Closed-loop request failed attempt {attempt+1}: {e}")
                if attempt == 2:
                    return None
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

