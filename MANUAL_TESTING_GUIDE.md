# Jarvis AI Control System — Manual Testing Checklist

Follow these steps to manually verify the new Jarvis AI architecture. You will provide the exact text inputs shown, and observe Jarvis performing the actions on your computer.

### Setup
1. Open a terminal in the project folder: `f:\RunningProjects\JarvisControlSystem`
2. Run the assistant: `python Jarvis/JarvisAssistantRunWithText.py`

---

## 🟩 Phase 1: Security & Activation
*Goal: Ensure commands are ignored unless Jarvis is awake.*

- [ ] **Type:** `open notepad`
   - **Expect:** Jarvis rejects the command and says "Say 'Hi Jarvis' to activate."
- [ ] **Type:** `hi jarvis`
   - **Expect:** Jarvis says "Jarvis activated. How can I help?"
- [ ] **Type:** `hi jarvis` (again)
   - **Expect:** Jarvis says "Jarvis is already active."

---

## 🟦 Phase 2: App & UI Navigation
*Goal: Prove Jarvis can open an app, navigate its menus using pywinauto, type inside it, and save the file.*

- [ ] **Type:** `launch notepad`
   - **Expect:** Notepad opens. 
- [ ] **Type:** `maximize window`
   - **Expect:** The Notepad window becomes full screen.
- [ ] **Type:** `click format`
   - **Expect:** The 'Format' menu in Notepad drops down.
- [ ] **Type:** `press escape`
   - **Expect:** The menu closes.
- [ ] **Type:** `start typing`
   - **Expect:** Typing mode is activated.
- [ ] **Type:** `Hello Jarvis! You are controlling this app.`
   - **Expect:** The text physically types itself out inside the Notepad window.
- [ ] **Type:** `stop typing`
   - **Expect:** Typing mode turns off.
- [ ] **Type:** `click file then save as`
   - **Expect:** The 'Save As' dialog pops up on screen.
- [ ] **Type:** `type in file name my_jarvis_test`
   - **Expect:** The name box fills with "my_jarvis_test". 
- [ ] **Type:** `click save`
   - **Expect:** The document is saved.
- [ ] **Type:** `close window`
   - **Expect:** Notepad closes.

---

## 🟨 Phase 3: File Explorer & Paths
*Goal: Verify Jarvis can navigate folders without using the mouse.*

- [ ] **Type:** `open explorer`
   - **Expect:** Windows File Explorer opens up.
- [ ] **Type:** `go to documents`
   - **Expect:** The active window navigates to your Documents folder.
- [ ] **Type:** `navigate to c drive`
   - **Expect:** The active window navigates to your `C:\` drive.
- [ ] **Type:** `go to this pc`
   - **Expect:** The active window switches to the 'This PC' view.
- [ ] **Type:** `close window`
   - **Expect:** File Explorer closes.

---

## 🟧 Phase 4: System Controls & Windows Settings
*Goal: Ensure deep system functions and fuzzy-matched Settings URIs still work.*

- [ ] **Type:** `set volume to 40`
   - **Expect:** Your system audio jumps to exactly 40%.
- [ ] **Type:** `increase volume by 20`
   - **Expect:** Your system audio goes up to 60%.
- [ ] **Type:** `open settings display`
   - **Expect:** The Windows Settings app opens directly to the Display page.
- [ ] **Type:** `open settings bluetooth`
   - **Expect:** The Settings app navigates to the Bluetooth page.
- [ ] **Type:** `close settings`
   - **Expect:** The Windows Settings app safely closes.

---

## 🟥 Phase 5: Window Management
*Goal: Prove the Window Controller can manage multiple open apps.*

- [ ] **Type:** `open calculator`
   - **Expect:** The Windows Calculator opens.
- [ ] **Type:** `snap left`
   - **Expect:** Calculator perfectly snaps to the left half of the screen.
- [ ] **Type:** `search for python tutorials`
   - **Expect:** Windows Search / Web Search executes your query.
- [ ] **Type:** `close calculator`
   - **Expect:** Calculator closes.
- [ ] **Type:** `close jarvis`
   - **Expect:** Jarvis deactivates. You can now close the terminal.

---

If all of the above works cleanly, the new intent engine, action registry, and generic UI navigator are fully battle-ready!
