---
name: git-committer
description: >-
  Iteratively scans workspace changes, groups related modifications by architectural layer,
  and commits them in a structured execution loop until the working tree is clean.
---

# Git Committer Skill

## Overview
The `git-committer` skill provides a state-driven execution loop for an autonomous agent. Rather than applying a single monolithic commit, the agent continuously observes the Git workspace, sanitizes dynamic artifacts, categorizes files into logical architectural boundaries, and commits them iteratively. The process only terminates when the repository state is completely clean.

## 🎯 What, Why, and When

* **What it is:** An automated workflow that categorizes uncommitted code by architectural layer (e.g., config, core logic, tests) and generates standardized, Conventional Commits for each group, while actively preventing temporary runtime files from being tracked.
* **Why use it:** To prevent messy, monolithic "work-in-progress" commits. It guarantees a clean, modular, and easily navigable project history, making rollbacks, code reviews, and debugging significantly easier.
* **When to trigger it:** * After completing a specific feature or bug fix.
  * When preparing to push changes to a remote repository.
  * When the workspace has accumulated multiple modified files across different components and needs to be cleanly saved.

---

## 🛠️ Allowed Toolkit (Comprehensive Git Command Reference)
The agent is authorized to use the following comprehensive suite of Git commands to navigate the workspace, manipulate the index, interact with remotes, and inspect internal states.

### 1. Observation & State Management
* `git status -uall`: Shows the working tree status, including all untracked files. **Always use this to begin a loop.**
* `git diff <file>`: Inspects unstaged changes in the working directory.
* `git diff --cached`: Reviews what is currently staged in the index before finalizing a commit.
* `git clean -fd`: Forcibly removes untracked files and directories (use with extreme caution).

### 2. Staging & Sanitization
* `git add <path>`: Stages specific files, directories, or patterns.
* `git add -p`: Interactively stages hunks of files.
* `git rm <path>`: Removes files from the working tree and the index.
* `git rm --cached <path>`: Untracks a file without deleting it from the local disk. **Crucial for sanitizing dynamic runtime artifacts (e.g., `.db`, `.log`).**
* `git restore <path>`: Restores working tree files to discard local unstaged changes.
* `git restore --staged <path>`: Unstages a file if it was accidentally added.

### 3. Committing & History
* `git commit -m "<msg>"`: Finalizes the staged group into a permanent commit.
* `git commit --amend -m "<msg>"`: Modifies the most recent commit (useful for fixing typos in the last commit message).
* `git log -n 5 --oneline`: Verifies recent commit history.
* `git show <commit_hash>`: Shows changes introduced by a specific commit.
* `git blame <file>`: Inspects line-by-line file history to determine who changed what and when.

### 4. Branching & Navigation
* `git branch`: Lists all local branches.
* `git switch <branch>` (or `git checkout <branch>`): Switches to an existing branch.
* `git switch -c <branch>` (or `git checkout -b <branch>`): Creates and switches to a new branch.
* `git merge <branch>`: Merges another branch into the current one.
* `git rebase <branch>`: Reapplies commits on top of another base tip.
* `git stash` / `git stash pop`: Temporarily shelves unstaged changes and restores them later.

### 5. Remote Operations
* `git fetch`: Downloads objects and refs from another repository.
* `git pull`: Fetches and integrates changes from a remote repository.
* `git push origin <branch>`: Updates remote references and uploads local objects.
* `git remote -v`: Lists current tracked remote repositories.

### 6. Low-Level "Plumbing" Commands (For Deep Inspection)
* `git ls-files`: Shows information about files currently in the index and working tree.
* `git ls-tree <tree-ish>`: Lists the raw contents of a tree object (similar to a directory listing).
* `git cat-file -p <object_hash>`: Safely inspects the raw content or metadata of a Git object (blob, tree, commit, tag).
* `git rev-parse <string>`: Turns references (like `HEAD`) into raw SHA-1 hashes.

---

## Behavioral Directives (The Execution Loop)
When invoked, the agent MUST NOT execute a linear, static script. It must adopt an iterative **Observe, Orient, Decide, Act (OODA)** loop. 

* **Entry Condition:** The workspace contains modified, added, or untracked files.
* **Exit Condition:** `git status` reports nothing to commit (working tree clean).

### The Iteration Logic:
```text
WHILE (uncommitted_files_exist):
    1. OBSERVE: Run `git status -uall` to assess current state.
    2. ORIENT: 
        a. Check for runtime/dynamic artifacts (e.g., .db, .log). 
        b. If found, ignore them (add to .gitignore) and loop back to OBSERVE.
        c. Otherwise, identify ONE logical grouping from the remaining files (e.g., Configs, Core Logic, or Tests).
    3. DECIDE: Synthesize a Conventional Commit message for this specific group.
    4. ACT: `git add <group_paths>` and `git commit -m "<message>"` (using multiple `-m` flags for body and footer if needed).
```

---

## 📋 Standard Commit Message Format & Guidelines

Every commit message produced by this skill must follow the **Conventional Commits** specification. This ensures that repository history is highly structured, readable, and machine-parsable for changelog generation.

### 1. Standard Commit Structure
```text
<type>(<scope>): <subject>

<body>

<footer>
```

* **Header (Required):** Must contain a `<type>`, an optional but highly recommended `<scope>`, and a `<subject>`.
  - **Character Limit:** Keep the subject line to **50 characters or less** (strict limit of 72).
  - **Formatting:** Write the subject in lowercase, start without a capital letter, and do NOT end with a period.
  - **Mood:** Use the **imperative mood** (e.g., "add support" instead of "added support" or "adds support").
* **Body (Recommended for complex changes):** Separated from the header by a single blank line. Explains the *motivation* for the change and contrasts it with previous behavior.
  - **Formatting:** Keep lines wrapped at **72 characters**. Use bulleted points for readability.
* **Footer (Optional):** Used to reference issue trackers (e.g., `Refs: #123`) or denote breaking changes (`BREAKING CHANGE: <description>`).

---

### 2. Commit Prefix & Scope Guide

The following table defines the allowed prefixes, when to apply them, and recommended scopes for this project:

| Prefix | Type | When to apply it | Recommended Scopes | Concrete Example |
| :--- | :--- | :--- | :--- | :--- |
| **`feat`** | Feature | Introducing a new functional capability or user-facing feature. | `brain`, `gateway`, `skills`, `cli`, `agent`, `adapters` | `feat(brain): implement asynchronous ReAct closed-loop engine` |
| **`fix`** | Bug Fix | Correcting functional errors, syntax bugs, logic mismatches, or crashes. | `memory`, `skills`, `nlu`, `safety`, `gateway` | `fix(skills): support fallback brightness and volume parameter keys` |
| **`refactor`** | Refactor | Modifying code structure or readability without changing logic/behavior. | `brain`, `utils`, `core`, `adapters` | `refactor(brain): clean up closed-loop state representation` |
| **`test`** | Tests | Adding new tests, upgrading mock architectures, or fixing existing assertions. | `integration`, `unit`, `regression`, `live` | `test(integration): run gateway tests against real Ollama LLM` |
| **`docs`** | Docs | Modifying markdown files, developer documentation, READMEs, or API docstrings. | `plans`, `skills`, `readme`, `api` | `docs(readme): add troubleshooting section for Ollama timeouts` |
| **`perf`** | Performance | Logic changes specifically targetting latency, memory usage, or query speed. | `memory`, `caching`, `db`, `nlu` | `perf(memory): warm trigger embeddings in background thread` |
| **`chore`** | Maintenance | Operations on dependencies, package files, configs, or ignored files. | `config`, `deps`, `git`, `native` | `chore(git): ignore local binary files and database backups` |
| **`style`** | Style | Format changes that don't affect code meaning (whitespace, lint errors). | `lint`, `format`, `semicolons` | `style(lint): resolve black formatting warnings in app_skill` |
| **`ci`** | CI/CD | Modifying automated build, test execution, or deployment pipelines. | `actions`, `pytest-runner` | `ci(actions): run integration suite on windows-latest runner` |

---

### 3. 🧠 Writing "Deeper", Ultra-Detailed Commits (Required for Any Complex Task)

When dealing with complex implementations, architectural changes, multi-file edits, or system integrations, commits must be **extremely deep, thorough, and highly detailed**. Standard one-line commits are strictly unacceptable for these scopes. 

Every detailed commit message must clearly explain the **Context**, the **Problem**, the **Decision (Why)**, and the **Implementation (What)** using the following principles:

#### Deep Commit Principles:
1. **Explain the Root-Cause and Context ("What was the problem"):** Document the initial limitation, error, regression, or design gap. Specify exact error codes, crash behaviors, architectural constraints, or runtime symptoms.
2. **Detail the Architectural Rationale ("Why did we do it this way"):** Explain why the chosen approach is robust, what trade-offs were considered, and how it resolves the root problem. Don't just list *what* code changed; focus on the *why*.
3. **List Concrete Technical Targets:** Reference exact class names, files, APIs, databases, variables, or system settings affected by the changes.
4. **Use Structured, Highly Descriptive Bullet Points:** Break down component-level modifications in the commit body, giving each logical module its own detailed context.

#### Example 1: C++ Manifest & Rebuild Task (System Level)
```text
chore(native): integrate project configurations and registration-free WinRT manifests

- Resolve a critical build issue in `UIAutomation.sln` where the `UIAutomationServer` C++ project was missing configuration mapping targets inside the `ProjectConfigurationPlatforms` section. This caused MSBuild to skip compilation of the server, leaving a stale ABI-mismatched executable from May 31st that triggered fail-fast crashes (`0xC0000409`) at runtime.
- Map all `Release|x64` and `Debug|x64` targets for the `UIAutomationServer` project `{B1234567-8C0C-4CFD-AED9-2E979751FDC0}` in the solution configuration.
- Integrate a custom Registration-Free WinRT side-by-side (SxS) manifest (`UIAutomationServer.exe.manifest`) into the `UIAutomationServer` project directory and workspace root.
- Update `UIAutomationServer.vcxproj` to configure the MSBuild manifest compiler, using the `<Manifest>` tag's `<AdditionalManifestFiles>` property to merge and embed the custom WinRT manifest directly into `UIAutomationServer.exe` via `/manifestinput`. This ensures that activator entries for `Microsoft.UI.UIAutomation.AutomationRemoteOperation` from `Microsoft.UI.UIAutomation.dll` are dynamically registered in native C++ contexts.
```

#### Example 2: pywinauto Calculator Demo & Process lifecycle (Automation Level)
```text
feat(adapters): add pywinauto calculator demo and native test harness

- Design and implement a highly polished, robust, standalone UI Automation demonstration script (`scratch/uia_calculator_demo.py`) utilizing the stable and preinstalled `pywinauto` UIA backend.
- Implement process self-cleaning safety logic in the Python script using `taskkill` to actively terminate any stale or hanging Calculator/CalculatorApp processes before beginning automation to avoid window-matching and active-focus collisions.
- Coordinate programmatic accessibility interactions including direct child control targeting (`child_window(auto_id=...)`), active focus enforcement (`set_focus()`), spatial physical clicking (`click_input()`), extraction of result display strings, and recursive traversing of `HistoryListView` children elements.
- Ensure graceful teardown fallback chains that safely dismiss panels and flyouts via top-level container click actions if standard controls are obscured or missing.
- Create a C++ RPC server console test harness (`scratch/test_run.py`) supporting redirected stdio (`stdin=PIPE`, `stdout=PIPE`, `stderr=PIPE`), custom directory context execution (`cwd`), and detailed exit code and log capture to verify direct C++ RPC initialization pipelines.
```

#### Example 3: Cognitive Decision-Making & Planner (Engine Level)
```text
feat(brain): integrate dynamic re-planning loop and recover from tool timeouts

- Add a dynamic verification step inside the core ReAct planning orchestrator to check if the current task execution duration has exceeded the localized 10-second threshold.
- Refactor the decision loop to catch raw network sockets timeout exceptions during Ollama local inference and trigger a soft fall-back to the pre-allocated backup provider (e.g. OpenAI / Anthropic).
- Inject historical task-resumption state context into the LLM prompt buffer dynamically during recovery phases, preserving the execution queue and preventing repetitive tool invocation loops.
```

---

### 4. Golden Rules of High-Quality Commits

1. **Focus on "Why", Not "What":** The git diff shows *what* changed. Your commit message body should explain *why* it was changed, what problem it solves, and what side effects it prevents.
2. **Never Use Lazy Messages:** Avoid messages like `fix bug`, `cleanup`, `updates`, or `working on files`. Be specific.
3. **Keep Commits Atomic:** Stage and commit logical changes independently. For example, do not mix a performance optimization in memory logic with formatting improvements in standard skills.
4. **Clean up before Committing:** Actively review staged files (`git diff --cached`) to ensure no temp logs, backup files, or private tokens are accidentally staged.

---

### 4. 🚀 JARVIS Project-Specific Commit Message Templates

Use the following project-specific templates as drop-in patterns for common modifications in each JARVIS repository layer:

#### A. Core Engine & Cognitive Planning (`brain`)
* **Use case:** Modifying reasoning, closed-loop engine, context, preference routing, or recovery logic.
* **Template:**
```text
<type>(brain): <action_in_imperative_mood>

- Detail 1: what was changed in reasoning, orchestrator, or execution loop
- Detail 2: why it was changed and how it handles planning edge cases
```
* **Real-world Examples:**
  - `feat(brain): add dynamic re-planning on mid-flight user updates`
  - `fix(brain): implement robust fallback to decide() when closed-loop is mocked`

#### B. Graph Memory & Embeddings (`memory`)
* **Use case:** Modifying vector search, trigger cache-warming, GraphDB SQLite, or pathfinding.
* **Template:**
```text
<type>(memory): <action_in_imperative_mood>

- Detail 1: changes to vector search, GraphDB schema, or trigger warming
- Detail 2: impact on recall latency or embedding retrieval stability
```
* **Real-world Examples:**
  - `fix(memory): pre-load nomic-embed-text to prevent startup warmup timeouts`
  - `perf(memory): warm trigger embeddings using background thread`

#### C. Settings Control Skills (`skills`)
* **Use case:** Modifying display brightness, volume control, app orchestration, WMI, or other built-ins.
* **Template:**
```text
<type>(skills): <action_in_imperative_mood>

- Detail 1: exact fallback keys or skill parameter definitions added
- Detail 2: specific OS panel or hardware compatibility addressed
```
* **Real-world Examples:**
  - `fix(skills): support fallback brightness and volume parameter keys`
  - `feat(skills): implement native WMI monitors control interface`

#### D. Session Management & Input Adapters (`gateway`)
* **Use case:** Refactoring Telegram adapters, TUI/CLI interfaces, long-polling, thread pools, or event queues.
* **Template:**
```text
<type>(gateway): <action_in_imperative_mood>

- Detail 1: changes to channel adapters, stream streams, or thread states
- Detail 2: how it preserves non-blocking user interaction during tasks
```
* **Real-world Examples:**
  - `feat(gateway): implement thread-safe session queue for async execution`
  - `fix(gateway): avoid blocking long-polling during active task runs`

#### E. Test Architecture & Assertions (`test`)
* **Use case:** Adding unit, integration, or regression tests, or adapting test runs to real/mock LLM.
* **Template:**
```text
test(<scope>): <action_in_imperative_mood>

- Detail 1: test cases added or modified
- Detail 2: specific fixtures, environment variables, or LLM configurations
```
* **Real-world Examples:**
  - `test(integration): upgrade gateway flow assertions to support real LLM replies`
  - `test(regression): add timeout and crash detection tests for multi-step tasks`


---

## ✍️ Commit Message Anatomy & Best Practices

A well-crafted commit message is crucial for maintaining a healthy repository. The agent must format messages using the structure below to provide rich context to reviewers and future debuggers.

### Structure Breakdown

1. **Header (Subject Line):** `<type>(<optional scope>): <description>`
* Keep it under 50 characters.
* Use the imperative mood (e.g., "add", "fix", "change" instead of "added", "fixes", "changed").
* Do not capitalize the first letter.
* Do not end with a period.


2. **Body (Optional but recommended):** * Wrap text at 72 characters.
* Explain the **What** and the **Why**, not just the **How** (the code diff already shows how).
* Explain the previous behavior and what the new behavior achieves.


3. **Footer (Optional):**
* Used for referencing issue trackers (e.g., `Resolves #123`) or breaking changes.



### Golden Rules for the Agent

* **Be Specific:** Avoid vague messages like `fix bug` or `update code`.
* **Context is King:** Always explain why a specific technical approach was chosen if it isn't immediately obvious.
* **Scope Appropriately:** Use scopes in parentheses to denote the specific architectural module (e.g., `feat(perception)`, `fix(network)`, `docs(architecture)`).

### Quality Examples

**Example 1: A Feature Addition**

```text
feat(pipeline): add IR and LiDAR data fusion for 6DoF pallet pose calculation

Calculates ground-truth poses automatically to eliminate manual annotation 
in the data labeling pipeline. While 3DoF is used for physical movement, 
6DoF is strictly required here to ensure precise geometric calculations 
during the labeling phase.

```

**Example 2: A Logic Fix**

```text
fix(viz): correct transform frame target for 3D trajectory plotting

Previously, the Dash web tool evaluated odometry by plotting the transform 
from 'map' to 'odom'. This resulted in inaccurate relative movement 
representations. Changed the plotting script to calculate the transform 
between 'odom' and 'base_link' for accurate local trajectory tracking.

```

**Example 3: Resolving Hardware/Sensor Issues**

```text
fix(perception): resolve Ouster projection ghosting 

Adjusted the sensor misalignment parameters in the ROS 2 launch file. 
The previous ghosting effect was directly caused by physical misalignment 
offsets in the URDF, not a lack of smoothing algorithms as initially 
suspected.

```

**Example 4: Architectural Documentation**

```text
docs(jarvis): specify boundary for static physics vs dynamic cognitive skills

Updated the semantic macro documentation. The system is now explicitly 
configured to memorize static physics skills (e.g., setting volumes, toggling 
states). Dynamic cognitive tasks (like typing generated text) are blacklisted 
from automatic memorization to prevent uncontrolled context pollution.

```

---

## Invocation & Triggers

Semantic triggers:

* *"Format and commit all changed files"*
* *"Run the git-committer loop"*
* *"Clean up and commit everything logically"*

## Edge Cases & Mitigation

* **Previously Tracked Files:** If files like `.db` were committed in previous revisions, updating `.gitignore` will not ignore them.
* *Mitigation:* Execute `git rm --cached <path>` explicitly.


* **Large Commits Over Token Limits:** Staging too many files at once can exceed context sizes when producing description text.
* *Mitigation:* Limit each commit stage to single directories or architectural scopes.
