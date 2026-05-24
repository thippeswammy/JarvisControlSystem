# Core Things You Need To Fix

# 1. Conversation State Manager (MOST IMPORTANT)

## Problem

Your system forgets active apps/context.

Example:

```text
open settings
open notepad
open brave
```

Then:

```text
open settings
```

SHOULD:

```text
focus existing settings window
```

NOT relaunch.

---

## Why Important

Without this:

* repeated launches
* broken continuity
* weak follow-up understanding
* poor agent memory

---

## What You Need

Maintain runtime state:

```python
active_windows = {
    "settings": {...},
    "notepad": {...},
    "brave": {...}
}

focused_window = "brave"

conversation_topic = "browser profile switching"
```

---

## Required Capabilities

### Window State Tracking

Track:

* opened apps
* minimized apps
* focused app
* window handles
* tabs/profiles (browser)

---

### App Reuse Logic

Before launch:

```python
if app already running:
    focus_existing_window()
else:
    launch_new()
```

VERY important.

---

# 2. Context Fusion Layer

## Problem

Your system processes messages independently.

---

## Needed

Pipeline should become:

```text
message
↓
conversation memory
↓
active app state
↓
recent actions
↓
intent understanding
↓
planner
```

---

## Why Important

Fixes:

```text
"close it"
"open it again"
"switch back"
"click the first one"
```

Without this, real agent behavior is impossible.

---

# 3. Desktop UI Abstraction Layer

## Problem

Currently:

* app control mixed with mouse automation
* no semantic UI understanding

---

## Needed

Use:

```text
pywinauto
+
uiautomation
```

as MAIN desktop layer.

---

## Why Important

Then you can do:

```python
find_button("System").click()
```

instead of:

```python
move mouse to x,y
```

Fixes:

* scaling problems
* wrong clicks
* fail-safe triggers
* resolution dependency

---

# 4. Browser Agent Separation (VERY IMPORTANT)

## Problem

Browser currently treated like normal desktop app.

That is wrong architecture.

---

## Needed

Create dedicated:

```text
BraveAgent
```

NOT generic desktop control.

---

## Use

```text
Playwright
+
CDP
```

---

## Why Important

Then browser becomes:

* DOM-aware
* profile-aware
* tab-aware
* URL-aware
* button-aware

Instead of:

* screen clicking

---

## Required Features

### Browser State

Track:

```python
active_browser = {
    "profiles": [],
    "tabs": [],
    "current_tab": ...
}
```

---

### Browser Semantic Actions

Support:

```text
open profile 1
switch tab
click login
search youtube
open chatgpt
```

through DOM.

---

# 5. Intent Safety Layer

## Problem

Discussion text still triggers actions.

Dangerous.

---

## Needed

Before planner:

```python
if message_is_discussion:
    NEVER execute actions
```

---

## Why Important

Fixes:

```text
"How do I open settings?"
```

NOT actually opening settings.

Critical safety fix.

---

# 6. Planner / Executor Separation

## Problem

Planner logic still leaks sometimes.

---

## Needed

Strict architecture:

```text
LLM planner
↓
executor
↓
validator
↓
formatter
↓
user
```

---

## Why Important

Prevents:

* JSON leaks
* accidental execution
* unstable behavior

---

# 7. Action Verification Layer

## Problem

System assumes success too early.

---

## Needed

After action:

```python
verify_window_exists()
verify_focus()
verify_navigation()
```

ONLY then:

```text
[OK]
```

---

## Why Important

Fixes false positives.

---

# 8. Window Focus Controller

## Problem

Re-opening instead of focusing.

---

## Needed

Window manager:

```python
focus_window(app)
restore_if_minimized(app)
switch_if_exists(app)
```

---

## Why Important

Makes assistant feel intelligent.

---

# 9. Structured App Registry

## Needed

Create registry:

```python
APPS = {
    "settings": {...},
    "notepad": {...},
    "brave": {...},
    "explorer": {...}
}
```

---

## Why Important

Fixes:

* synonym confusion
* bad launches
* inconsistent naming

---

# 10. Multi-Agent Architecture (IMPORTANT)

Separate:

```text
DesktopAgent
BrowserAgent
ConversationAgent
VisionFallbackAgent
```

NOT one giant controller.

---

## Why Important

Current system mixes:

* browser
* desktop
* conversation
* automation

into one planner.

That becomes unstable fast.

---

# Your Correct Future Stack

# Desktop

```text
pywinauto
+
uiautomation
```

---

# Browser

```text
Playwright
+
CDP
```

---

# Conversation

```text
Conversation State Manager
+
Context Fusion
```

---

# Fallback

```text
Vision/OCR only if needed
```
