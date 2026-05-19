# Problems

* Close commands launch apps instead of closing them
* Planner JSON exposed to user
* Conversational text treated as app names
* Log analysis requests not routed correctly
* Compound/multiline prompts split incorrectly
* Capability questions answered with unrelated context
* Automation agent typed unexpectedly
* Weak fallback/error responses
* No confirmation for system actions
* Synonym handling inconsistent (`notebook` vs `notepad`)

# Common Root Problems

* Weak intent classification
* Missing action-priority hierarchy
* No separation between planner/executor/response
* Fallback launcher triggers too aggressively
* Poor multiline/quoted-text parsing
* Context memory injected incorrectly
* Missing natural-language aliases for commands
* No safety gating for automation actions

# What Needs To Happen

## Intent Pipeline

Correct order:

```text
Conversation
→ Slash/System Command
→ Desktop Action
→ Tool Action
→ Fallback
```

---

## Planner Isolation

Never show:

```json
{"type":"plan","steps":[...]}
```

Instead:

```text
[OK] Opened Notepad
```

---

## Better Parsing

Treat quoted/multiline logs as one payload:

```python
if quoted_block:
    preserve_as_single_input()
```

---

## Strong Verb Detection

Examples:

```text
open notepad  → OPEN_APP
close notepad → CLOSE_APP
```

NOT default launch behavior.

---

## Better Fallbacks

Instead of:

```text
I don't know how to handle...
```

Use:

```text
Log analysis module not connected yet.
```

---

## Conversational Understanding

Do not app-search for normal conversation:

```text
Ok can open apps
```

Should respond conversationally.

---

## Synonym Normalization

```python
{
  "notebook": "notepad",
  "settings": "windows settings"
}
```

---

## Safe Automation

Before typing/clicking:

* validate target
* confirm active window
* confirm intent

---

## Needed Features

* Intent confidence scoring
* Tool routing aliases
* Conversation memory filtering
* Action confirmation layer
* Structured error handling
