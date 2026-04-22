"""
Jarvis LLM Fallback Module
==========================
Uses a lightweight local LLM (e.g. Qwen2.5-1.5B or Llama-3.2-1B) to resolve
ambiguous intents or failed actions based on environmental context.

Now enhanced with:
  - ContextSnapshot: rich "present condition" (app, location, visible targets)
  - MemoryManager: injects all past learned recipes into the LLM system prompt
    so the LLM can reason from past learning, not just the current screen.

Flow:
  1. JarvisEngine → MemoryManager.recall() → hit? replay steps directly
  2. Miss → LLMFallbackModule.analyze(raw, failed_action, snapshot, memory_context)
  3. LLM infers corrected intent or asks user
  4. On success → MemoryManager.save() → written to memory/*.md
"""

import logging
import json
import re
from typing import Optional, Dict, Any

from Jarvis.core.intent_engine import Intent, ActionType
from Jarvis.core.context_manager import Context
from Jarvis.core.action_registry import ActionResult
from Jarvis.core.context_collector import ContextSnapshot

logger = logging.getLogger(__name__)


class LLMFallbackModule:
    """
    Handles LLM-based fallback generation.
    Accepts a rich ContextSnapshot and the full memory context string.
    """

    def __init__(self, model_id: str = "Qwen/Qwen2.5-0.5B-Instruct", use_mock: bool = True):
        self.use_mock = use_mock
        self.pipeline = None
        if not use_mock:
            self._init_model(model_id)

    def _init_model(self, model_id: str):
        try:
            from transformers import pipeline
            import torch
            logger.info(f"Loading local LLM {model_id}...")
            self.pipeline = pipeline(
                "text-generation",
                model=model_id,
                model_kwargs={"torch_dtype": torch.float16},
                device_map="auto",
            )
            logger.info("LLM loaded successfully.")
        except Exception as e:
            logger.warning(f"Failed to load transformers LLM: {e}. Falling back to mock.")
            self.use_mock = True

    # ── Main entry ───────────────────────────────
    def analyze(
        self,
        raw_input: str,
        failed_action: Optional[ActionType],
        snapshot: ContextSnapshot,
        memory_context: str = "",
    ) -> tuple[Optional[Intent], Optional[str]]:
        """
        Analyzes a failed command using the LLM, a rich context snapshot,
        and all past memory (as injected text).

        Returns:
            (CorrectedIntent, None)        — high confidence fix, execute directly
            (None, "question to ask user") — unsure, ask for confirmation
        """
        logger.info(f"Triggering LLM Fallback for: {raw_input!r}")

        system_prompt = self._build_system_prompt(memory_context)
        user_prompt = self._build_user_prompt(raw_input, failed_action, snapshot)

        if self.use_mock:
            response_json = self._mock_inference(raw_input, snapshot)
        else:
            response_json = self._real_inference(system_prompt, user_prompt)

        return self._parse_llm_json(response_json, raw_input)

    # ── Prompt Engineering ───────────────────────
    def _build_system_prompt(self, memory_context: str) -> str:
        return (
            "You are Jarvis, an AI assistant that controls Windows via voice commands.\n"
            "A command failed. Your job is to resolve it by:\n"
            "  - Fixing typos or fuzzy phrasing (e.g. 'rduino' → 'Arduino')\n"
            "  - Using the exact 'Present Condition' (current app, location, visible targets)\n"
            "  - Consulting the 'Learned Memory' below for past navigation paths\n\n"
            "IMPORTANT: The same command can mean different things depending on context.\n"
            "  e.g. 'open advanced display' from the DESKTOP requires 4 steps;\n"
            "        from 'Settings - Display' it is just 1 click.\n"
            "  Always pick the recipe whose Preconditions match the current state.\n\n"
            "Valid Intent actions: OPEN_APP, CLOSE_APP, NAVIGATE_LOCATION, CLICK_ELEMENT, PRESS_KEY.\n"
            "Output strictly valid JSON — no markdown, no explanation.\n\n"
            "=== LEARNED MEMORY ===\n"
            f"{memory_context or '(no memory yet — this will be the first time)'}\n"
        )

    def _build_user_prompt(
        self,
        raw_input: str,
        failed_action: Optional[ActionType],
        snapshot: ContextSnapshot,
    ) -> str:
        failed_str = failed_action.name if failed_action else "UNKNOWN"
        return (
            f"Failed Command: '{raw_input}'\n"
            f"Failed Action Type: {failed_str}\n\n"
            "=== PRESENT CONDITION ===\n"
            f"{snapshot.as_text()}\n\n"
            "Based on the Present Condition and Learned Memory above, "
            "output a JSON object classifying the intent.\n"
            "Include a 'category' key indicating where to store this memory.\n"
            "(Use 'apps' for software, 'folders' for directories, 'settings' for Windows options, or 'navigation' for general UI flows).\n\n"
            "Example valid outputs:\n"
            '{"action": "NAVIGATE_LOCATION", "target": "CorrectedName", "confidence": 0.95, "category": "folders"}\n'
            '{"action": "CLICK_ELEMENT",     "target": "ElementName",   "confidence": 0.90, "category": "navigation"}\n'
            '{"action": "OPEN_APP",          "target": "AppName",       "confidence": 0.92, "category": "apps"}\n'
            '{"action": "ASK_USER",          "message": "Did you mean X?"}\n'
        )

    # ── Inference ────────────────────────────────
    def _real_inference(self, system_prompt: str, user_prompt: str) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ]
        outputs = self.pipeline(
            messages,
            max_new_tokens=150,
            temperature=0.1,
            do_sample=False,
        )
        generated_text = outputs[0]["generated_text"][-1]["content"]
        # Strip markdown code fences if present
        match = re.search(r"```(?:json)?(.*?)```", generated_text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return generated_text.strip()

    def _mock_inference(self, raw_input: str, snapshot: ContextSnapshot) -> str:
        """
        Mock inference — used during testing.
        Simulates the LLM reasoning using simple heuristics.
        """
        lower = raw_input.lower()
        targets_lower = [t.lower() for t in snapshot.visible_targets]

        # Fuzzy folder name correction
        if "rduino" in lower and "arduino" in targets_lower:
            return '{"action": "NAVIGATE_LOCATION", "target": "Arduino", "confidence": 0.98, "category": "folders"}'

        if "linkedln" in lower or "linkedin" in lower:
            return '{"action": "OPEN_APP", "target": "linkedin", "confidence": 0.95, "category": "apps"}'

        if "clink" in lower or "click" in lower:
            # Extract the target after "clink/click"
            parts = lower.replace("clink", "click").split("click", 1)
            target = parts[1].strip() if len(parts) > 1 else ""
            if target:
                return f'{{"action": "CLICK_ELEMENT", "target": "{target}", "confidence": 0.88, "category": "navigation"}}'

        return '{"action": "ASK_USER", "message": "I didn\'t quite catch that. Could you clarify?"}'

    # ── JSON parser ──────────────────────────────
    def _parse_llm_json(
        self, json_str: str, raw_input: str
    ) -> tuple[Optional[Intent], Optional[str]]:
        try:
            data = json.loads(json_str)
            action_str = data.get("action", "")

            if action_str == "ASK_USER":
                return None, data.get("message", "Can you clarify?")

            confidence = float(data.get("confidence", 0.0))
            target = data.get("target", "").strip()
            category = data.get("category", "navigation").strip()

            if confidence >= 0.85:
                try:
                    action_enum = ActionType[action_str]
                except KeyError:
                    logger.error(f"LLM returned invalid ActionType: {action_str!r}")
                    return None, "System error interpreting intent."

                corrected_intent = Intent(
                    action=action_enum,
                    target=target,
                    raw=raw_input,
                    confidence=confidence,
                    category=category,
                )
                logger.info(f"LLM → {action_str}({target!r}) category={category!r} confidence={confidence:.2f}")
                return corrected_intent, None
            else:
                return None, f"Did you mean '{target}'?"

        except json.JSONDecodeError:
            logger.error(f"Failed to parse LLM JSON: {json_str!r}")
            return None, "System error in fallback parsing."
