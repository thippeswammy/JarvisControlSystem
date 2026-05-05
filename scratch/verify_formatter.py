import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jarvis.brain.message_formatter import MessageFormatter
from jarvis.skills.skill_bus import SkillResult

results = [
    SkillResult(success=True, skill_name="chat_reply", message="Certainly. I'm opening Notepad now to draft that summary for you."),
    SkillResult(success=True, skill_name="open_app", action_taken="Launched and focused notepad"),
    SkillResult(success=True, skill_name="type_text", action_taken="Typed text about AI"),
]

formatted = MessageFormatter.format(results)
print("--- FORMATTED RESPONSE ---")
print(formatted)
print("--------------------------")

error_results = [
    SkillResult(success=True, skill_name="chat_reply", message="I'll try to open that app."),
    SkillResult(success=False, skill_name="open_app", message="App 'unknown' not found"),
]

formatted_err = MessageFormatter.format(error_results)
print("\n--- ERROR RESPONSE ---")
print(formatted_err)
print("--------------------------")
