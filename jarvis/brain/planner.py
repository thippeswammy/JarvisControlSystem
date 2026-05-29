"""
Planner
=======
Converts a PerceptionPacket into an executable Plan (list of SkillCalls).

Decision priority:
    1. Memory recall (A* path or fuzzy trigger match)
    2. Rule-based fast-map (session, volume, brightness — no LLM needed)
    3. LLM Router (Ollama → tunneled → mock)

For compound commands, each sub-command is planned independently.
"""

import logging
from typing import Optional

from jarvis.llm.llm_router import LLMRouter
from jarvis.llm.llm_interface import SkillCallSpec, Plan
from jarvis.brain.preference_router import PreferenceRouter
from jarvis.memory.memory_manager import MemoryManager, MemoryPath
from jarvis.perception.perception_packet import PerceptionPacket, Utterance
from jarvis.skills.skill_bus import SkillCall, SkillBus

logger = logging.getLogger(__name__)


class Planner:
    """
    Converts PerceptionPacket → list[SkillCall] (the Plan).

    Usage:
        planner = Planner(memory, router)
        plan = planner.plan(packet)
        for call in plan:
            bus.dispatch(call)
    """

    def __init__(self, memory: MemoryManager, router: LLMRouter, bus: SkillBus, agent_bus=None, mcp_bus=None):
        self._memory = memory
        self._router = router
        self._bus = bus
        self._agent_bus = agent_bus
        self._mcp_bus = mcp_bus
        self._preference_router = PreferenceRouter()

    def plan(self, packet: PerceptionPacket, react_history: list[dict] = None) -> list[SkillCall]:
        """Convert PerceptionPacket → ordered list of SkillCalls."""

        # Compound command: send the FULL original sentence to the LLM in ONE call.
        # This is better than splitting because:
        #   - The LLM understands the whole sentence in context
        #   - "write about the Ai" makes sense only when LLM sees the full command
        #   - Results in one LLM call instead of N calls
        if packet.compound and packet.sub_commands:
            full_text = packet.utterance.text  # The original un-split full sentence
            logger.info(f"[Planner] Compound → single LLM call: {full_text!r}")
            compound_packet = PerceptionPacket(
                utterance=packet.utterance,
                intent="llm_route",
                entities={"raw": full_text},
                app_context=packet.app_context,
                memory_context=packet.memory_context,
            )
            compound_packet.context_snapshot = packet.context_snapshot
            compound_packet.override_prompt = full_text
            return self._plan_single(compound_packet, snapshot=packet.context_snapshot, react_history=react_history)

        return self._plan_single(packet, snapshot=packet.context_snapshot, react_history=react_history)

    def _plan_single(self, packet: PerceptionPacket, snapshot=None, react_history: list[dict] = None) -> list[SkillCall]:
        # 0. Check safe mode for quoted blocks or text analysis
        if getattr(packet, "safe_mode", False):
            logger.info(f"[Planner] Safe mode active for: {packet.text!r}")
            return [SkillCall(
                skill="chat_reply",
                params={"message": f"I've analyzed the text, but since it is inside a cognitive text analysis query, I won't execute any commands. Text: '{packet.text}'"}
            )]

        # 1. Direct map (safety/session intents based on Skill registry)
        if self._bus.is_fast_path_eligible(packet.intent) and (packet.intent_category == "EXECUTION" or packet.intent == "chat_reply"):
            logger.info(f"[Planner] Direct map bypass for intent: {packet.intent}")
            # Ensure text is in entities if not present (useful for chat_reply)
            params = packet.entities.copy()
            if "text" not in params and packet.text:
                params["text"] = packet.text
            return [SkillCall(skill=packet.intent, params=params)]

        # 2. Pre-built plan from memory recall (pathfinder result)
        if packet.raw_plan_override:
            logger.info("[Planner] Using memory recall plan")
            return packet.raw_plan_override

        # 3. Unknown intent / all others → LLM Unified Router
        logger.info(f"[Brain] Routing to cognitive layer for intent: {packet.intent!r}")
        return self._plan_via_unified_llm(packet, snapshot=snapshot, react_history=react_history)

    def _plan_open_app(self, packet: PerceptionPacket) -> list[SkillCall]:
        target = packet.entities.get("target", "")
        sub = packet.sub_location or packet.entities.get("sub_location", "")

        calls = [SkillCall(skill="open_app", params={"target": target})]

        if sub:
            # Try memory recall for sub-location navigation
            mem_path = self._memory.recall(
                f"navigate {sub}",
                app_id=target if target != "settings" else "settings",
            )
            if mem_path:
                calls.extend(self._path_to_skill_calls(mem_path))
            else:
                # Fallback: Use LLM to figure out the navigation steps
                logger.info(f"[Planner] Sub-location {sub!r} unknown — routing to LLM")
                sub_packet = PerceptionPacket(
                    utterance=Utterance(
                        text=f"navigate to {sub} in {target}",
                        source=packet.utterance.source
                    ),
                    intent="navigate_location",
                    entities={"target": sub, "app": target},
                    app_context=target,
                    memory_context=packet.memory_context,
                )
                calls.extend(self._plan_via_llm(sub_packet))

        return calls

    def _plan_navigate(self, packet: PerceptionPacket) -> list[SkillCall]:
        target = packet.entities.get("target", "")
        app_id = packet.app_context or "settings"

        # Try memory recall
        mem_path = self._memory.recall(
            f"navigate {target}",
            app_id=app_id,
        )
        if mem_path:
            return self._path_to_skill_calls(mem_path)

        # Fallback skill call
        return [SkillCall(skill="navigate_location", params={"target": target})]

    def _get_os_desktop_state(self) -> str:
        try:
            import win32gui
            from pywinauto import Desktop
            
            hwnd = win32gui.GetForegroundWindow()
            fore_title = win32gui.GetWindowText(hwnd)
            
            # Enumerate open windows and modal dialogs
            windows = Desktop(backend="uia").windows()
            open_wins = []
            modal_popups = []
            
            for win in windows:
                try:
                    title = win.window_text().strip()
                    if title:
                        open_wins.append(title)
                        # Identify potential modal child dialogs
                        for child in win.children():
                            if child.control_type() == "Window":
                                c_title = child.window_text().strip()
                                if c_title:
                                    modal_popups.append(f"{c_title} (child of {title})")
                except:
                    continue
            
            state_desc = f"Active Foreground Window: \"{fore_title}\"\n"
            if open_wins:
                state_desc += f"Open Application Windows: {open_wins}\n"
            if modal_popups:
                state_desc += f"Active Dialogs/Popups detected: {modal_popups}\n"
            else:
                state_desc += "Active Dialogs/Popups detected: None\n"
            return state_desc
        except Exception as e:
            return f"OS Desktop State Error: {e}"

    def _plan_via_unified_llm(self, packet: PerceptionPacket, snapshot=None, react_history: list[dict] = None) -> list[SkillCall]:
        # Context enrichment for LLM
        system_ctx = self._preference_router.get_system_context()
        ui_ctx = "UI State: Unknown"
        lineage_ctx = "State reached by: UNKNOWN"

        if snapshot:
            if snapshot.ui_snapshot:
                ui_ctx = snapshot.ui_snapshot.to_llm_context()
            if snapshot.state_origin:
                lineage_ctx = f"State reached by: {snapshot.state_origin} — '{snapshot.prior_action}'"

        skill_catalog = self._bus.get_skill_catalog()
        episodic_context = packet.memory_context or "No recent memory."

        mcp_catalog = ""
        if self._mcp_bus:
            mcp_catalog = self._mcp_bus.get_tool_catalog()

        agent_catalog = ""
        if self._agent_bus:
            agent_catalog = self._agent_bus.get_agent_catalog()

        active_app_ctx = "None"
        if snapshot:
            active_app_ctx = f"Application Name: \"{snapshot.active_app}\"\nWindow Title: \"{snapshot.active_window_title}\""

        os_desktop_ctx = self._get_os_desktop_state()
        
        react_history_ctx = "No preceding steps in this turn."
        if react_history:
            react_history_ctx = "\n".join(
                f"- Step {i+1}: {step.get('skill')}({ {k: v for k, v in step.get('params', {}).items() if not k.startswith('_')} }) -> {'SUCCESS' if step.get('success') else 'FAILED'}"
                f"{' (' + step.get('message') + ')' if step.get('message') else ''}"
                for i, step in enumerate(react_history)
            )

        enriched_context = (
            f"[Active Foreground Window]\n{active_app_ctx}\n\n"
            f"[OS Desktop State]\n{os_desktop_ctx}\n\n"
            f"[Execution History in Current Turn]\n{react_history_ctx}\n\n"
            f"[System Preferences]\n{system_ctx}\n\n"
            f"[Current UI State]\n{ui_ctx}\n\n"
            f"[State Provenance]\n{lineage_ctx}\n\n"
            f"[Episodic Memory]\n{episodic_context}\n\n"
            f"[Available Skills]\n{skill_catalog}\n\n"
        )
        if mcp_catalog:
            enriched_context += f"[Available MCP Tools]\n{mcp_catalog}\n\n"
        if agent_catalog:
            enriched_context += f"[Available Agents]\n{agent_catalog}\n\n"

        enriched_context += (
            "[Critical Rules]\n"
            "1. META-RULE: If the user intent involves content generation (explaining, summarizing, drafting, jokes) AND a destination application is specified OR active, you MUST deliver that content using 'type_text' into the target app. Do NOT use the 'message' field for the payload.\n"
            "2. CONTEXT-AWARENESS: If an app is already active and the user says 'write a summary', target that active app.\n"
            "3. CONVERSATIONAL: If the input is conversational (e.g. 'Ok can open apps', 'thanks'), respond conversationally and do NOT assume app launching or actions.\n"
            "4. CAPABILITY: If asked about capabilities, list the [Available Skills] concisely.\n"
            "5. AUTONOMOUS AGENTS: If the task requires deep reasoning, multi-step sub-tasks, or running complex background logic, you may delegate to a sub-agent using type: 'agent' or 'multiagent'.\n"
            "6. MCP TOOLS: If the task requires external tools (like reading files, web search, etc.) which are listed in [Available MCP Tools], you can use type: 'mcp' to call them directly.\n\n"
            "[Examples]\n"
            'User: "open notepad" → {{"type":"plan","steps":[{{"skill":"open_app","params":{{"target":"notepad"}}}}]}}\n'
            'User: "write a python hello world in vscode" → {{"type":"plan","steps":[{{"skill":"open_app","params":{{"target":"vscode"}}}},{{"skill":"type_text","params":{{"text":"print(\'hello world\')"}}]}}\n'
            'User: "summarize the news in word" → {{"type":"plan","steps":[{{"skill":"open_app","params":{{"target":"word"}}}},{{"skill":"type_text","params":{{"text":"The main news today is..."}}]}}\n'
            'User: "search youtube for funny cats" → {{"type":"plan","steps":[{{"skill":"open_app","params":{{"target":"chrome"}}}},{{"skill":"type_text","params":{{"text":"funny cats"}},{{"skill":"press_key","params":{{"key":"enter"}}]}}\n'
            'User: "tell a joke in slack" → {{"type":"plan","steps":[{{"skill":"open_app","params":{{"target":"slack"}}}},{{"skill":"type_text","params":{{"text":"Why did the AI cross the road? To get to the other dataset."}}]}}\n'
            'User: "close settings and open notepad and type hello" → {{"type":"plan","steps":[{{"close_app","params":{{"target":"settings"}}}},{{"open_app","params":{{"target":"notepad"}}}},{{"type_text","params":{{"text":"hello"}}}}]}}\n'
            'User: "type status in notepad and save as report.txt" → {{"type":"plan","steps":[{{"skill":"open_app","params":{{"target":"notepad"}}}},{{"skill":"type_text","params":{{"text":"status"}}}},{{"skill":"press_key","params":{{"key":"ctrl+s"}}}},{{"skill":"type_text","params":{{"text":"report.txt"}}}},{{"skill":"press_key","params":{{"key":"enter"}}}}]}}\n'
            'User: "ask search_agent to search for python tutorials" → {{"type":"agent","agent":"search_agent","agent_task":"search for python tutorials"}}\n'
            'User: "use filesystem to read_file notes.txt" → {{"type":"mcp","mcp_server":"filesystem","mcp_tool":"read_file","mcp_params":{{"path":"notes.txt"}}}}\n'
        )

        # Use override prompt if compound command prepared one
        prompt = packet.override_prompt or packet.text

        logger.info(f"[Cognitive] Requesting decision from LLM backend...")
        decision = self._router.decide(
            prompt=prompt,
            context=enriched_context,
        )

        if not decision:
            logger.error("[Cognitive] LLM failed to provide a valid response.")
            return [SkillCall(skill="chat_reply", params={"message": "I'm sorry, I failed to generate a response."})]

        logger.info(f"[Decision] LLM response mode identified: {decision.type.upper()}")
        calls = []
        
        # 1. Chat
        if decision.type == "chat":
            if decision.message:
                calls.append(SkillCall(skill="chat_reply", params={"message": decision.message}))
                
        # 2. Plan
        elif decision.type == "plan":
            if decision.steps:
                for s in decision.steps:
                    calls.append(SkillCall(skill=s.skill, params=s.params, source="llm"))
                    
        # 3. Mixed
        elif decision.type == "mixed":
            if decision.message:
                calls.append(SkillCall(skill="chat_reply", params={"message": decision.message}))
            if decision.steps:
                for s in decision.steps:
                    calls.append(SkillCall(skill=s.skill, params=s.params, source="llm"))
                    
        # 4. Clarify
        elif decision.type == "clarify":
            if decision.question:
                calls.append(SkillCall(skill="ask_user", params={"question": decision.question}))

        # 5. Agent
        elif decision.type == "agent":
            if decision.agent and decision.agent_task:
                calls.append(SkillCall(
                    skill="run_agent",
                    params={
                        "agent": decision.agent,
                        "task": decision.agent_task,
                        "_agent_bus": self._agent_bus,
                        "_router": self._router
                    },
                    source="llm"
                ))

        # 6. Multiagent
        elif decision.type == "multiagent":
            if decision.agent_tasks:
                calls.append(SkillCall(
                    skill="run_agent_pipeline",
                    params={
                        "tasks": decision.agent_tasks,
                        "_agent_bus": self._agent_bus,
                        "_router": self._router
                    },
                    source="llm"
                ))

        # 7. MCP
        elif decision.type == "mcp":
            if decision.mcp_server and decision.mcp_tool:
                calls.append(SkillCall(
                    skill="call_mcp_tool",
                    params={
                        "server": decision.mcp_server,
                        "tool": decision.mcp_tool,
                        "params": decision.mcp_params or {},
                        "_mcp_bus": self._mcp_bus
                    },
                    source="llm"
                ))

        # Safety fallback
        if not calls:
            logger.warning(f"[Planner] Decision generated no calls: {decision}")
            if packet.intent == "log_analysis":
                fallback_msg = "Log analysis module not connected yet."
            else:
                fallback_msg = "I'm not quite sure how to handle that context right now."
            calls.append(SkillCall(skill="chat_reply", params={"message": fallback_msg}))
            
        return calls

    @staticmethod
    def _path_to_skill_calls(path: MemoryPath) -> list[SkillCall]:
        """Convert a MemoryPath into executable SkillCalls."""
        calls = []
        for edge in path.edges:
            if getattr(edge, "action_type", "") == "macro":
                import json
                try:
                    # Generic macros store serialized SkillCalls in action_params["calls"]
                    serialized_calls = edge.action_params.get("calls", [])
                    if isinstance(serialized_calls, str):
                        serialized_calls = json.loads(serialized_calls)
                    
                    for call_dict in serialized_calls:
                        calls.append(SkillCall(
                            skill=call_dict.get("skill", "unknown"),
                            params=call_dict.get("params", {}),
                            source="memory"
                        ))
                except Exception as e:
                    logger.error(f"[Planner] Failed to deserialize macro edge {edge.id}: {e}")
            elif edge.fast_path == "uri":
                calls.append(SkillCall(
                    skill="navigate_location",
                    params={"uri": edge.fast_path_value, "target": edge.to_id},
                    source="memory",
                ))
            elif edge.steps:
                calls.append(SkillCall(
                    skill="navigate_location",
                    params={"steps": edge.steps, "target": edge.to_id},
                    source="memory",
                ))
        return calls
