"""
Message Formatter
=================
Converts a list of SkillResults into a cohesive, persona-driven message
for Telegram or CLI output.
"""

from typing import List
from jarvis.skills.skill_bus import SkillResult

class MessageFormatter:
    """
    Crafts "good" messages for testing and production.
    Ensures persona consistency and clear action feedback.
    """

    @staticmethod
    def format(results: List[SkillResult], source: str = "telegram") -> str:
        if not results:
            return "🤖 **JARVIS**: I'm sorry, I encountered an error processing that request."

        # Find the primary message (usually from chat_reply or ask_user)
        primary_msg = ""
        actions = []
        all_success = True

        for res in results:
            if not res.success:
                all_success = False
            
            # If it's a conversational skill, take its message as primary
            if res.skill_name in ("chat_reply", "ask_user"):
                primary_msg = res.message
            else:
                # Accumulate action feedback
                action_text = res.message or res.action_taken
                if action_text:
                    status_icon = "✅" if res.success else "❌"
                    actions.append(f"{status_icon} *{action_text}*")

        # Start building the response
        response_lines = []
        
        # Header (Optional: only if it's a complex response)
        # response_lines.append("🤖 **JARVIS**")

        if primary_msg:
            response_lines.append(f"🤖 {primary_msg}")
        
        if actions:
            # If we have a primary message, add a small gap
            if primary_msg:
                response_lines.append("")
            
            response_lines.extend(actions)

        # Safety fallback
        if not response_lines:
            last = results[-1]
            icon = "✅" if last.success else "❌"
            return f"{icon} {last.message or last.action_taken}"

        return "\n".join(response_lines)
