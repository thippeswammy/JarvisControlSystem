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

from jarvis.llm.llm_interface import LLMInterface, Plan, SkillCallSpec, LLMDecision

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

        # ── Heuristic Compound Command Splitter ──────────
        if "[this is a compound command with" in text:
            match = re.search(r"parts:\s*(.+?)\]\.\s*plan", text)
            if match:
                parts_str = match.group(1)
                raw_parts = parts_str.split('", "')
                parts = [p.strip().strip('"') for p in raw_parts if p.strip()]
                if not parts:
                    parts = re.findall(r'"([^"]+)"', parts_str)
                if parts:
                    plan_steps = []
                    for part in parts:
                        part_plan = self.plan(part, memory_context)
                        if part_plan:
                            plan_steps.extend(part_plan)
                    return plan_steps

        separators = [" and then ", " then ", " after that ", " also ", " and navigate to ", " and write ", " and type ", " and open "]
        for sep in separators:
            if sep in text:
                parts = []
                if sep in [" and write ", " and type "]:
                    split_parts = text.split(sep, 1)
                    parts = [split_parts[0], sep.replace(" and ", "").strip() + " " + split_parts[1]]
                elif sep == " and navigate to ":
                    split_parts = text.split(sep, 1)
                    parts = [split_parts[0], "navigate to " + split_parts[1]]
                elif sep == " and open ":
                    split_parts = text.split(sep, 1)
                    parts = [split_parts[0], "open " + split_parts[1]]
                else:
                    parts = [p.strip() for p in text.split(sep) if p.strip()]
                
                plan_steps = []
                for part in parts:
                    part_plan = self.plan(part, memory_context)
                    if part_plan:
                        plan_steps.extend(part_plan)
                if plan_steps:
                    return plan_steps

        # ── Safe Quoted-Block Protection ──────────
        has_quotes = '"' in text or "'" in text
        if has_quotes:
            text_outside = re.sub(r'("[^"]*"|\'[^\']*\')', '', text).strip()
            cognitive_keywords = ["summarize", "explain", "translate", "tell me", "what is", "analyze", "read", "write a", "parse", "how to", "search", "lookup"]
            if any(k in text_outside for k in cognitive_keywords):
                return [SkillCallSpec(
                    skill="chat_reply",
                    params={"message": f"I analyzed the text: {prompt}. It contains a query or request to process text rather than execute action."}
                )]

        # ── Session Activate/Deactivate ──────────
        if re.search(r"\b(hi jarvis|hello jarvis|activate|hey jarvis)\b", text):
            return [SkillCallSpec(skill="session_activate", params={})]
        if re.search(r"\b(bye|goodbye|close jarvis|deactivate|stop jarvis)\b", text):
            return [SkillCallSpec(skill="session_deactivate", params={})]

        # ── Greetings / Help ──────────
        if re.search(r"\b(hi|hello|hey|greetings|morning|evening)\b", text) and len(text.split()) < 4:
            return [SkillCallSpec(
                skill="chat_reply",
                params={"message": "Hello! My cognitive core is running in emergency mode, but I can still help with basic app controls."}
            )]
        if re.search(r"\b(help|what can you do|who are you)\b", text):
            return [SkillCallSpec(
                skill="chat_reply",
                params={"message": "I am JARVIS. My main brain is offline, so I'm using my emergency reflexes. I can open apps, type text, and control your system volume or windows."}
            )]

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
        if re.search(r"^\s*(?:open|launch|start|run)\b", text) and not text.endswith("?"):
            target = re.sub(r"^\s*(?:open|launch|start|run)\b\s*", "", text).strip()
            if target:
                return [SkillCallSpec(skill="open_app", params={"target": target, "_source": "mock"})]

        # ── Context-Aware Testing Mock ────────────────
        if "semantic intent:" in text:
            # Parse enriched prompt:
            app_match = re.search(r"active app context:\s*(.+)", text)
            intent_match = re.search(r"semantic intent:\s*(.+)", text)
            
            if app_match and intent_match:
                app_ctx = app_match.group(1).strip()
                intent_ctx = intent_match.group(1).strip()
                
                # App-specific mock simulation
                if intent_ctx == "navigate_back":
                    if "explorer" in app_ctx:
                        return [SkillCallSpec(skill="press_key", params={"key": "alt+left"})]
                    # Could add browser mock: if "msedge" in app_ctx: return "alt+left" etc.

        # ── Navigation ────────────────────────────────
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
        bring_back_match = re.search(r"\b(bring|restore|focus|activate)\s+(?:back\s+)?([\w\s]+?)(?:\s+back)?$", text)
        if bring_back_match:
            target = bring_back_match.group(2).strip()
            if target not in ["window", "it", "them", "this", "that", "the app", "the window", ""]:
                return [SkillCallSpec(skill="activate_window", params={"target": target, "_source": "mock"})]

        if re.search(r"^\s*(?:minimize|minimise)\b", text):
            return [SkillCallSpec(skill="minimize_window", params={"_source": "mock"})]
        if re.search(r"^\s*(?:maximize|maximise|fullscreen)\b", text):
            return [SkillCallSpec(skill="maximize_window", params={"_source": "mock"})]
        if re.search(r"^\s*(?:close|quit|exit)\b", text):
            target = re.sub(r"^\s*(?:close|quit|exit)\b\s*", "", text).strip() or "active"
            return [SkillCallSpec(skill="close_app", params={"target": target, "_source": "mock"})]

        # ── Keyboard ──────────────────────────────────
        m = re.search(r"^\s*(?:press|hold)\b\s+(.+)", text)
        if m:
            return [SkillCallSpec(skill="press_key", params={"key": m.group(1).strip(), "_source": "mock"})]

        # ── Typing ────────────────────────────────────
        m = re.search(r"^\s*(?:type|write|say)\s+(.+?)\s+(?:in|into|on|to)\s+([\w\s]+)$", text)
        if m:
            return [SkillCallSpec(skill="type_text", params={"text": m.group(1).strip(), "target": m.group(2).strip(), "_source": "mock"})]

        m = re.search(r"^\s*(?:type|write|say)\b\s+(.+)", text)
        if m:
            return [SkillCallSpec(skill="type_text", params={"text": m.group(1).strip(), "_source": "mock"})]

        # ── Unknown → ask user ────────────────────────
        logger.info(f"[MockLLM] No heuristic match for: {text!r}")
        return [SkillCallSpec(
            skill="ask_user",
            params={"reason": f"I don't know how to handle: '{prompt}'"}
        )]

    def decide(self, prompt: str, context: str = "") -> Optional[LLMDecision]:
        logger.debug(f"[MockLLM] Deciding for: {prompt!r}")
        plan = self.plan(prompt, context)
        if plan:
            # 1. Clarification
            if len(plan) == 1 and plan[0].skill == "ask_user":
                return LLMDecision(type="clarify", question=plan[0].params.get("reason", "Could you clarify?"))
            
            # 2. Pure Chat
            if len(plan) == 1 and plan[0].skill == "chat_reply":
                return LLMDecision(type="chat", message=plan[0].params.get("message", "I'm not sure."))
            
            # 3. Mixed / Plan
            chat_step = next((s for s in plan if s.skill == "chat_reply"), None)
            other_steps = [s for s in plan if s.skill != "chat_reply"]
            
            if chat_step and other_steps:
                return LLMDecision(type="mixed", message=chat_step.params.get("message"), steps=other_steps)
            elif other_steps:
                return LLMDecision(type="plan", steps=other_steps)
            
        return LLMDecision(type="chat", message="I'm a mock brain, and I don't know what to say.")
