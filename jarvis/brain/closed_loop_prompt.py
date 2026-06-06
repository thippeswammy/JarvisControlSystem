"""
Closed-Loop Prompt Builder
==========================
Constructs the specialized system prompt for closed-loop LLM calls.
Distinct from the planner's prompt — this includes execution history,
world-state diffs, and a structured response schema with explicit
DONE/IN_PROGRESS/BLOCKED status signals.
"""

import logging

logger = logging.getLogger(__name__)


def build_closed_loop_system_prompt() -> str:
    """
    Returns the system prompt for closed-loop execution.
    This prompt enforces the LLM to return a structured JSON
    with an explicit status signal.
    """
    return (
        "You are JARVIS, an advanced AI desktop assistant executing a user's goal autonomously.\n"
        "You are inside a CLOSED-LOOP execution cycle. The system will keep calling you until the goal is complete.\n"
        "\n"
        "RESPONSE FORMAT — You MUST return a SINGLE valid JSON object matching ONE of these schemas:\n"
        "\n"
        '1. Actions needed (goal not yet complete):\n'
        '   {"status": "in_progress", "reasoning": "brief explanation of what to do next", '
        '"actions": [{"skill": "skill_name", "params": {...}}]}\n'
        "\n"
        '2. Goal complete (all tasks done):\n'
        '   {"status": "done", "reasoning": "why the goal is complete", "summary": "what was accomplished"}\n'
        "\n"
        '3. Blocked (cannot proceed without help):\n'
        '   {"status": "blocked", "reasoning": "why blocked", "block_reason": "description of the issue", "question": "specific context-aware clarification question to ask the user"}\n'
        "\n"
        "CRITICAL RULES:\n"
        "1. Return ONLY valid JSON. No markdown, no explanations outside the JSON.\n"
        "2. Check the [Execution History] carefully. Do NOT repeat actions that already SUCCEEDED.\n"
        "3. If all parts of the goal are already done (visible in execution history), return status='done'.\n"
        "4. If a previous action FAILED, try an alternative approach — do NOT blindly retry the same thing.\n"
        "5. Return at most 3-5 actions per iteration. The system will call you again after executing them.\n"
        "6. Only use skills listed in [Available Skills].\n"
        "7. When the user's request involves content generation AND a target app, use 'type_text' to deliver content.\n"
        "8. For 'chat_reply' responses (conversational answers with no desktop action), use status='done' with the message in 'summary'.\n"
        "9. When blocked or needing clarification, write a direct, context-aware clarification question in the 'question' field so that Jarvis can ask the user directly.\n"
    )


def build_closed_loop_context(
    goal: str,
    execution_history: str,
    world_state: str,
    world_diff: str,
    skill_catalog: str,
    active_app_ctx: str,
    os_desktop_ctx: str,
    system_preferences: str,
    episodic_memory: str,
    mcp_catalog: str = "",
    agent_catalog: str = "",
    iteration: int = 1,
    max_iterations: int = 10,
) -> str:
    """
    Build the full context block for a closed-loop LLM call.
    
    This is injected as a system message alongside the closed-loop system prompt.
    """
    ctx = (
        f"[User Goal]\n{goal}\n\n"
        f"[Loop Progress]\nIteration {iteration}/{max_iterations}\n\n"
        f"[Execution History]\n{execution_history}\n\n"
        f"[World State Changes Since Last Step]\n{world_diff}\n\n"
        f"[Current World State]\n{world_state}\n\n"
        f"[Active Foreground Window]\n{active_app_ctx}\n\n"
        f"[OS Desktop State]\n{os_desktop_ctx}\n\n"
        f"[System Preferences]\n{system_preferences}\n\n"
        f"[Episodic Memory]\n{episodic_memory}\n\n"
        f"[Available Skills]\n{skill_catalog}\n\n"
    )
    if mcp_catalog:
        ctx += f"[Available MCP Tools]\n{mcp_catalog}\n\n"
    if agent_catalog:
        ctx += f"[Available Agents]\n{agent_catalog}\n\n"
    
    return ctx
"""Module: closed_loop_prompt.py — Prompt builder for the closed-loop engine."""
