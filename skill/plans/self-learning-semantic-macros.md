# Self-Learning Semantic Macros & The Universal OS Operator

The user has defined a profound architectural shift: **JARVIS is a Universal OS Operator**. The core philosophy is the absolute decoupling of Cognitive Intent (The Brain) from Physical Execution (The Muscle).

## The Universal OS Operator Paradigm
Most automation bots suffer from the "Tool Explosion Problem," requiring humans to code new functions for every mental task (`draft_email`, `translate_text`). JARVIS rejects this. It scales infinitely with zero additional code by pushing 100% of the cognitive load into the LLM and restricting the Python backend to pure physics (`keyboard_inject`, `mouse_click`). 

Because JARVIS treats the OS exactly like a human does, the **Self-Learning Semantic Memory** must be designed to perfectly complement this paradigm:
1. **The LLM (The Brain)** thinks deeply, handles all reasoning/drafting, and outputs purely physical sequences.
2. **The Memory (The Reflex)** watches the Brain. If the Brain executes a static, repetitive physical sequence (like clicking through 5 menus to reach a setting), the Reflex permanently memorizes it as a **Semantic Macro**.
3. The next time the user asks for that setting, the Reflex takes over instantly (O(1) Vector Search), bypassing the Brain's inference latency entirely.

## Proposed Implementation Changes

---

### 1. Macro Storage Location: The "Global" Node
We will create a virtual `app_id="global"` node. When storing an OS-level macro, the edge will be attached to this global node rather than the active window. 
- **Schema Logic**: When the user utters a command, `MemoryManager.recall()` searches both the current `active_app` edges AND the `global` edges. This ensures OS-level commands work regardless of UI context.

---

### 2. Payload Safety Check: Protecting the Cognitive/Physics Boundary
Because the LLM does all the "thinking" before calling a physical tool, a command like "Write a polite email declining the meeting" will result in a physical `keyboard_inject` containing the drafted email. 
**If JARVIS memorizes this physical sequence, it will type the exact same email next time.**

We must explicitly protect the boundary between static physics and dynamic cognition.

> [!WARNING]
> **Dynamic Payload Blacklist**
> We will explicitly define which physical/system skills are allowed to be memorized as Reflexes.
> - **Safe to Memorize (Static Physics/State)**: `set_volume`, `set_brightness`, `power_action`, `launch_app`, `navigate_location`, `click_element`, `mouse_click`, `press_key`.
> - **Unsafe to Memorize (Cognitive/Dynamic)**: `type_text`, `keyboard_inject`, `search_web`, `search_windows`, `send_message`, `ask_user`.
> 
> *Logic:* In `orchestrator.py`, if the LLM plan contains any Unsafe skill, JARVIS recognizes it as a highly specific cognitive task and **skips** the reflex memorization step. It will force the system to route through the LLM "Brain" every time.

---

### 3. The "Success-Gate" Validation
To prevent "Poisoning the Memory Cache" with hallucinated bad paths or incomplete physical executions, JARVIS will only memorize behaviors that are strictly verified.

#### [MODIFY] `jarvis/brain/orchestrator.py`
- In `process()`, track the success of every `SkillCall` in the LLM-generated plan.
- **Success-Gate Logic**: Before calling `self._memory.add_learned_macro(edge)`, we verify:
  1. The plan originated from the LLM (`source == "llm"`).
  2. Every step in the physical execution loop returned `result.success == True`.
  3. No skills in the plan belong to the Dynamic Payload Blacklist.

---

### 4. Upgrade `Planner` for Reflex Execution

#### [MODIFY] `jarvis/brain/planner.py`
- Modify `_path_to_skill_calls(path: MemoryPath)` to support `action_type == "macro"`.
- Deserialize the `edge.action_params["calls"]` (the cached physical sequence) and return those calls directly.

---

### 5. Hot-Loading New Reflexes

#### [MODIFY] `jarvis/memory/memory_manager.py`
- Modify `recall(..., app_id=...)` to check both the active `app_id` AND the `global` app_id.
- Add `add_learned_macro(edge: GraphEdge)` which saves the macro to the Graph DB and synchronously computes the Ollama embedding, hot-loading it into the `self._trigger_embeddings` RAM cache for zero-latency availability on the very next command.

## Verification Plan

1. Speak a static OS command: "dim the visual output by a lot".
2. Watch the logs verify `[Orchestrator] Learned new macro edge for trigger: 'dim the visual output by a lot'`.
3. Speak a semantically similar command: "lower the visual output".
4. Watch the logs verify it hits the O(1) Semantic Vector Search fast-lane (The Reflex).
5. Speak a cognitive command: "Draft an email to Bob saying hello".
6. Watch the logs explicitly state `[Orchestrator] Skipping macro learning: plan contains dynamic cognitive skill 'type_text' / 'keyboard_inject'`.
