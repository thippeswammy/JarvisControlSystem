"""
Chat Skill — Conversational AI Responses
=========================================
Handles general conversation, greetings, and questions that are NOT
OS-level commands. Routes directly to the LLM for a natural, short reply
and returns it to the user's interface (Telegram, voice, etc.).
"""

import logging
import re
import requests

from jarvis.skills.skill_decorator import skill
from jarvis.skills.skill_bus import SkillResult

logger = logging.getLogger(__name__)

_OLLAMA_URL = "http://localhost:11434/v1/chat/completions"
_MODEL = "gemma3:1b"
_CHAT_SYSTEM = (
    "You are JARVIS, a smart, friendly AI desktop assistant. "
    "Respond to the user naturally and concisely in 1-3 sentences. "
    "You help with Windows tasks and can also chat. "
    "Do NOT output JSON or code — just plain natural language."
)

_CANNED_RESPONSES = {
    "hi": "Hey! 👋 I'm JARVIS, your AI assistant. How can I help you today?",
    "hello": "Hello! 👋 Ready to assist. What do you need?",
    "hey": "Hey there! What can I do for you?",
    "thanks": "You're welcome! 😊 Anything else?",
    "thank you": "Happy to help! 😊",
    "thx": "No problem! 😊",
    "ty": "Anytime! 😊",
    "ok": "Got it! Let me know if you need anything.",
    "okay": "Got it! Let me know if you need anything.",
    "cool": "Glad you think so! 😄",
    "nice": "Thanks! 😄",
    "awesome": "Appreciate it! 😄",
    "great": "Great! Let me know what's next.",
    "got it": "Perfect! Let me know if you need anything else.",
    "sure": "Sure thing! What would you like me to do?",
    "alright": "Alright! 👍 What's next?",
}


def _llm_chat(user_message: str) -> str:
    """Ask Ollama for a conversational reply. Returns plain text."""
    try:
        payload = {
            "model": _MODEL,
            "messages": [
                {"role": "system", "content": _CHAT_SYSTEM},
                {"role": "user", "content": user_message},
            ],
            "max_tokens": 120,
            "temperature": 0.7,
            "stream": False,
        }
        resp = requests.post(_OLLAMA_URL, json=payload, timeout=10)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()
        # Remove any accidental JSON or markdown
        content = re.sub(r"```.*?```", "", content, flags=re.DOTALL).strip()
        return content or "I'm here! How can I help?"
    except Exception as e:
        logger.warning(f"[chat_skill] LLM chat failed: {e}")
        return "I'm here and ready to help! 😊 What do you need?"


@skill(
    triggers=["hi", "hello", "hey", "how are you", "what can you do", "who are you",
              "thanks", "thank you", "chat"],
    name="chat_reply",
    category="session",
    is_cognitive=True,   # Never auto-learned as a macro
)
def chat_reply(params: dict) -> SkillResult:
    """
    Conversational response skill. Called when the intent is 'chat'.
    Uses canned responses for simple greetings, LLM for richer questions.
    """
    text = params.get("text", params.get("raw", "")).strip().lower()
    logger.info(f"[chat_skill] Conversational input: {text!r}")

    # Fast-path: canned response for very common phrases
    reply = _CANNED_RESPONSES.get(text)

    # Slightly richer questions → LLM
    if not reply:
        reply = _llm_chat(text or "hello")

    return SkillResult(
        success=True,
        message=reply,
        action_taken="Conversational reply sent",
    )
