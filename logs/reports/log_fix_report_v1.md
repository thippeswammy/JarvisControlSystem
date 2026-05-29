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
_______________________________________________

# Re-Analysis

# Main Good Improvements

## Fixed Correctly

### 1. Close Intent

Now correctly detected:

```text
'Close notepad' → intent=close_app
```

AND:

```text
Dispatching: close_app
SUCCESS: terminated
```

GOOD FIX.

---

### 2. Log Analysis Routing

Now works:

```text
'Analyze the logs' → intent=log_analysis
```

GOOD FIX.

---

### 3. Planner Leak Fixed

No raw planner JSON shown anymore.

GOOD FIX.

---

# Remaining Critical Problems

# 1. Massive Timeout Problem

This is now your BIGGEST issue.

Almost every action succeeds BUT test times out.

Example:

```text
Launched: notepad.exe
```

then:

```text
TIMEOUT after 15s
```

Same for:

* open
* type
* close

---

## Root Cause

Actions execute correctly.

BUT:

* scenario validator
* completion callback
* async state update
* success signal

is delayed or never returned.

---

## Evidence

Action completed BEFORE timeout:

```text
17:55:42 launched
17:55:47 timeout
```

So executor works.

Test framework never receives completion state.

---

# 2. Ollama Failure Is Breaking System Stability

Repeated:

```text
Failed to connect to Ollama
WinError 10061
```

This is affecting:

* semantic memory
* orchestration speed
* routing latency
* test timings

---

## Current Behavior

Every command:

```text
try embedding
↓
fail
↓
auto-start
↓
retry
↓
continue
```

This wastes ~4 seconds EACH step.

---

## Fix Needed

When Ollama unavailable:

```python
disable_semantic_features_temporarily = True
```

DO NOT retry every command.

Use cooldown:

```python
next_retry_after = 60s
```

---

# 3. Cognitive Layer Still Dangerous

Still failing:

```text
Ok can open apps
→ open_app(ok can apps)
```

Critical issue remains.

---

## Root Cause

Mock LLM returning PLAN blindly.

No conversational classifier before planner.

---

## Needed

Before planner:

```python
if conversational_sentence:
    return chat_reply
```

NOT planner.

---

# 4. Quoted Block Protection Completely Broken

VERY IMPORTANT ISSUE.

Input:

```text
Summarize this: "open notepad and then close settings"
```

Should:

* summarize text only

Instead:

```text
Dispatching: open_app
```

VERY dangerous.

---

## Why

Quoted text still enters action parser.

System treats quoted payload as executable command.

---

## Needed Protection

```python
if inside_quotes:
    executable = False
```

OR:

```python
mode = SAFE_TEXT_ANALYSIS
```

This is critical for safety.

---

# 5. Type Intent Still Weak

Input:

```text
Type hello world into notepad
```

Detected as:

```text
intent=llm_route
```

Should be:

```text
intent=type_text
target=notepad
text=hello world
```

---

## Current Failure

Planner extracted:

```text
hello world into notepad
```

as typing content.

Wrong entity extraction.

---

# 6. Macro Learning Pollution

Dangerous learning:

```text
Learned new macro:
'Ok can open apps'
```

and:

```text
Searched and launched: ok can apps
```

BAD.

System is learning failures as successful macros.

---

## Needed

Only learn macro IF:

```python
intent_confidence > threshold
AND action_success == verified
AND user_not_confused
```

---

# 7. Wrong App Resolution

This is suspicious:

```text
'Open notebook'
→ app=jarviscontrolsystem
```

Then later launches notepad correctly.

Means:

* app matcher polluted
* semantic retrieval noisy
* alias ranking unstable

---

# 8. Mock Backend Is Causing False Positives

Logs:

```text
Skipping unhealthy backend
Requesting decision from mock
Mode identified: PLAN
```

Mock backend appears to:

* always return PLAN
* over-trigger actions

Very dangerous.

---

## Needed

Mock backend should ONLY:

```python
return CHAT
```

unless confidence high.

---

# Actual System State

# Working

* Skill execution
* App open
* App close
* Log analysis routing
* Planner isolation
* Intent detection improved
* Skill bus stable

---

# Broken

* Completion signaling
* Async test synchronization
* Conversational understanding
* Quote protection
* Semantic backend retry logic
* Macro learning safety
* Type-text entity parsing
* Mock LLM behavior

---

# Highest Priority Fixes

## Priority 1

Fix timeout/completion pipeline.

This is blocking ALL tests.

---

## Priority 2

Disable repeated Ollama retries.

Huge latency problem.

---

## Priority 3

Add quote safety protection.

Critical safety issue.

---

## Priority 4

Prevent conversational text from becoming actions.

---

# Most Dangerous Current Bug

THIS:

```text
Summarize this: "open notepad"
```

causing actual app launch.

That is your biggest safety problem now.
