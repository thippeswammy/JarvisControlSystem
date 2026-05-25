# Recursive Learning, Direct Execution, & UI Spidering Plan (v2)

This updated plan incorporates your feedback. Jarvis will not only learn how to launch apps and settings directly, but it will also actively "spider" and learn the interior UI elements of applications.

## User Review Required

> [!WARNING]
> **UI Spidering Depth**
> Automatically clicking through *every* button and inner panel of an application to learn its UI could inadvertently change settings or cause unwanted actions. Because of this, it is safer to have Jarvis perform a **Visual/UIA Scan** (learning what buttons exist on the screen and recording their names) *without* blindly clicking everything, OR only click tabs to map layouts if explicitly told it is in "Safe Discovery Mode". Do you agree with restricting auto-clicking and focusing on visual mapping?

## Proposed Changes

---

### 1. Active UI Spidering (Deep UI Learning)
Jarvis will map the layout of applications so it knows what buttons/panels exist before you even ask.

#### [NEW] `Jarvis/core/ui_spider.py`
- A scanner that interacts with `AppNavigator` (your existing OCR/UIA visual system).
- **Functionality**:
  - Takes an open application (e.g. Settings).
  - Scans all visible buttons, texts, and panels.
  - Builds a localized "UI Map" memory for that specific app and window.
- **Trigger**: Can be triggered manually via a command like "Jarvis, learn this application's UI", or automatically anytime an app is idle.

#### [MODIFY] `Jarvis/core/jarvis_memory.py`
- Add a new memory file `ui_maps.md`.
- Store mapping such as: `App: Settings | Window: Network -> Elements: [Wi-Fi, Ethernet, VPN, Airplane Mode]`.
- Provide this vocabulary to the LLM so it inherently knows what it can click without guessing.

---

### 2. Recursive System Crawler (Asynchronous Scraper)
Jarvis actively scans the PC for apps and settings. As requested, this will run asynchronously and can be explicitly triggered with parameters.

#### [NEW] `Jarvis/core/system_crawler.py`
- **Asynchronous Execution**: Runs in the background on a separate thread so Jarvis remains responsive.
- **App Scanner**: Scans Windows Start Menu, Registry, and `.lnk` files for actual `.exe` paths.
- **Settings Scanner**: Scans and catalogs all `ms-settings:` URIs.
- **User Config scanner**: Scans specific user directories (like `F:\RunningProjects`) to find project roots.

#### [MODIFY] `Jarvis/core/handlers/crawler_handler.py`
- Add support for explicit commands: `"Jarvis, scan my system"` or `"Jarvis, scan apps in background"`.

---

### 3. Reactive Search Memorization & Direct Execution
Your agreement to skip UI steps and launch programs directly in the future.

#### [MODIFY] `Jarvis/core/intent_engine.py` & `action_registry.py`
- Add `ActionType.EXECUTE_PROCESS`. 
- When Jarvis learns an app for the first time, it saves `execute_process C:\Path\To\App.exe` or `execute_process ms-settings:display` into memory instead of saving UI clicks.

#### [MODIFY] `Jarvis/core/jarvis_engine.py`
- Intercepts successful searches: When Jarvis successfully uses the UI to search for and open an app, it will inspect the OS process list, find what just opened, and save the direct execution path automatically.

## Open Questions

1. **Spidering Strategy**: Should the UI spider run automatically in the background every time you open a new window to learn it quietly, or ONLY when you say `"Jarvis, analyze this UI"`?
2. **Project Mapping**: For learning "my existing things", should Jarvis create an index of all `.py`, `.md` folders in `f:\RunningProjects` so you can say `"Open test_live_sequence"` and it finds the file across projects?

## Verification Plan

### Automated / Unit Tests
- Test asynchronous execution of `system_crawler.py` to ensure it doesn't block the main engine thread.
- Test `ui_spider.py` against a known dummy UI to ensure it extracts the text nodes correctly.

### Manual Verification
- Ask Jarvis: `"Scan my system"`, verify background logs show finding `.exes`.
- Open Settings, ask: `"Jarvis, map this UI"`, then review `ui_maps.md` to see if it captured the inner buttons like "System", "Bluetooth", etc.
- Ask `"Open X"`, manually let it find it via search, stop Jarvis, and ask it to open it again—verify it launches instantly via Direct Execution.
