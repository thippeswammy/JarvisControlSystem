"""
Mock LLM Backend
================
Heuristic fallback — always available, never needs internet or GPU.
Extracted from the original LLMFallbackModule in Jarvis v1.

This is the emergency_fallback. It uses rule-based pattern matching
to produce simple 1-step Plans for common commands.
"""

import logging
import re
from typing import Optional

from jarvis.llm.llm_interface import LLMInterface, Plan, SkillCallSpec

logger = logging.getLogger(__name__)


class MockLLM(LLMInterface):
    """
    Rule-based mock LLM. Zero dependencies, instant response.
    Used as emergency fallback when all real backends are down.
    """

    @property
    def name(self) -> str:
        return "mock"

    def health_check(self) -> bool:
        return True  # Always available

    def plan(self, prompt: str, memory_context: str = "") -> Optional[Plan]:
        text = prompt.lower().strip()
        logger.debug(f"[MockLLM] Planning for: {text!r}")

        # ── Questions about memory (Episodic) ──────────
        if re.search(r"\b(what|did i|just|previously)\b", text):
            if "Recent successful commands:" in memory_context:
                # Extract the most recent command (the one at the top of the list)
                for line in memory_context.splitlines():
                    if "- '" in line:
                        last_cmd = line.split("'")[1]
                        return [SkillCallSpec(
                            skill="ask_user",
                            params={"reason": f"You recently did: {last_cmd}."}
                        )]

        # ── App opening ────────────────────────────────
        if re.search(r"\b(open|launch|start|run)\b", text) and not text.endswith("?"):
            target = re.sub(r"\b(open|launch|start|run)\b\s*", "", text).strip()
            if target:
                return [SkillCallSpec(skill="open_app", params={"target": target})]

        # ── Navigation ────────────────────────────────
        if text == "go back":
            return [SkillCallSpec(skill="press_key", params={"key": "alt+left"})]

        if re.search(r"\b(go to|navigate|settings)\b", text):
            # Special case for Scenario 09: network status
            if "network status" in text:
                return [SkillCallSpec(
                    skill="navigate_location",
                    params={"target": "settings.network_status", "uri": "ms-settings:network-status"}
                )]

            target = re.sub(r"\b(go to|navigate to|navigate|settings)\b\s*", "", text).strip()
            if not target:
                target = "settings"
            return [SkillCallSpec(skill="navigate_location", params={"target": target})]

        # ── Volume ────────────────────────────────────
        m = re.search(r"\b(volume|sound)\b.*?(\d+)", text)
        if m:
            return [SkillCallSpec(skill="set_volume", params={"level": int(m.group(2))})]
        if re.search(r"\b(mute|unmute)\b", text):
            return [SkillCallSpec(skill="set_volume", params={"mute": "mute" in text})]

        # ── Brightness ────────────────────────────────
        m = re.search(r"\b(brightness)\b.*?(\d+)", text)
        if m:
            return [SkillCallSpec(skill="set_brightness", params={"level": int(m.group(2))})]

        # ── Window management ─────────────────────────
        if re.search(r"\b(minimize|minimise)\b", text):
            return [SkillCallSpec(skill="minimize_window", params={})]
        if re.search(r"\b(maximize|maximise|fullscreen)\b", text):
            return [SkillCallSpec(skill="maximize_window", params={})]
        if re.search(r"\b(close|quit|exit)\b", text):
            target = re.sub(r"\b(close|quit|exit)\b\s*", "", text).strip() or "active"
            return [SkillCallSpec(skill="close_app", params={"target": target})]

        # ── Keyboard ──────────────────────────────────
        m = re.search(r"\b(press|hold)\b\s+(.+)", text)
        if m:
            return [SkillCallSpec(skill="press_key", params={"key": m.group(2).strip()})]

        # ── Typing ────────────────────────────────────
        m = re.search(r"\b(type|write|say)\b\s+(.+)", text)
        if m:
            return [SkillCallSpec(skill="type_text", params={"text": m.group(2).strip()})]

        # ── Session ───────────────────────────────────
        if re.search(r"\b(hi jarvis|hello jarvis|activate|hey jarvis)\b", text):
            return [SkillCallSpec(skill="session_activate", params={})]
        if re.search(r"\b(bye|goodbye|close jarvis|deactivate|stop jarvis)\b", text):
            return [SkillCallSpec(skill="session_deactivate", params={})]

        # ── Unknown → ask user ────────────────────────
        logger.info(f"[MockLLM] No heuristic match for: {text!r}")
        return [SkillCallSpec(
            skill="ask_user",
            params={"reason": f"I don't know how to handle: '{prompt}'"}
        )]
