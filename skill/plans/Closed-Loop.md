# Implementation Plan: JARVIS Orchestrator Architectural Improvements (Deepened)

This updated plan outlines the deepened implementation of key architectural improvements to the JARVIS control system based on your feedback. We are transitioning the orchestrator to a **deeper, context-aware closed-loop ReAct engine** that is highly sensitive to current OS context (modal dialogs, popup windows, focus shifting), enforces `gemma3` usage (disallowing silent mock fallbacks), and will be verified using the `--telegram` test flags.

---

## User Review Required

> [!IMPORTANT]
> **Context-Aware Closed-Loop (ReAct) Engine**
> The orchestrator will no longer run an offline static checklist. In each Sense-Think-Act iteration, it will explicitly inspect the system for:
> 1. The currently focused foreground window.
> 2. The list of all open application windows.
> 3. **Modal popups & dialogs** (e.g., "Save As", file overwrite prompts, or confirmation windows).
> If a popup is active, the ReAct loop will feed this context to the LLM (e.g., *"Active Foreground: Save As dialog"*), letting the LLM dynamically generate keyboard inputs (`type_text`, `press_key(enter)`) to handle the dialog *before* continuing the main task.
>
> **Strict Ollama Gemma3 Enforcement**
> * If Ollama is offline or unreachable, the system will **not** silently fallback to the `MockLLM` for dynamic planning. Instead, it will attempt ensuring Ollama starts up, and if unsuccessful, it will explicitly raise a warning/error to the user asking to start the service.

---

## Open Questions

None currently. All previous design questions have been resolved according to your comments.

---

## Proposed Changes

### 1. Deeper Sense-Think-Act (ReAct) Engine

#### [MODIFY] [orchestrator.py](file:///f:/RunningProjects/JarvisControlSystem/jarvis/brain/orchestrator.py)
* Replace the linear `for call in plan:` execution with a `while` loop (up to `max_iterations=10`):
  * **Sense**:
    * Retrieve foreground window title.
    * Enumerate all open top-level window titles (detecting popups/dialogs like `"Save As"`, `"Confirm Save As"`, `"Warning"`, etc.).
    * If browser is active, extract the DOM accessibility tree (via Playwright or fallback to window hierarchy).
    * Bundle this into an rich, real-time context payload.
  * **Think**:
    * Call the LLM with the prompt + RAG memories + current OS state + `react_history` of past attempts in this turn.
    * The LLM selects the **next single action** or a short sub-plan to handle the immediate situation.
  * **Act**:
    * Execute the selected action(s) via the verification loop.
    * Record detailed success/fail result, and append to `react_history` (e.g. `[OK] typed filename`, `[FAIL] FakeButton123 not found`).
    * If the LLM generates a terminal `chat` action or `ask_user` action, or the goal is satisfied, exit the loop.

#### [MODIFY] [planner.py](file:///f:/RunningProjects/JarvisControlSystem/jarvis/brain/planner.py)
* Update `plan()` and `_plan_via_unified_llm()` to accept `react_history` list parameter.
* Format a new `[Execution History in Current Turn]` block and inject it into the prompt so the LLM knows what happened in preceding steps.
* Update `enriched_context` to include:
  * `[Foreground Window & Modal Dialogs]` listing active popup states.
  * `[All Open Windows]` listing active desktop apps.

---

### 2. Strict Ollama/Gemma3 Routing

#### [MODIFY] [llm_router.py](file:///f:/RunningProjects/JarvisControlSystem/jarvis/llm/llm_router.py)
* Modify the fallback hierarchy in `decide()`:
  * When executing high-priority dynamic cognitive steps, if the `primary` backend is `local` (Ollama) or `tunneled` (Gemma3) and it fails, do **not** run the emergency `MockLLM` for planning.
  * Instead, trigger `ensure_ollama_running()` to attempt auto-startup. If it remains offline, raise a warning/error reply: *"Ollama Gemma3 cognitive core is offline. Please make sure the service is running (`ollama serve`)."*

---

### 3. Build and Fix the Sensory Toolkit

#### [MODIFY] [system_skill.py](file:///f:/RunningProjects/JarvisControlSystem/jarvis/skills/builtins/system_skill.py)
* Add **`get_active_window_title`** skill:
  * Uses `win32gui` foreground tracking to return the active foreground window title.
* Add **`verify_element_exists`** skill:
  * Searches the active native window via `pywinauto` (UIA descendants) or Playwright browser pages to check if a specific element or popup button is visible.

#### [MODIFY] [browser_skill.py](file:///f:/RunningProjects/JarvisControlSystem/jarvis/skills/builtins/browser_skill.py)
* Stabilize `extract_browser_dom_tree`:
  * If playwright is not installed, fail gracefully and fall back to native window title/hierarchy parsing via `pywinauto` to report what browser windows are open.

---

### 4. LLM JSON Structure Self-Correction

#### [MODIFY] [local_llm.py](file:///f:/RunningProjects/JarvisControlSystem/jarvis/llm/backends/local_llm.py)
#### [MODIFY] [tunneled_llm.py](file:///f:/RunningProjects/JarvisControlSystem/jarvis/llm/backends/tunneled_llm.py)
* Implement a JSON self-correction loop in `decide()`:
  * If parsing the LLM response fails:
    1. Re-call the model with the messages history appended with:
       * The malformed response text (role: assistant).
       * A correction prompt specifying the JSON error traceback (role: user) and requesting a clean JSON output.
    2. Try up to 2 retry attempts.

---

## Verification Plan

### Automated Tests
* Run the live integration test suite with live Telegram reporting enabled so you can watch execution progress in your Telegram app:
  ```powershell
  python -m tests.live.scenario_99_new_test_cases --telegram
  ```

### Manual Verification
* Inspect the trace messages inside your Telegram chat to verify:
  1. Correct Sense-Think-Act decision trace when dealing with Notepad's "Save As" explorer dialogs.
  2. Prompt correction handling when Gemma3 auto-corrects any invalid JSON layout.
