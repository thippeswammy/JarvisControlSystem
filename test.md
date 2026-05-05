# 🧠 JARVIS MESSAGE TYPE TEST SUITE (FULL)

## 🔵 1. CHAT CASES (NO ACTION)

Use these to test pure conversation handling.

```
Hi
Hello
What is your name?
Who are you?
What are you doing?
Tell me a joke
How are you?
Good morning
Can you help me?
Explain AI in simple words
```

✔ Expected: Only text reply
❌ No tools should trigger

---

## 🟡 2. SINGLE ACTION COMMANDS

Use these for direct execution testing.

```
Open notepad
Open settings
Close notepad
Type hello world
Write about AI
Open chrome
Minimize window
Maximize window
```

✔ Expected:

* ONE tool call only
* No planning JSON
* Immediate execution

---

## 🟠 3. MULTI-STEP PLAN CASES (IMPORTANT)

Use these to test planning engine.

```
Open settings and then open notepad
Close settings and write about AI in notepad
Open chrome and search AI and open first result
Open notepad then write AI then save file
Close all apps and open calculator and compute 25+30
```

✔ Expected:

* type: "plan"
* step-by-step breakdown
* ordered execution

---

## 🔴 4. COMPLEX MIXED INSTRUCTIONS

These test real-world chaos input.

```
Open settings, scroll and click system, then open notepad and write AI
Close everything and then open notepad write about artificial intelligence and save
Open chrome search machine learning open first result and take notes in notepad
```

✔ Expected:

* clean decomposition
* no mixed chat/action output

---

## 🟣 5. AMBIGUOUS / CLARIFICATION CASES

These test intelligence + safety.

```
Open it
Close that
Write something
Go there
Fix it
Do the same thing again
Open file and continue
```

✔ Expected:

* Ask clarification
* OR refuse with question
* NEVER guess

---

## ⚫ 6. ERROR HANDLING TEST CASES

Simulate failure conditions.

```
Open unknownapp
Click system in unknown screen
Write in notepad but notepad not open
Close settings but settings already closed
Navigate to file that doesn't exist
```

✔ Expected:

* error state
* retry OR fallback plan

---

## 🟢 7. SYSTEM / INTERNAL TEST CASES

For backend logic only (should NOT respond to user directly)

```
update memory AI preference
set mode to autonomous
log action history
retry last command
rollback last step
```

✔ Expected:

* internal handling only
* no UI response (or minimal debug)

---

## 🔷 8. NATURAL COMBINED REAL SCENARIOS

These are the MOST IMPORTANT for Jarvis testing.

```
Open settings check system info then open notepad and write summary
Start notepad and explain artificial intelligence in simple terms
Open chrome search deep learning then open notepad and summarize
Close all apps and prepare a note about robotics
Open system settings and then create a note on AI advantages
```

✔ Expected:

* full pipeline planning
* stable execution order