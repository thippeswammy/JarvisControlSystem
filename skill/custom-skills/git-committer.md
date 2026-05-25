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

## 📋 Dynamic Command Template & Commit Prefix Guide

Use the following prefixes when synthesizing Conventional Commit messages. Below is the mapping of **What** it is, **Why** we use it, and **When** to apply it.

| Prefix | Type | What it is | Why we use it | When to apply it |
| :--- | :--- | :--- | :--- | :--- |
| **`feat`** | Feature | Addition of a new user-facing feature or code capability. | Clarifies that new functionality is introduced to the application or system. | When adding a new module, endpoint, API, or agent skill. |
| **`fix`** | Bug Fix | Resolution of a functional bug, error, crash, or logic gap. | Flags bug fixes for patch releases and confirms a regression has been solved. | When correcting logic errors, fixing failing tests, or resolving runtime warnings. |
| **`docs`** | Documentation | Edits to documentation, README files, or code docstrings. | Helps developers and users understand system architecture without altering code execution. | When writing user guides, updating APIs inline documentation, or writing SKILL.md files. |
| **`test`** | Tests | Addition, modification, or correction of unit, integration, or E2E tests. | Assures that test coverage is maintained and updated alongside feature changes. | When adding test scripts, mocking clients, or expanding test parameter suites. |
| **`refactor`** | Refactoring | Code modification that improves readability/structure without changing behavior. | Improves code maintenance, quality, and performance without introducing bugs. | When restructuring functions, applying design patterns, or renaming internal variables. |
| **`style`** | Formatting | Changes that do not affect code logic (whitespace, formatting, semicolons). | Enforces uniform linting rules and style conventions across the development team. | When running code formatters (e.g., Black, Prettier) or fixing indentation. |
| **`perf`** | Performance | Code modification specifically aimed at optimizing speed or resource usage. | Improves runtime efficiency, latency, or memory consumption. | When adding caches, optimizing database queries, or refactoring algorithms. |
| **`chore`** | Maintenance | Operations on build scripts, dependencies, build files, or tools. | Separates utility tasks from real functional codebase changes. | When modifying package.json, requirements.txt, .gitignore, or build pipelines. |
| **`ci`** | CI/CD | Changes to continuous integration configurations and scripts. | Keeps deployment pipelines and testing workflows functional and updated. | When modifying GitHub Actions, GitLab pipelines, or build environment configurations. |

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
