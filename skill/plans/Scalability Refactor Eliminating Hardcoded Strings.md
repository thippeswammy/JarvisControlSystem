# Scalability Refactor: Eliminating Hardcoded Strings

This document outlines the findings of the codebase audit regarding hardcoded strings, logic, and configurations, along with a plan to refactor them into a scalable, dynamic architecture.

## 🔍 Audit Findings (Hardcoded Elements)

1. **Hardcoded Intent Categories (Scattered across `nlu.py`, `orchestrator.py`, `planner.py`, `perception_packet.py`)**
   - The categories `"EXECUTION"`, `"EDUCATIONAL"`, `"HYPOTHETICAL"`, `"CAPABILITY"`, and `"TEXT_ANALYSIS"` are currently written as raw strings throughout the codebase. If we ever want to add a new category or rename one, we have to track down every instance.

2. **Hardcoded LLM Prompts & Allowed Intents (`nlu.py`)**
   - The system prompt inside `nlu.py` hardcodes the list of allowed intents (`"open_app" | "close_app" | "type_text" | ...`).
   - *Problem:* If a new skill is registered, the NLU prompt won't know about it unless the prompt string is manually updated. This is highly unscalable.

3. **Hardcoded Few-Shot Examples (`planner.py`)**
   - Inside the Planner LLM instructions, there are hardcoded few-shot examples (e.g., `User: "open notepad" -> {"skill": "open_app"}`). 
   - *Problem:* If we change the name of `open_app` or its parameters, these examples will break the LLM's understanding.

4. **Skill Name Coupling in Engine Logic (`verification_loop.py`, `recovery_engine.py`)**
   - There are explicit `if call.skill == "open_app":` checks. 
   - *Problem:* The core brain logic should not care about specific skill names. It should rely on skill properties (e.g., `if bus.get_skill(call.skill).category == "app":`).

5. **Basic Fallback Heuristics (`nlu.py`)**
   - There is still an `if text_lower.startswith("open "): intent = "open_app"` heuristic for when the LLM is unavailable.

---

> [!WARNING]
> **User Review Required**
> 
> The changes below will significantly restructure how intents and prompts are managed. This will make the system highly scalable but requires touching several core files. Please review the proposed changes and let me know if you approve this architectural refactor.

## 🛠️ Proposed Changes

### 1. Introduce `IntentCategory` Enum
Create a new file `jarvis/perception/intents.py` defining an `Enum` for categories.
Replace all raw strings in `orchestrator.py`, `nlu.py`, and `planner.py` with `IntentCategory.EXECUTION`, etc.

### 2. Dynamic Prompt Generation (`nlu.py` & `planner.py`)
- Modify `nlu.py` to dynamically fetch the list of available skills from `SkillBus.list_skills()` and inject them into the prompt.
- Modify `planner.py` to decouple the few-shot examples. We will build a helper that dynamically constructs examples based on available skills.

### 3. Decouple Engine Logic
- Replace hardcoded `if call.skill == "open_app"` checks in `verification_loop.py` and `recovery_engine.py` with dynamic skill metadata checks (`skill_def.category == "app"`).

### 4. Remove `startswith` Heuristics
- Clean up `nlu.py` to remove the string-matching heuristic. If the LLM is down, it should explicitly fail rather than guess, enforcing the "local LLM only" reliability you requested.

## 🚦 Verification Plan

### Automated Tests
- Run `python -m pytest tests/` to ensure no unit tests are broken by the Enum refactoring.
- Run `python -m tests.live.scenario_99_normal_actions` to verify that dynamic prompt injection still accurately produces correct intent classification and routing.

### Manual Verification
- Trace the logs to ensure the LLM prompt generated at runtime actually contains the dynamically registered skills rather than the old hardcoded list.
