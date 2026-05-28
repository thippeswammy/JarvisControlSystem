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
* **When to trigger it:** 
  * After completing a specific feature or bug fix.
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
    4. ACT: `git add <group_paths>` and `git commit -m "<message>"`.
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
| **`feat`** | Feature | Introducing a new functional capability or user-facing feature. | `brain`, `gateway`, `skills`, `cli`, `agent` | `feat(brain): implement asynchronous ReAct closed-loop engine` |
| **`fix`** | Bug Fix | Correcting functional errors, syntax bugs, logic mismatches, or crashes. | `memory`, `skills`, `nlu`, `safety`, `gateway` | `fix(skills): support volume and brightness parameter fallbacks` |
| **`refactor`** | Refactor | Modifying code structure or readability without changing logic/behavior. | `brain`, `utils`, `core`, `adapters` | `refactor(brain): clean up closed-loop state representation` |
| **`test`** | Tests | Adding new tests, upgrading mock architectures, or fixing existing assertions. | `integration`, `unit`, `regression`, `live` | `test(integration): run gateway tests against real Ollama LLM` |
| **`docs`** | Docs | Modifying markdown files, developer documentation, READMEs, or API docstrings. | `plans`, `skills`, `readme`, `api` | `docs(readme): add troubleshooting section for Ollama timeouts` |
| **`perf`** | Performance | Logic changes specifically targetting latency, memory usage, or query speed. | `memory`, `caching`, `db`, `nlu` | `perf(memory): warm trigger embeddings in background thread` |
| **`chore`** | Maintenance | Operations on dependencies, package files, configs, or ignored files. | `config`, `deps`, `git` | `chore(git): ignore local binary files and database backups` |
| **`style`** | Style | Format changes that don't affect code meaning (whitespace, lint errors). | `lint`, `format`, `semicolons` | `style(lint): resolve black formatting warnings in app_skill` |
| **`ci`** | CI/CD | Modifying automated build, test execution, or deployment pipelines. | `actions`, `pytest-runner` | `ci(actions): run integration suite on windows-latest runner` |

---

### 3. Golden Rules of High-Quality Commits

1. **Focus on "Why", Not "What":** The git diff shows *what* changed. Your commit message body should explain *why* it was changed, what problem it solves, and what side effects it prevents.
2. **Never Use Lazy Messages:** Avoid messages like `fix bug`, `cleanup`, `updates`, or `working on files`. Be specific.
3. **Keep Commits Atomic:** Stage and commit logical changes independently. For example, do not mix a performance optimization in memory logic with formatting improvements in standard skills.
4. **Clean up before Committing:** Actively review staged files (`git diff --cached`) to ensure no temp logs, backup files, or private tokens are accidentally staged.

---

## Invocation & Triggers
Semantic triggers:
* *"Format and commit all changed files"*
* *"Run the git-committer loop"*
* *"Clean up and commit everything logically"*

## Edge Cases & Mitigation
* **Previously Tracked Files:** If files like `.db` were committed in previous revisions, updating `.gitignore` will not ignore them.
  - *Mitigation:* Execute `git rm --cached <path>` explicitly.
* **Large Commits Over Token Limits:** Staging too many files at once can exceed context sizes when producing description text.
  - *Mitigation:* Limit each commit stage to single directories or architectural scopes.
