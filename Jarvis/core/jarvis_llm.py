"""
Jarvis LLM Fallback Module
==========================
Uses a lightweight local LLM (e.g. Qwen2.5-1.5B or Llama-3.2-1B) to resolve
ambiguous intents or failed actions based on environmental context.

This module acts as a smart parser when IntentEngine fails to understand,
or when ActionRegistry fails to execute (e.g. missing target).
"""

import logging
import json
import re
from typing import Optional, Dict, Any

from Jarvis.core.intent_engine import Intent, ActionType
from Jarvis.core.context_manager import Context
from Jarvis.core.action_registry import ActionResult

logger = logging.getLogger(__name__)

class LLMFallbackModule:
    """
    Handles LLM-based fallback generation.
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
            # We use float16 to keep memory usage low (around 1-2GB for 1B param model)
            self.pipeline = pipeline(
                "text-generation", 
                model=model_id, 
                model_kwargs={"torch_dtype": torch.float16}, 
                device_map="auto"
            )
            logger.info("LLM loaded successfully.")
        except Exception as e:
            logger.warning(f"Failed to load transformers LLM: {e}. Falling back to mock.")
            self.use_mock = True

    def analyze(self, raw_input: str, failed_action: Optional[ActionType], current_context: Context, context_data: Dict[str, Any]) -> tuple[Optional[Intent], Optional[str]]:
        """
        Analyzes a failed command using the LLM and the screen/directory context.
        Returns (CorrectedIntent, None) if highly confident, OR
        Returns (None, "Prompt to ask user") if needs confirmation.
        """
        logger.info(f"Triggering LLM Fallback for: {raw_input!r}")
        
        # ── 1. Gather Context ──
        active_app = current_context.active_app or "Unknown"
        available_targets = context_data.get("available_targets", [])
        
        system_prompt = (
            "You are Jarvis, an intelligent fallback module. The user gave a command that failed. "
            "Your job is to resolve spelling mistakes or fuzzy phrasing based on the available targets in the current context.\n"
            "If you are highly confident, return a JSON object with a corrected intent.\n"
            "If you are unsure, return a JSON action 'ASK_USER' with a clarification message.\n"
            "Valid Intent actions: OPEN_APP, CLOSE_APP, NAVIGATE_LOCATION, CLICK_ELEMENT.\n"
            "Output strictly valid JSON.\n"
        )
        
        user_prompt = (
            f"User Command: '{raw_input}'\n"
            f"Active Application: '{active_app}'\n"
            f"Available Targets (folders/files/elements): {available_targets}\n"
            "Output JSON format:\n"
            "{\"action\": \"NAVIGATE_LOCATION\", \"target\": \"CorrectedTargetName\", \"confidence\": 0.95}\n"
            "OR\n"
            "{\"action\": \"ASK_USER\", \"message\": \"Did you mean X?\"}\n"
        )
        
        if self.use_mock:
            response_json = self._mock_inference(raw_input, available_targets)
        else:
            response_json = self._real_inference(system_prompt, user_prompt)
            
        return self._parse_llm_json(response_json, raw_input)

    def _real_inference(self, system_prompt: str, user_prompt: str) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        outputs = self.pipeline(
            messages,
            max_new_tokens=100,
            temperature=0.1,
            do_sample=False,
        )
        generated_text = outputs[0]["generated_text"][-1]["content"]
        # Extract JSON from potential markdown blocks
        match = re.search(r"```(?:json)?(.*?)```", generated_text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return generated_text.strip()

    def _mock_inference(self, raw_input: str, targets: list) -> str:
        """Mock inference for rapid testing or specific scenarios."""
        lower_input = raw_input.lower()
        if "rduino" in lower_input and any("arduino" in t.lower() for t in targets):
            # Extremely confident fix
            return '{"action": "NAVIGATE_LOCATION", "target": "Arduino", "confidence": 0.98}'
            
        # Default mock response for unknown
        return '{"action": "ASK_USER", "message": "I didn\'t quite catch that. Could you clarify your command?"}'

    def _parse_llm_json(self, json_str: str, raw_input: str) -> tuple[Optional[Intent], Optional[str]]:
        try:
            data = json.loads(json_str)
            action_str = data.get("action", "")
            
            if action_str == "ASK_USER":
                return None, data.get("message", "Can you clarify?")
                
            confidence = float(data.get("confidence", 0.0))
            if confidence >= 0.85:
                # High confidence, parse the action
                try:
                    action_enum = ActionType[action_str]
                    target = data.get("target", "")
                    # Construct fixed intent
                    corrected_intent = Intent(
                        action=action_enum, 
                        target=target,
                        raw=raw_input,
                        confidence=confidence
                    )
                    return corrected_intent, None
                except KeyError:
                    logger.error(f"LLM returned invalid ActionType: {action_str}")
                    return None, "System error interpreting intent."
            else:
                return None, f"Did you mean {data.get('target', 'that')}?"
        except json.JSONDecodeError:
            logger.error(f"Failed to parse LLM JSON output: {json_str}")
            return None, "System error in fallback parsing."
