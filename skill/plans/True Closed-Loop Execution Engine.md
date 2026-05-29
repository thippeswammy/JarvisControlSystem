# True Closed-Loop Execution Engine

A single user request triggers a **System ↔ LLM autonomous loop** that keeps iterating — sensing, reasoning, acting, and verifying — until the user's intent is **fully satisfied**, with **zero additional user input required**.

## The Core Problem

The current ReAct loop in [orchestrator.py](file:///f:/RunningProjects/JarvisControlSystem/jarvis/brain/orchestrator.py#L194-L295) has critical flaws that prevent true closed-loop completion:

1. **No Goal Completion Signal**: The LLM has no way to say "I'm done, the goal is complete." It just keeps generating new plans until it hits a terminal action or max iterations.
2. **No Accumulated Feedback**: After executing a step, the system re-invokes the LLM with the **same original prompt**. The LLM doesn't see *what changed* on screen — only that prior steps succeeded/failed.
3. **No World-State Diff Injection**: The `WorldStateModeler` and `ContextHarvester` capture state but this **isn't structured as a diff** (before vs after) for the LLM.
4. **No Goal Decomposition**: Complex requests ("open Notepad, write hello, save as test.txt") are sent whole, and the LLM re-plans the entire thing each iteration instead of tracking sub-goals.
5. **Runaway Loops**: As seen in [screen.md](file:///f:/RunningProjects/JarvisControlSystem/logs/screen.md#L104-L115), iteration 2+ re-asks the same question and gets the same (wrong) answer, looping until timeout.
6. **No `DONE` Signal**: The planner returns `chat_reply` or `ask_user` as termination signals, but there's no explicit "goal achieved" signal from the LLM.

## Architecture: The Closed-Loop Cycle

```
┌──────────────────────────────────────────────────────┐
│                    USER REQUEST                       │
│           "Open Notepad and write hello"              │
└──────────────────┬───────────────────────────────────┘
                   │ (single entry point)
                   ▼
┌──────────────────────────────────────────────────────┐
│              CLOSED-LOOP ENGINE                       │
│                                                       │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐           │
│  │ 1.SENSE │───▶│ 2.THINK │───▶│ 3.ACT   │           │
│  │         │    │  (LLM)  │    │         │           │
│  └────▲────┘    └─────────┘    └────┬────┘           │
│       │                             │                │
│       │         ┌─────────┐         │                │
│       └─────────│4.VERIFY │◀────────┘                │
│                 │ (DONE?) │                          │
│                 └────┬────┘                          │
│                      │                               │
│               ┌──────▼──────┐                        │
│               │  GOAL MET?  │                        │
│               │  yes → EXIT │                        │
│               │  no  → LOOP │                        │
│               └─────────────┘                        │
└──────────────────────────────────────────────────────┘
```

Each iteration:
1. **SENSE**: Capture full world state (OS windows, UI tree, active app, screen hash)
2. **THINK**: Feed the LLM: original goal + execution history + world-state diff + "what's left?"  
   LLM responds with ONE of: `{action: [...], status: "in_progress"}` or `{status: "done", summary: "..."}`
3. **ACT**: Execute the returned skill calls
4. **VERIFY**: Compare before/after state, check success, inject result feedback

## Proposed Changes

### Brain — Core Engine

#### [MODIFY] [orchestrator.py](file:///f:/RunningProjects/JarvisControlSystem/jarvis/brain/orchestrator.py)

The ReAct loop (lines 194–295) will be **replaced** with a call to the new `ClosedLoopEngine`. The orchestrator remains the entry point but delegates to the engine for the iterative loop.

- Replace the inline `while iteration < max_iterations` block with `ClosedLoopEngine.run()`
- The engine handles: sense → think → act → verify → done?
- Memory path (fast path) remains unchanged as an optimization

#### [NEW] [closed_loop_engine.py](file:///f:/RunningProjects/JarvisControlSystem/jarvis/brain/closed_loop_engine.py)

The **core autonomous execution engine**. Encapsulates the full System↔LLM loop.

**Key design:**

```python
class ClosedLoopEngine:
    """
    Autonomous System ↔ LLM execution loop.
    
    Single user request → iterative sense/think/act/verify
    until the LLM signals DONE or max iterations reached.
    """
    
    def __init__(self, planner, bus, router, context_harvester, 
                 episodic, temporal, verification_loop, learner,
                 world_modeler, max_iterations=10):
        ...
    
    def run(self, goal: str, packet: PerceptionPacket, 
            snapshot: ContextSnapshot) -> ClosedLoopResult:
        """
        Execute the closed loop until goal is satisfied.
        
        Returns ClosedLoopResult with:
          - results: list[SkillResult]
          - plan: list[SkillCall] (accumulated)
          - completed: bool
          - summary: str (LLM's own summary of what was done)
          - iterations: int
        """
        execution_ledger = ExecutionLedger(goal=goal)
        
        for iteration in range(1, self.max_iterations + 1):
            # 1. SENSE
            world_before = self._sense(snapshot)
            
            # 2. THINK — LLM sees goal + ledger + world state
            decision = self._think(goal, execution_ledger, world_before)
            
            if decision.status == "done":
                return ClosedLoopResult(completed=True, 
                                       summary=decision.summary, ...)
            
            # 3. ACT
            step_results = self._act(decision.actions, world_before)
            
            # 4. VERIFY — capture world after, compute diff
            world_after = self._sense(snapshot)
            diff = self._compute_diff(world_before, world_after)
            
            # Update ledger with results + diff
            execution_ledger.record_step(
                iteration=iteration,
                actions=decision.actions,
                results=step_results,
                world_diff=diff,
            )
```

**The `ExecutionLedger`** is a structured history that gets injected into every LLM call:

```python
@dataclass
class LedgerEntry:
    iteration: int
    actions_taken: list[dict]      # skill + params
    results: list[dict]            # success/fail + message
    world_diff: dict               # what changed on screen
    timestamp: float

class ExecutionLedger:
    """Accumulates step-by-step execution history for the LLM."""
    goal: str
    entries: list[LedgerEntry]
    
    def to_llm_context(self) -> str:
        """Serializes full execution history for LLM injection."""
```

---

#### [NEW] [closed_loop_prompt.py](file:///f:/RunningProjects/JarvisControlSystem/jarvis/brain/closed_loop_prompt.py)

Dedicated prompt builder for the closed-loop LLM calls. This is **different** from the planner's prompt because it includes:

- The **goal** (original user request)
- The **execution ledger** (what was done so far, what succeeded, what failed)
- The **current world state** (active windows, UI tree, etc.)
- A **structured response schema** that includes `status: "done" | "in_progress" | "blocked"`

The response schema the LLM must follow:

```json
{
  "status": "in_progress | done | blocked",
  "reasoning": "Brief internal reasoning about what to do next",
  "actions": [
    {"skill": "open_app", "params": {"target": "notepad"}}
  ],
  "summary": "Only when status=done: what was accomplished"
}
```

> [!IMPORTANT]
> The `status: "done"` signal is the **key innovation**. It lets the LLM explicitly say "the goal is complete" rather than relying on heuristic detection of terminal skills like `chat_reply`.

---

### Brain — Supporting Changes

#### [MODIFY] [planner.py](file:///f:/RunningProjects/JarvisControlSystem/jarvis/brain/planner.py)

Add a new method `plan_closed_loop_step()` that builds the closed-loop prompt (using `closed_loop_prompt.py`) and calls `router.decide_closed_loop()`. This is separate from the existing `plan()` to avoid breaking the current flow.

---

#### [MODIFY] [world_state.py](file:///f:/RunningProjects/JarvisControlSystem/jarvis/brain/world_state.py)

Add a `diff()` static method:

```python
@staticmethod
def diff(before: WorldState, after: WorldState) -> dict:
    """Compute semantic diff between two world states."""
    # Returns: new windows, closed windows, focus changes, 
    # resource deltas, browser tab changes
```

This diff gets injected into the execution ledger so the LLM sees exactly what changed.

---

### LLM Layer

#### [MODIFY] [llm_interface.py](file:///f:/RunningProjects/JarvisControlSystem/jarvis/llm/llm_interface.py)

Add a new `ClosedLoopDecision` dataclass and `decide_closed_loop()` abstract method:

```python
@dataclass
class ClosedLoopDecision:
    status: str  # "done", "in_progress", "blocked"
    reasoning: str
    actions: list[SkillCallSpec]  # empty when status="done"
    summary: Optional[str] = None  # populated when status="done"
```

#### [MODIFY] [llm_router.py](file:///f:/RunningProjects/JarvisControlSystem/jarvis/llm/llm_router.py)

Add `decide_closed_loop()` method that mirrors `decide()` but uses the closed-loop system prompt and returns `ClosedLoopDecision`.

#### [MODIFY] [local_llm.py](file:///f:/RunningProjects/JarvisControlSystem/jarvis/llm/backends/local_llm.py)

Implement `decide_closed_loop()` with:
- Closed-loop system prompt (from `closed_loop_prompt.py`)
- JSON schema enforcement for `ClosedLoopDecision`
- The same retry/self-correction logic as `decide()`

#### [MODIFY] Backend files: [nvidia_llm.py](file:///f:/RunningProjects/JarvisControlSystem/jarvis/llm/backends/nvidia_llm.py), [openai_llm.py](file:///f:/RunningProjects/JarvisControlSystem/jarvis/llm/backends/openai_llm.py), [tunneled_llm.py](file:///f:/RunningProjects/JarvisControlSystem/jarvis/llm/backends/tunneled_llm.py), [mock_llm.py](file:///f:/RunningProjects/JarvisControlSystem/jarvis/llm/backends/mock_llm.py)

Each backend gets a `decide_closed_loop()` implementation following the same pattern as `decide()` but returning `ClosedLoopDecision`.

---

## How the Loop Prevents the Current Bugs

### Bug 1: Iteration 2+ Re-Plans Everything (screen.md L36-48)
**Before**: Iteration 2 sees same user request, generates full plan again (open notepad + write) even though it's already done.  
**After**: The execution ledger shows "Step 1: open_app(notepad) → SUCCESS, type_text('Agent memory test') → SUCCESS". The LLM sees this and returns `status: "done"`.

### Bug 2: LLM Returns Chat Instead of Action (screen.md L85-89)
**Before**: "Bring it back" gets a `chat_reply` with the literal text "The memory system works correctly."  
**After**: The closed-loop prompt explicitly says "You MUST return actions to complete the goal, not chat." The `status` field forces structured output.

### Bug 3: Runaway minimize_window Loop (screen.md L103-115)
**Before**: "Close it without saving" → LLM keeps returning `minimize_window` in a loop.  
**After**: The ledger shows "Step 1: minimize_window → SUCCESS, Step 2: minimize_window → SUCCESS" and the world-state diff shows "notepad still open". The LLM sees this pattern and course-corrects.

### Bug 4: Recovery Engine Not Integrated (recovery_engine.py exists but unused)
**After**: The closed-loop engine integrates `RecoveryEngine.diagnose_and_heal()` when a step fails, injecting corrective actions before the next LLM call.

---

## Open Questions

> [!IMPORTANT]
> **Max Iterations**: Currently set to 10. Should this be configurable per-request complexity? Simple commands (open app) should complete in 1-2 iterations. Complex multi-step tasks might need 8-10. Should we have an adaptive limit?

> [!IMPORTANT]
> **Blocked State Handling**: When the LLM returns `status: "blocked"` (e.g., "I need a save dialog to appear but it hasn't"), should we:
> - Option A: Escalate to user immediately via `ask_user`
> - Option B: Try recovery (RecoveryEngine) first, then escalate
> - Option C: Allow up to 2 retry iterations before escalating

> [!WARNING]
> **LLM Token Budget**: The execution ledger grows with each iteration. With 10 iterations of world-state + actions + diffs, we could exceed the context window. Should we implement a sliding window (keep last N entries) or a summarization strategy (compress older entries)?

> [!NOTE]
> **OODA Runner**: The existing [ooda_runner.py](file:///f:/RunningProjects/JarvisControlSystem/jarvis/brain/ooda_runner.py) overlaps heavily with this new engine. Should we deprecate it in favor of `ClosedLoopEngine`? They serve the same purpose but the new engine is more structured.

---

## Verification Plan

### Automated Tests
1. **Unit test**: `ClosedLoopEngine` with mocked planner/bus — verify it exits on `status: "done"`
2. **Unit test**: `ExecutionLedger.to_llm_context()` produces correct prompt format
3. **Unit test**: `WorldState.diff()` correctly identifies window changes
4. **Integration test**: Run `scenario_99_new_test_cases --steps 01` to verify the Notepad open+write+minimize+restore sequence completes without runaway loops
5. Build validation: `python -m pytest tests/ -x` to ensure no regressions

### Manual Verification
- Run the full scenario 99 test suite with `--telegram` flag
- Observe that iteration counts drop (most commands complete in 1-2 iterations instead of hitting max)
- Verify no timeout failures on previously-failing steps
