import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jarvis.llm.backends.local_llm import LocalLLM
import logging

logging.basicConfig(level=logging.INFO)

llm = LocalLLM(model="gemma3:4b")

# The problematic string from the log
problematic_raw = """✅ ```json
{"type": "plan", "steps": [{"skill": "navigate_location", "params": {"uri": "ms-settings:home"}}]}
```"""

decision = llm._parse_decision(problematic_raw)

print(f"--- TEST 1: Markdown JSON block ---")
print(f"Type: {decision.type}")
if decision.steps:
    print(f"Steps: {decision.steps}")
else:
    print(f"Message: {decision.message}")

# Test 2: Malformed JSON that should be cleaned
malformed_raw = """I have a plan for you:
```json
{
  "type": "chat",
  "message": "Hello world"
}
```
Hope you like it!"""

decision2 = llm._parse_decision(malformed_raw)
print(f"\n--- TEST 2: Mixed text and JSON ---")
print(f"Type: {decision2.type}")
print(f"Message: {decision2.message}")

# Test 3: Failed parsing but stripped markdown
failed_raw = """```json
{"malformed": "json"
```"""
decision3 = llm._parse_decision(failed_raw)
print(f"\n--- TEST 3: Failed JSON (should strip markdown) ---")
print(f"Type: {decision3.type}")
print(f"Message: {decision3.message}")
