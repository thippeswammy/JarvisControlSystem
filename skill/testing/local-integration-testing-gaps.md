# Implementation Plan: Ultra-Complex Local Integration Testing & Core System Gaps

This plan implements highly advanced, deep testing workflows simulating realistic, complex "computer-agent work" across multiple system applications and browsers, while resolving core navigation and file-saving gaps.

---

## User Review Required

### 1. In-Place Browser Navigation & Information Foraging
> [!IMPORTANT]
> To prevent default browser hijacks, we will implement **In-Place Browser Navigation** using `ctrl+l` when any browser window is active.
> Additionally, we are building **Complex Information Foraging** capabilities into the browser automation:
> * **Search & Redirect**: Navigate to search engines, type queries, press enter, extract the interactive Accessibility DOM Tree, locate the primary result link by index, and click to redirect.
> * **Content Extraction**: Retrieve and parse page contents to extract key information (e.g., search details, repo names).

### 2. Multi-App System Deep Navigation
> [!TIP]
> **Scenario 15** is expanded into a deep multi-app system integration test covering:
> 1. **File Explorer**: Open, navigate to folders, create/verify diagnostic files.
> 2. **Settings**: Open and navigate deep into Personalization or System Settings screens.
> 3. **Notepad**: Save a diagnostic report using `ctrl+s` + file name + `enter`.
> 4. **SQLite Timeline**: Query temporal records to audit active execution steps.

---

## Proposed Changes

### Core System Enhancements

#### [MODIFY] [navigator_skill.py](file:///f:/RunningProjects/JarvisControlSystem/jarvis/skills/builtins/navigator_skill.py)
* Update `navigate_location` to inspect the active window's title via `pyautogui.getActiveWindowTitle()`.
* If a browser process is active (e.g. title matches Chrome, Edge, Brave, Firefox), simulate `ctrl+l` -> type URL -> `enter` rather than launching `os.startfile(url)` which hijacks the active window with the default browser.

#### [MODIFY] [planner.py](file:///f:/RunningProjects/JarvisControlSystem/jarvis/brain/planner.py)
* Inject a explicit example of writing and saving a text file in Notepad in `Planner._plan_via_unified_llm` to instruct the local LLM (`gemma3:4b`) to run `ctrl+s` -> `type_text` -> `enter` for file saving:
  `User: "type status in notepad and save as report.txt" → ctrl+s → type_text("report.txt") → enter`.

---

### Scenario 15: Deep Desktop & System App Orchestration
#### [MODIFY] [scenario_15_autonomous_desktop_agent.py](file:///f:/RunningProjects/JarvisControlSystem/tests/live/scenario_15_autonomous_desktop_agent.py)
Update to run a deeply nested, multi-app coordination sequence:
* **Step 1: Session Boot & Resource Check**: Initialize session and fetch host system resources.
* **Step 2: File Explorer Deep Navigation**: Launch File Explorer, navigate to the user's `%TEMP%` directory (a real filesystem target), and verify workspace readiness.
* **Step 3: Deep Settings Navigation**: Open Display or Personalization settings using Windows deep-link schemes (`ms-settings:`), verify focus, and close settings gracefully.
* **Step 4: Notepad Telemetry & Saving**: Launch Notepad, write the system resource diagnostic telemetry report, trigger the Save As dialog with `ctrl+s`, type `%TEMP%\diagnostic_report.txt`, and press `enter` to confirm the save.
* **Step 5: Structured Memory Verification**: Query the SQLite Graph database timeline to find when Notepad was launched and what actions were performed.
* **Step 6: Graceful Cleanup**: Programmatically close Notepad, File Explorer, and any remaining settings windows.

---

### Scenario 16: Complex Playwright Browser Automation & Web Foraging
#### [NEW] [scenario_16_browser_automation.py](file:///f:/RunningProjects/JarvisControlSystem/tests/live/scenario_16_browser_automation.py)
A new, extremely complex, and advanced browser-centric integration test:
* **Step 1: Browser Launch**: Boot a Playwright Chromium session or connect to a CDP-controlled browser profile.
* **Step 2: Navigate & Search**: Navigate to `google.com` or `duckduckgo.com`.
* **Step 3: Interactive Search**:
  * Type the query `"Jarvis Control System"` in the search input box.
  * Press `enter` to submit the search.
* **Step 4: DOM Accessibility Extraction & Link Redirection**:
  * Extract the interactive DOM tree (e.g. links, inputs) with indices (`[1] Link "...", [2] ...`).
  * Identify a search result link pointing to GitHub or documentation.
  * Simulate click-by-index on that search result node (`click_browser_node(index)`) to trigger redirection.
* **Step 5: Content Mining & Tab Switching**:
  * Verify the redirection page has loaded.
  * Extract specific text (e.g., page header or repo stats).
  * Open a new browser tab, navigate to a separate site (e.g. `github.com/trending`), and extract trending repositories.
* **Step 6: Multi-Tab Graceful Cleanup**: Close all open pages, contexts, and browser threads.

---

## Verification Plan

### Automated Run Commands
We will run both advanced suites locally using Ollama NLU backends:
```powershell
# Run the Desktop Multi-App Integration Test
python -m tests.live.scenario_15_autonomous_desktop_agent

# Run the Advanced Browser & Web Foraging Test
python -m tests.live.scenario_16_browser_automation
```

### Manual Audit Checklist
* Confirm `logs/telegram_test.log` captures the full simulated conversations cleanly.
* Verify the file `%TEMP%\diagnostic_report.txt` is physically written and contains correct CPU/RAM details.
* Ensure Playwright does not crash, and correctly handles index-based DOM interactions.
