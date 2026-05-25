# Pure LLM Brain — Complete Architecture Redesign

## Vision

> **The LLM is the only brain. It sees everything, decides everything.**

No hardcoded rules. No regex classifiers. No canned responses. No dual-brain conflict.  
Every user message goes to the LLM. The LLM decides if it should talk, act, do both, or ask. The system is fully scalable — adding a new skill means the LLM automatically knows how to use it (via skill catalog injection).

---

## What Gets Removed

| Component | Status | Why |
|---|---|---|
| `nlu.py` intent patterns | **DELETED** | LLM is a far better classifier |
| Canned responses in `chat_skill.py` | **DELETED** | LLM writes better responses |
| `_DIRECT_MAP` in `planner.py` | **DELETED** | LLM handles all routing |
| `chat` intent in NLU patterns | **DELETED** | LLM owns this |
| Fast-lane NLU (volume, power, etc.) | **MINIMISED** | Only keep absolute safety-critical triggers (`shutdown`, `restart`, `sleep`) as a guard — everything else goes LLM |

---

## New Architecture Flow

```
User Message (Telegram / Voice / Text)
         │
         ▼
 [Telegram Adapter]
  • Send "typing..." indicator immediately
         │
         ▼
 [Context Assembler]  ← runs while LLM is thinking
  • Live UI Snapshot  (UIInspector)
  • State Provenance  (EpisodicMemory lineage)
  • User Preferences  (PreferenceRouter)
  • Episodic History  (last 3 sessions)
  • Skill Catalog     (all registered skills + descriptions + params)
         │
         ▼
 [LLM Unified Brain]
  • Receives full context block + user message
  • Decides ONE of:
    ┌─────────────────────────────────────────────────┐
    │  "chat"    → reply conversationally              │
    │  "plan"    → execute one or more skills          │
    │  "mixed"   → reply AND execute skills together   │
    │  "clarify" → ask user for missing information    │
    └─────────────────────────────────────────────────┘
         │
         ▼
 [Response Dispatcher]
  • "chat"    → send message text back to user
  • "plan"    → execute skills via SkillBus, send result
  • "mixed"   → send message text first, then execute skills
  • "clarify" → send question back to user, await response
         │
         ▼
 [Telegram Reply] + [EpisodicMemory log] + [Macro Learner]
```

---

## Core Design: The Unified LLM Contract

The LLM is given a **structured contract** via its system prompt. The contract defines:

### 1. What Context It Receives (Input Block)
Every message to the LLM is assembled with these sections:
- `[System Preferences]` — OS, browser, email, terminal (from `preferences.yaml`)
- `[Current UI State]` — Active app, page title, nav items, visible buttons (from `UIInspector`)
- `[State Provenance]` — Who/what caused the current state (USER navigated / JARVIS executed)
- `[Episodic Memory]` — Recent successful commands (from `EpisodicMemory.as_llm_context()`)
- `[Available Skills]` — Full catalog: name + description + params of every skill registered in `SkillBus`
- `[User Message]` — The raw message from the user

### 2. What It Must Return (Output Contract)
The LLM MUST always return a single JSON object. It is never allowed to return plain text.

**Response Type A — Chat:**
```
{ "type": "chat", "message": "Hey! I'm JARVIS..." }
```

**Response Type B — Plan:**
```
{ "type": "plan", "steps": [ {"skill": "open_app", "params": {"target": "settings"}} ] }
```

**Response Type C — Mixed (Talk + Act):**
```
{ "type": "mixed", "message": "Sure! Opening Settings for you.", "steps": [...] }
```

**Response Type D — Clarify:**
```
{ "type": "clarify", "question": "Which display do you want to change?" }
```

### 3. Decision Rules (Baked into System Prompt)
The system prompt instructs the LLM exactly when to choose each type:
- If the user is **greeting, asking general questions, saying thanks** → always `chat`
- If the user wants **something done on the OS** → `plan`
- If the user wants something done **AND** it makes sense to acknowledge → `mixed`
- If the user's request is **ambiguous or missing a key parameter** → `clarify`
- **NEVER** invent skill names — only use skills from the `[Available Skills]` catalog
- **NEVER** return plain text — always a valid JSON object

---

## Component-by-Component Changes

### Component 1: Skill Catalog Injection (New)
**File: `jarvis/skills/skill_bus.py`**

Add a `get_skill_catalog()` method that returns a compact, LLM-readable string listing all registered skills with their name, trigger description, and parameter schema. This is injected into every LLM prompt so the LLM always knows *exactly* what actions are available.

Example output:
```
- open_app(target): Opens an application by name. Use for: "open notepad", "launch chrome"
- set_volume(level, action, mute): Controls system volume. Use for: "set volume 50", "mute"
- navigate_location(target, uri): Navigates within an app. Use for: "go to display settings"
- chat_reply(message): Send a conversational reply. Use for: any non-action response
```

---

### Component 2: Unified LLM Brain (New Method)
**File: `jarvis/llm/backends/local_llm.py`**

Replace the current `plan()` method with `decide()` — a new method that:
1. Builds the full context block (preferences + UI state + episodic memory + skill catalog + user message)
2. Sends to Ollama
3. Parses the response into one of the 4 response types
4. Returns a typed result object: `LLMDecision(type, message, steps, question)`

The `build_system_prompt()` is completely rewritten to implement the Output Contract above.

The JSON parser is made even more robust — trying multiple extraction strategies and never returning `None` silently (always logs what it received vs what it expected).

---

### Component 3: NLU — Stripped to Safety-Only
**File: `jarvis/perception/nlu.py`**

Keep ONLY:
- `session_activate` pattern ("hi jarvis", "wake up jarvis", "hello jarvis")
- `session_deactivate` pattern ("bye jarvis", "stop jarvis")
- Safety power commands: `shutdown`, `restart`, `sleep` (these are irreversible, we don't want an LLM hallucination to trigger them)

Everything else → intent becomes `"llm_route"`.

This means NLU is now purely a **safety gate**, not a classifier. The LLM classifies everything.

---

### Component 4: Planner — Unified Dispatcher
**File: `jarvis/brain/planner.py`**

- Remove `_DIRECT_MAP` (no more hardcoded routing)
- Remove `_plan_via_llm()` (replaced by new unified approach)
- Add `_plan_via_unified_llm()` which calls `LLMRouter.decide()` and converts the `LLMDecision` into a plan:
  - `chat` → single `chat_reply` skill call with the message pre-filled
  - `plan` → list of skill calls
  - `mixed` → `chat_reply` first, then the skill calls
  - `clarify` → single `ask_user` skill call with the question pre-filled

---

### Component 5: Telegram Typing Indicator
**File: `jarvis/input/adapters.py`** (TelegramAdapter)

When a message is received:
1. Immediately call `bot.send_chat_action(chat_id, "typing")` before dispatching to Orchestrator
2. Telegram shows "JARVIS is typing..." for up to 5 seconds automatically
3. For long LLM calls, re-send the typing action every 4 seconds in a background thread until the response is ready

---

### Component 6: LLM Router — Update `route()` to `decide()`
**File: `jarvis/llm/llm_router.py`**

- Add `decide(prompt, context)` method alongside existing `route()`
- `decide()` tries backends in order, returns `LLMDecision`
- Falls back gracefully: if all backends fail → `LLMDecision(type="chat", message="Sorry, my brain is offline right now.")`
- Remove the mock backend's "always return open_app" behaviour — mock should return a sensible chat reply instead

---

### Component 7: Chat Reply Skill — Pure Pass-Through
**File: `jarvis/skills/builtins/chat_skill.py`**

Completely rewritten to be a pure pass-through:
- Receives `params["message"]` (the LLM-generated reply text)
- Returns it as `SkillResult(success=True, message=params["message"])`
- No canned responses, no internal LLM call — the LLM Unified Brain already decided the text
- Still marked `is_cognitive=True` so never auto-learned as macro

---

### Component 8: Orchestrator — Wire Typing Indicator
**File: `jarvis/brain/orchestrator.py`**

- Accept an optional `typing_callback` parameter in `process()`
- Telegram adapter passes `lambda: bot.send_chat_action(...)` as the callback
- Orchestrator calls it right before invoking the planner

---

## Data Flow Example: "Hi"

```
User: "Hi"
  → TelegramAdapter: send "typing..." to Telegram
  → Orchestrator.process("Hi")
  → NLU: no pattern match → intent = "llm_route"
  → Context Assembler: builds full context block
  → LLM: receives context + "Hi"
  → LLM decides: {"type": "chat", "message": "Hey! 👋 What can I do for you today?"}
  → Planner: creates SkillCall(skill="chat_reply", params={"message": "Hey! 👋 ..."})
  → SkillBus: executes chat_reply → SkillResult(message="Hey! 👋 ...")
  → TelegramAdapter: sends "Hey! 👋 What can I do for you today?" to user
```

## Data Flow Example: "Open Settings"

```
User: "Open Settings"
  → TelegramAdapter: send "typing..." to Telegram
  → Orchestrator.process("Open Settings")
  → NLU: no pattern match → intent = "llm_route"
  → LLM: receives context (UI shows desktop) + "Open Settings"
  → LLM decides: {"type": "plan", "steps": [{"skill": "open_app", "params": {"target": "settings"}}]}
  → Planner: creates [SkillCall(skill="open_app", params={"target": "settings"})]
  → SkillBus: executes open_app → opens Settings
  → Macro Learner: saves "open settings" → open_app(settings) macro
```

## Data Flow Example: "Open Spotify and play something relaxing"

```
User: "Open Spotify and play something relaxing"
  → LLM decides: {
      "type": "mixed",
      "message": "Opening Spotify for you! I can't control playback directly yet, but I'll get it open.",
      "steps": [{"skill": "open_app", "params": {"target": "spotify"}}]
    }
  → Planner: chat_reply first, then open_app
  → User sees: "Opening Spotify for you! I can't control playback directly yet..."
  → Spotify opens
```

---

## Verification Plan

Send these from Telegram in order after implementation:

| Message | Expected Response Type | Expected Behaviour |
|---|---|---|
| `Hi` | `chat` | Friendly greeting from LLM |
| `How are you?` | `chat` | Natural LLM reply |
| `What can you do?` | `chat` | LLM lists capabilities from skill catalog |
| `Open Settings` | `plan` | Settings opens |
| `Set volume to 50` | `plan` | Volume set |
| `Open Notepad and say hello` | `mixed` | LLM replies + Notepad opens |
| `Open the display settings` | `plan` | Navigates to display |
| `shutdown` | `session/safety gate` | Asks to confirm first |
| `What time is it?` | `chat` | LLM answers conversationally |
| `Take a screenshot` | `clarify` or `plan` | LLM decides |

---

> [!IMPORTANT]
> **One Dependency Change**: The Telegram adapter needs `python-telegram-bot` typing action support. This is already in the existing library — just a new API call.

> [!NOTE]
> **Backward Compatibility**: The existing `plan()` method in `LLMRouter` stays as-is for now. The new `decide()` method is additive. We can migrate fully once tested.
