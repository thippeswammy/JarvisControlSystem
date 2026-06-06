"""
LLM Interface
=============
Abstract base class for all LLM backends.
Every backend implements this single contract.

The Plan return type is a list of SkillCall dicts:
    [
        {"skill": "open_app", "params": {"target": "notepad"}},
        {"skill": "type_text", "params": {"text": "hello world"}},
    ]
"""

import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


import os
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class SkillCallSpec:
    """A single planned action from the LLM."""
    skill: str
    params: dict = field(default_factory=dict)


Plan = list[SkillCallSpec]

@dataclass
class LLMDecision:
    """The unified decision from the LLM Brain."""
    type: str  # "chat", "plan", "mixed", "clarify", "agent", "multiagent", "mcp"
    message: Optional[str] = None
    steps: Optional[Plan] = None
    question: Optional[str] = None
    # Agent fields
    agent: Optional[str] = None
    agent_task: Optional[str] = None
    agent_tasks: Optional[list[dict]] = None   # for multiagent
    # MCP fields
    mcp_server: Optional[str] = None
    mcp_tool: Optional[str] = None
    mcp_params: Optional[dict] = None


@dataclass
class ClosedLoopDecision:
    """
    Decision from the LLM within the closed-loop execution cycle.
    
    The LLM signals:
      - "in_progress": actions to execute, then re-sense and loop
      - "done":        goal is complete, exit the loop
      - "blocked":     cannot proceed, escalate to recovery/user
    """
    status: str              # "done", "in_progress", "blocked"
    reasoning: str = ""      # LLM's internal reasoning (logged, not shown to user)
    actions: list = field(default_factory=list)  # list[SkillCallSpec] — empty when done
    summary: Optional[str] = None  # Populated when status="done" — what was accomplished
    block_reason: Optional[str] = None  # Populated when status="blocked"
    question: Optional[str] = None  # Custom dynamic question to ask the user when blocked



class LLMInterface(ABC):
    """
    Abstract base for all LLM backends (Ollama, OpenAI, Tunneled, Mock).

    Every backend must implement:
      - plan(prompt, context) → Plan
      - decide(prompt, context) → LLMDecision
      - health_check() → bool
      - name property

    Closed-loop support is provided by default via decide() wrapping.
    Backends can optionally override _call_llm_closed_loop() for native support.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable backend name (e.g. 'local/ollama', 'openai', 'mock')."""

    @abstractmethod
    def health_check(self) -> bool:
        """
        Returns True if this backend is currently reachable and ready.
        Must be fast (<2s). Called from health monitor thread.
        """

    @abstractmethod
    def plan(self, prompt: str, memory_context: str = "") -> Optional[Plan]:
        """
        Given a user command + memory context, return an ordered Plan.
        Returns None if the backend cannot produce a valid plan.

        Args:
            prompt: The raw user command (e.g. "open display settings")
            memory_context: RAG-retrieved memory snippets for context

        Returns:
            Plan (list of SkillCallSpec), or None on failure / uncertainty.
        """

    @abstractmethod
    def decide(self, prompt: str, context: str = "") -> Optional[LLMDecision]:
        """
        Given a user command and full context block, make a unified decision.
        Returns None if the backend cannot produce a valid decision.
        """

    # ── Closed-Loop Support (shared by all backends) ──────────

    def decide_closed_loop(self, prompt: str, context: str = "") -> Optional[ClosedLoopDecision]:
        """
        Closed-loop decision with 3-tier strategy:
          1. Try native closed-loop call (_call_llm_closed_loop)
          2. If not implemented, wrap decide() → ClosedLoopDecision
        
        Subclasses can override _call_llm_closed_loop() for native support.
        """
        # Tier 1: Try native closed-loop (HTTP backends override this)
        try:
            raw = self._call_llm_closed_loop(prompt, context)
            if raw is not None:
                decision = self._parse_closed_loop_decision(raw)
                if decision:
                    return decision
        except NotImplementedError:
            pass  # Fall through to Tier 2
        except Exception as e:
            logger.warning(f"[{self.name}] Native closed-loop failed: {e}. Falling back to decide() wrapper.")

        # Tier 2: Wrap decide() into a ClosedLoopDecision
        return self._wrap_decide_as_closed_loop(prompt, context)

    def _call_llm_closed_loop(self, prompt: str, context: str) -> Optional[str]:
        """
        Override in HTTP backends to make a native closed-loop LLM call.
        Returns raw response text, or None if not supported.
        Raise NotImplementedError if the backend doesn't support native closed-loop.
        """
        raise NotImplementedError

    def _wrap_decide_as_closed_loop(self, prompt: str, context: str) -> Optional[ClosedLoopDecision]:
        """
        Fallback: call decide() and convert LLMDecision → ClosedLoopDecision.
        This means ANY backend works with the closed-loop engine automatically.
        """
        decision = self.decide(prompt, context)
        if decision is None:
            return ClosedLoopDecision(
                status="blocked",
                reasoning=f"{self.name} returned no decision",
                block_reason="LLM returned None",
            )

        # Map LLMDecision types to ClosedLoopDecision
        if decision.type == "chat":
            return ClosedLoopDecision(
                status="done",
                reasoning="LLM responded with chat (no actions needed)",
                summary=decision.message or "",
            )
        elif decision.type == "clarify":
            return ClosedLoopDecision(
                status="blocked",
                reasoning="LLM needs clarification",
                block_reason=decision.question or "Need more information",
                question=decision.question or "Need more information",
            )
        elif decision.type in ("plan", "mixed"):
            actions = decision.steps or []
            return ClosedLoopDecision(
                status="in_progress" if actions else "done",
                reasoning=f"LLM generated {len(actions)} action(s)",
                actions=actions,
                summary=decision.message,
            )
        elif decision.type == "agent":
            actions = []
            if decision.agent and decision.agent_task:
                actions.append(SkillCallSpec(
                    skill="run_agent",
                    params={
                        "agent": decision.agent,
                        "task": decision.agent_task,
                    }
                ))
            return ClosedLoopDecision(
                status="in_progress" if actions else "done",
                reasoning="LLM delegated to sub-agent",
                actions=actions,
                summary=decision.message,
            )
        elif decision.type == "multiagent":
            actions = []
            if decision.agent_tasks:
                actions.append(SkillCallSpec(
                    skill="run_agent_pipeline",
                    params={
                        "tasks": decision.agent_tasks,
                    }
                ))
            return ClosedLoopDecision(
                status="in_progress" if actions else "done",
                reasoning="LLM delegated to multi-agent pipeline",
                actions=actions,
                summary=decision.message,
            )
        elif decision.type == "mcp":
            actions = []
            if decision.mcp_server and decision.mcp_tool:
                actions.append(SkillCallSpec(
                    skill="call_mcp_tool",
                    params={
                        "server": decision.mcp_server,
                        "tool": decision.mcp_tool,
                        "params": decision.mcp_params or {},
                    }
                ))
            return ClosedLoopDecision(
                status="in_progress" if actions else "done",
                reasoning="LLM called MCP tool",
                actions=actions,
                summary=decision.message,
            )
        else:
            # Fallback for any other decision type
            actions = decision.steps or []
            return ClosedLoopDecision(
                status="in_progress" if actions else "done",
                reasoning=f"LLM decision type: {decision.type}",
                actions=actions,
                summary=decision.message,
            )

    @staticmethod
    def _parse_closed_loop_decision(raw: str) -> Optional[ClosedLoopDecision]:
        """
        Parse raw LLM text into a ClosedLoopDecision.
        Shared by ALL backends — no duplication needed.
        """
        cleaned = re.sub(r"```(?:json)?\s*", "", raw, flags=re.IGNORECASE).strip()
        cleaned = cleaned.replace("```", "").strip()

        obj_match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
        candidate = obj_match.group(1) if obj_match else cleaned

        try:
            data = json.loads(candidate)
        except Exception:
            # Try healing common JSON issues
            try:
                healed = candidate.replace("'", '"')
                # Fix trailing commas
                healed = re.sub(r",\s*([}\]])", r"\1", healed)
                data = json.loads(healed)
            except Exception:
                logger.debug(f"[LLMInterface] Failed to parse closed-loop JSON: {raw[:200]}")
                return None

        if not isinstance(data, dict) or "status" not in data:
            logger.debug(f"[LLMInterface] Closed-loop JSON missing 'status' field: {data}")
            return None

        actions = []
        if "actions" in data and isinstance(data["actions"], list):
            for item in data["actions"]:
                if isinstance(item, dict) and "skill" in item:
                    actions.append(SkillCallSpec(
                        skill=item["skill"],
                        params=item.get("params", {}),
                    ))

        return ClosedLoopDecision(
            status=data.get("status", "blocked"),
            reasoning=data.get("reasoning", ""),
            actions=actions,
            summary=data.get("summary"),
            block_reason=data.get("block_reason"),
            question=data.get("question") or data.get("block_reason"),
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

    def _parse_plan(self, raw: str) -> Optional[Plan]:
        """Extract JSON array from LLM response and convert to Plan."""
        import re
        
        # Step 1: Strip all markdown code fences (```json ... ``` or ``` ... ```)
        cleaned = re.sub(r"```(?:json)?\s*", "", raw, flags=re.IGNORECASE).strip()
        cleaned = cleaned.replace("```", "").strip()

        # Step 2: Extract first valid JSON array via regex (greedy)
        array_match = re.search(r"(\[.*\])", cleaned, re.DOTALL)
        candidate = array_match.group(1) if array_match else cleaned

        try:
            data = json.loads(candidate)
            if not isinstance(data, list):
                data = [data]
            plan = []
            for item in data:
                if isinstance(item, dict) and "skill" in item:
                    plan.append(SkillCallSpec(
                        skill=item["skill"],
                        params=item.get("params", {}),
                    ))
            return plan if plan else None
        except json.JSONDecodeError:
            # Step 3: Last-resort — find any {"skill": ...} object in the raw text
            objects = re.findall(r'\{[^{}]*"skill"[^{}]*\}', cleaned, re.DOTALL)
            if objects:
                plan = []
                for obj_str in objects:
                    try:
                        item = json.loads(obj_str)
                        if "skill" in item:
                            plan.append(SkillCallSpec(skill=item["skill"], params=item.get("params", {})))
                    except Exception:
                        continue
                if plan:
                    return plan
            logger.warning(f"[LLMInterface] Failed to parse plan JSON.\nRaw: {raw[:300]}")
            return None

    def _parse_decision(self, raw: str) -> Optional[LLMDecision]:
        import re
        
        # Pre-clean: strip markdown fences globally before extraction
        cleaned = re.sub(r"```(?:json)?\s*", "", raw, flags=re.IGNORECASE).strip()
        cleaned = cleaned.replace("```", "").strip()

        # Strategy 1: Find the largest outermost JSON object {...}
        # This handles cases where the LLM adds text before or after the JSON block.
        obj_match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
        candidate = obj_match.group(1) if obj_match else cleaned
            
        try:
            data = json.loads(candidate)
        except Exception:
            try:
                healed = self._heal_json(candidate)
                data = json.loads(healed)
            except Exception:
                # Strategy 2: If JSON loads failed, it might be partial or contain non-JSON text.
                # Try to find ANY { } block if we haven't already.
                if candidate != cleaned: # we already tried the search once
                    # Wrap the raw text (cleaned of markdown) as a chat message as a last resort.
                    # BUT: if it still looks like JSON (starts with {), try to strip the outer layer.
                    if cleaned.startswith("{") and "}" in cleaned:
                        # Final attempt: try to just take everything between first and last bracket
                        try:
                            idx_start = cleaned.find("{")
                            idx_end = cleaned.rfind("}")
                            data = json.loads(cleaned[idx_start:idx_end+1])
                        except Exception:
                            return LLMDecision(type="chat", message=self._clean_chat_text(raw))
                    else:
                        return LLMDecision(type="chat", message=self._clean_chat_text(raw))
                else:
                    return LLMDecision(type="chat", message=self._clean_chat_text(raw))

        try:
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
            logger.warning(f"[LLMInterface] Failed to parse decision JSON fields.\nRaw: {raw[:300]}\nError: {e}")
            return LLMDecision(type="chat", message=self._clean_chat_text(raw))

    def _clean_chat_text(self, text: str) -> str:
        """Strips markdown fences and attempts to hide JSON artifacts from the user."""
        import re
        # Remove markdown fences
        text = re.sub(r"```(?:json)?\s*", "", text, flags=re.IGNORECASE).strip()
        text = text.replace("```", "").strip()
        # If it's JUST a JSON object, try to extract the "message" or "question" field
        if text.startswith("{") and text.endswith("}"):
            try:
                data = json.loads(text)
                if "message" in data: return data["message"]
                if "question" in data: return data["question"]
            except:
                pass
        return text
        
    def _heal_json(self, s: str) -> str:
        """Autonomously closes open JSON structures for truncated LLM responses."""
        s = s.strip()
        if not s.startswith("{"):
            return s
        open_braces = 0
        open_brackets = 0
        in_string = False
        escape = False
        
        for i, char in enumerate(s):
            if escape:
                escape = False
                continue
            if char == "\\":
                escape = True
                continue
            if char == '"' and (i == 0 or s[i-1] != "\\"):
                in_string = not in_string
                continue
            if not in_string:
                if char == "{":
                    open_braces += 1
                elif char == "}":
                    open_braces = max(0, open_braces - 1)
                elif char == "[":
                    open_brackets += 1
                elif char == "]":
                    open_brackets = max(0, open_brackets - 1)
                    
        if in_string:
            s += '"'
        if open_brackets > 0:
            s += "]" * open_brackets
        if open_braces > 0:
            s += "}" * open_braces
        return s

    # ── System Prompt ────────────────────────────────────────

    def build_system_prompt(self) -> str:
        """
        Returns the Jarvis identity + structured output instructions.
        Loads from external Markdown file if available.
        """
        try:
            # Resolve path relative to this file
            prompt_path = Path(__file__).parent / "prompts" / "system_instructions.md"
            if prompt_path.exists():
                return prompt_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"[LLMInterface] Failed to load external prompt: {e}")

        # Emergency Fallback (minimal identity)
        return (
            "You are Jarvis, a Windows desktop automation assistant.\n"
            "Output ONLY a valid JSON array of steps: [{\"skill\": \"name\", \"params\": {...}}]\n"
            "Available skills: open_app, close_app, navigate_location, click_element, "
            "type_text, press_key, set_volume, set_brightness, search_web, ask_user.\n"
        )

