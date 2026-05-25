# State-Aware Delta Navigation for JARVIS (v2 — Updated Plan)

## What Changed From v1 of This Plan

| Your Comment | Change Made |
|---|---|
| "not only this, also all my system" | **Universal State-Awareness** — the paradigm covers ALL stateful systems (OS, browser, file system, even external APIs) — not just the Windows UI |
| "LLMs will make this more good" | **LLM is now a first-class delta calculator** — not just a fallback. It always receives the full UI snapshot to maximize delta precision |
| "states traceable — user action OR last JARVIS action" | **State Provenance Engine** — every state transition records WHO caused it (`USER` or `JARVIS`) and WHAT action caused it, forming a traceable lineage journal |
| "yes" (graceful degrade) | ✅ `UIInspector` returns empty `UISnapshot` if pywinauto unavailable |
| "yes, extend later" (email) | ✅ Single default email/browser in `preferences.yaml` for now |
| "yes" (synchronous) | ✅ `UIInspector` runs synchronously alongside `StateHarvester` |

---

## The Core Philosophy (Universal, Not Just Windows)

> The OS is stateful. The browser is stateful. The file system is stateful. Every external API has session state. **Blind macros fail everywhere — not just in Windows Settings.**

JARVIS must hold a **Universal State Model** across all domains:

| Domain | State Example | State Signature Source |
|---|---|---|
| Windows OS / Settings | "Currently on: Windows Update page" | `UIInspector` (pywinauto UIA) |
| Browser | "Chrome, tab: Gmail Inbox" | `UIInspector` (window title parse) |
| File System | "CWD: C:\Users\thipp\Documents" | `FileStateInspector` (simple `os.getcwd()`) |
| Terminal/Shell | "Last command: pip install X" | `EpisodicMemory` (last logged action) |
| External APIs | "Telegram: last replied to chat_id=456" | `EpisodicMemory` (logged action) |

The `UIInspector` is the *primary* state reader for GUI contexts. For non-GUI contexts, `EpisodicMemory` already logs every action taken — it becomes the state source. **No new infrastructure is needed for non-GUI state: it's already in Episodic Memory.**

---

## Architecture Diagram (Updated)

```
User: "Connect Bluetooth"
       │
       ▼
[ContextHarvester.capture()]
   ┌─────────────────────────────────────┐
   │ active_app  = "Settings"            │
   │ page_title  = "Windows Update"      │
   │ nav_items   = [Bluetooth, Network…] │
   │ state_sig   = "abc123ef45cd"        │◄── UIInspector reads this
   │ state_origin = "USER"               │◄── Provenance: user navigated here
   │ prior_action = "clicked Windows     │
   │                 Update link"        │◄── Last traceable action
   └─────────────────────────────────────┘
       │
       ├──────────────────────────────────────────────────────┐
       ▼                                                      ▼
[MemoryManager.recall(cmd, state_sig)]           [StateLineage.query(state_sig)]
  Pass 1: state_sig match → Edge_B               Returns: "Settings/Windows Update
  → [click_element("Bluetooth & devices")]        reached by USER at 13:42"
  Hit? → Execute directly (no LLM needed) ✅
       │
       │ (No memory hit → LLM path)
       ▼
[LLM DeltaPlanner] ◄── ALWAYS gets full UI context (not just on fallback)
  Prompt includes:
  - System Context (preferences: browser=chrome, email=gmail_web)
  - Current UI Snapshot (page, nav, buttons)
  - State Provenance ("Settings open, user navigated to Windows Update")
  - Task: "Connect Bluetooth"
  - Instruction: "Calculate DELTA steps only from current state"
  LLM output: [click_element("Bluetooth & devices")]  ← minimal delta
       │
       ▼
[Execution]
       │
       ▼
[State-Keyed Macro Learning]
  Save GraphEdge with:
  - starting_state_sig = "abc123ef45cd"
  - state_origin       = "USER"
  - prior_action       = "clicked Windows Update link"
```

---

## New Concept: State Provenance Engine

**Your key insight**: "States reached by user using [manually], or over last action taken by JARVIS — this needs to be traceable."

Every state transition in JARVIS must answer:
1. **WHO** caused this state? (`USER` or `JARVIS`)
2. **WHAT** action caused it? (e.g., `"clicked Bluetooth & devices"` or `"user opened Settings manually"`)
3. **WHEN** did it happen? (timestamp)

### How It's Implemented

**`EpisodicMemory`** already logs every JARVIS action. We extend it to also serve as the **State Lineage Journal** — a readable trace of how the current state was reached.

The `StateLineage` object (returned by `EpisodicMemory.get_lineage()`) answers: *"How did we get here?"*

```python
@dataclass
class StateTransition:
    state_sig: str           # The resulting UI state
    cause: str               # "USER" | "JARVIS"
    action: str              # "clicked 'Windows Update'" | "launched settings"
    skill_used: str          # "click_element" | "open_app" | "" (for user)
    timestamp: str           # ISO8601
    app_context: str         # "settings"
```

This lineage is injected into the LLM prompt, giving the LLM a *reason* for the current state:

```
[State Provenance]
Current state: Settings/Windows Update
Reached by: USER (manually navigated at 13:42)
OR
Reached by: JARVIS (executed click_element("Windows Update") at 13:41)
```

The LLM can then make smarter decisions:
- If **JARVIS** navigated here → JARVIS knows exactly where it is, high confidence delta
- If **USER** navigated here → JARVIS should verify via UIInspector before acting

---

## What's Already Built (Unchanged)

| Component | Status |
|---|---|
| `StateHarvester` — pywinauto UIA hash | ✅ (used for verification) |
| `ContextHarvester` — active app/title | ✅ (extended in this plan) |
| `GraphDB / GraphEdge` — SQLite graph | ✅ (schema extended) |
| `MemoryManager` — semantic recall | ✅ (two-pass added) |
| `Orchestrator` — auto-learn macro | ✅ (state_sig injection added) |
| `Planner._plan_via_llm` | ✅ (prompt enriched) |
| `EpisodicMemory` — action log | ✅ (lineage journal added) |
| `SkillBus` + `@skill` decorator | ✅ (unchanged) |

---

## Proposed Changes (9 Components)

### Component 1 — `UIInspector` [NEW]
#### [NEW] `jarvis/perception/ui_inspector.py`

Reads the live accessibility tree and returns a compact, LLM-readable `UISnapshot`.

**Output structure:**
```python
@dataclass
class UISnapshot:
    active_app: str         # "Settings"
    page_title: str         # "Windows Update"
    nav_items: list[str]    # ["System", "Bluetooth & devices", ...]
    visible_buttons: list[str]  # ["Check for updates"]
    active_section: str     # "Windows Update"
    state_signature: str    # sha256(sorted_nav + page_title)[:12] — stable short ID
    is_empty: bool = False  # True if pywinauto unavailable or nothing harvested

    def to_llm_context(self) -> str:
        """Compact LLM-injectable string."""
        return (
            f"Active App: {self.active_app} | Current Page: {self.page_title}\n"
            f"Navigation Menu: {self.nav_items[:10]}\n"
            f"Visible Buttons: {self.visible_buttons[:8]}"
        )
```

**Design rules:**
- Capped at 40 UI elements (LLM token budget protection)
- `state_signature` = `sha256(sorted(nav_items) + page_title)[:12]` — stable across minor UI redraws
- Gracefully returns `UISnapshot(is_empty=True)` if pywinauto unavailable
- Covers: Windows Settings, Chrome, Notepad, Explorer, any UIA-accessible app

---

### Component 2 — `GraphEdge` Schema Extension [MODIFY]
#### [MODIFY] `jarvis/memory/graph_db.py`

**`GraphEdge` dataclass — 3 new fields:**
```python
starting_state_sig: str = ""   # sha256[:12] of UISnapshot at macro execution start
state_origin: str = ""         # "USER" | "JARVIS" — who caused the starting state
prior_action: str = ""         # Human-readable description of the action that led here
```

**SQL migration (safe — adds nullable columns with defaults):**
```sql
ALTER TABLE edges ADD COLUMN starting_state_sig TEXT DEFAULT '';
ALTER TABLE edges ADD COLUMN state_origin TEXT DEFAULT '';
ALTER TABLE edges ADD COLUMN prior_action TEXT DEFAULT '';
```

**New query method:**
```python
def get_edges_by_state(self, app_id: str, state_sig: str) -> list[GraphEdge]:
    """Return all edges whose starting_state_sig matches the given signature."""
```

---

### Component 3 — `EpisodicMemory` Lineage Extension [MODIFY]
#### [MODIFY] `jarvis/memory/layers/episodic.py`

Extend `EpisodicMemory` to serve as the **State Lineage Journal**.

**New method:**
```python
def record_state_transition(
    self,
    state_sig: str,
    cause: str,        # "USER" | "JARVIS"
    action: str,       # "clicked 'Bluetooth & devices'" | "user opened Settings"
    skill_used: str,   # skill name or ""
    app_context: str,
) -> None:
    """Log a state transition to the lineage journal."""

def get_lineage(self, state_sig: str = "") -> Optional[StateTransition]:
    """
    Get the most recent state transition, optionally filtered by state_sig.
    Used by the Planner to inject provenance into the LLM prompt.
    """
```

This is a lightweight extension to the existing episodic log — adds one new record type, no separate DB table needed.

---

### Component 4 — `ContextSnapshot` + `UISnapshot` in Packet [MODIFY]
#### [MODIFY] `jarvis/perception/perception_packet.py`

```python
@dataclass
class ContextSnapshot:
    active_app: str = ""
    active_window_title: str = ""
    active_node_id: str = ""
    screen_hash: str = ""
    ui_snapshot: Optional["UISnapshot"] = None   # NEW — live UI tree
    state_sig: str = ""                          # NEW — short stable state ID
    state_origin: str = ""                       # NEW — "USER" | "JARVIS"
    prior_action: str = ""                       # NEW — last traceable action
```

---

### Component 5 — `ContextHarvester` Upgrade [MODIFY]
#### [MODIFY] `jarvis/perception/context_harvester.py`

Wire `UIInspector` into `capture()`. Also wire the `EpisodicMemory` lineage query to populate `state_origin` and `prior_action` automatically.

```python
def capture(self) -> ContextSnapshot:
    title = self._get_foreground_title()
    app_id = self._infer_app_id(title)
    ui_snap = self._inspector.inspect()           # UIInspector
    lineage = self._episodic.get_lineage()        # Who last changed state?

    return ContextSnapshot(
        active_app=app_id,
        active_window_title=title,
        screen_hash=...,
        ui_snapshot=ui_snap,
        state_sig=ui_snap.state_signature,
        state_origin=lineage.cause if lineage else "UNKNOWN",
        prior_action=lineage.action if lineage else "",
    )
```

---

### Component 6 — `MemoryManager` Two-Pass State-Keyed Recall [MODIFY]
#### [MODIFY] `jarvis/memory/memory_manager.py`

**Upgraded `recall()` signature:**
```python
def recall(
    self,
    command: str,
    app_id: Optional[str] = None,
    state_sig: str = "",           # NEW
    command_threshold: float = 0.55,
) -> Optional[MemoryPath]:
```

**Two-pass logic:**
```
Pass 1 (Precise Match):
   Filter edges WHERE starting_state_sig == state_sig
   Then run semantic match on triggers
   → If found with score > threshold: return immediately

Pass 2 (State-Agnostic Fallback):
   Run full semantic search across all edges (existing behavior)
   → Handles macros saved without state_sig (legacy/desktop-start macros)

Tie-breaker upgrade:
   Within top-0.02 band, prefer:
   1. matching state_sig (exact state match wins)
   2. matching app_id (local app over global)
   3. higher success_count (proven history)
```

---

### Component 7 — `PreferenceRouter` [NEW]
#### [NEW] `jarvis/brain/preference_router.py`

Reads `preferences.yaml`, provides a `get_system_context()` string injected into every LLM prompt.

```python
class PreferenceRouter:
    def get_system_context(self) -> str:
        return (
            f"[User Workspace Defaults]\n"
            f"OS: {prefs['os']} | Browser: {prefs['browser']} | "
            f"Email: {prefs['email']} ({prefs['email_url']}) | "
            f"Terminal: {prefs['terminal']} | Editor: {prefs['text_editor']}"
        )
```

---

### Component 8 — `DeltaPlanner` — LLM Always Gets UI Context [MODIFY]
#### [MODIFY] `jarvis/brain/planner.py`

**Key upgrade: LLM is now a first-class delta calculator, not just a fallback.**

The `_plan_via_llm()` method now **always** receives:
- System context (preferences)
- Current UI snapshot (page, nav, buttons)
- State provenance (who caused this state + prior action)
- Delta instruction (only generate steps not yet done)

```python
def _plan_via_llm(
    self,
    packet: PerceptionPacket,
    ui_snapshot: Optional[UISnapshot] = None,
    state_lineage: Optional[StateTransition] = None,
) -> list[SkillCall]:

    system_ctx = self._preference_router.get_system_context()
    ui_ctx = ui_snapshot.to_llm_context() if ui_snapshot else "UI state: unknown"
    lineage_ctx = (
        f"State reached by: {state_lineage.cause} — '{state_lineage.action}'"
        if state_lineage else "State origin: unknown"
    )

    enriched_prompt = (
        f"{system_ctx}\n\n"
        f"[Current UI State]\n{ui_ctx}\n\n"
        f"[State Provenance]\n{lineage_ctx}\n\n"
        f"[Available Skills]\n{available_skills_list}\n\n"
        f"[Task]\n{packet.text}\n\n"
        "IMPORTANT: Output ONLY the delta steps needed from the CURRENT UI state. "
        "Do NOT re-open apps already open. Do NOT re-navigate to pages already visible."
    )
```

---

### Component 9 — `Orchestrator` State-Keyed Macro Learning [MODIFY]
#### [MODIFY] `jarvis/brain/orchestrator.py`

Three upgrades:
1. Pass `snapshot.state_sig` into `MemoryManager.recall()`
2. Save `starting_state_sig`, `state_origin`, `prior_action` on new macro edges
3. Call `episodic.record_state_transition()` after every successful skill execution (traces JARVIS-caused state changes)

```python
# On macro learn:
new_edge = GraphEdge(
    ...
    starting_state_sig=snapshot.state_sig,       # NEW
    state_origin=snapshot.state_origin,           # NEW: "USER" | "JARVIS"
    prior_action=snapshot.prior_action,           # NEW: traceable cause
)

# After every skill execution (JARVIS causes a state change):
self._episodic.record_state_transition(
    state_sig="",          # post-execution state (re-harvested next cycle)
    cause="JARVIS",
    action=f"executed {call.skill}({call.params})",
    skill_used=call.skill,
    app_context=snapshot.active_app,
)
```

---

### Component 10 — `preferences.yaml` [NEW]
#### [NEW] `jarvis/config/preferences.yaml`

```yaml
workspace:
  os: windows_11
  browser: chrome
  email: gmail_web
  email_url: https://mail.google.com
  terminal: powershell
  text_editor: notepad
```

---

## Files Changed Summary

| File | Action | Purpose |
|---|---|---|
| `jarvis/perception/ui_inspector.py` | **NEW** | Live UI tree → `UISnapshot` + `state_signature` |
| `jarvis/perception/perception_packet.py` | **MODIFY** | Add `UISnapshot`, `state_sig`, `state_origin`, `prior_action` to `ContextSnapshot` |
| `jarvis/perception/context_harvester.py` | **MODIFY** | Wire `UIInspector` + episodic lineage into `capture()` |
| `jarvis/memory/graph_db.py` | **MODIFY** | Add `starting_state_sig`, `state_origin`, `prior_action` to `GraphEdge`; new `get_edges_by_state()` |
| `jarvis/memory/memory_manager.py` | **MODIFY** | Two-pass state-keyed recall with upgraded tie-breaking |
| `jarvis/memory/layers/episodic.py` | **MODIFY** | Add `StateTransition` record type + `record_state_transition()` + `get_lineage()` |
| `jarvis/brain/preference_router.py` | **NEW** | Preference config reader + system context injection |
| `jarvis/brain/planner.py` | **MODIFY** | LLM always gets UI context + delta instruction; pass `ui_snapshot` and `state_lineage` |
| `jarvis/brain/orchestrator.py` | **MODIFY** | Pass `state_sig` to recall; save state provenance in macro edges; log JARVIS state transitions |
| `jarvis/config/preferences.yaml` | **NEW** | User-editable workspace defaults |

---

## State Provenance — How Traceability Works End-to-End

### Scenario: User opens Settings manually, then says "Connect Bluetooth"

```
13:40  User opens Settings manually (Windows Home screen)
       → StateTransition NOT recorded (JARVIS didn't do this)
       → UIInspector sees: page="Home", state_sig="home_abc123"

13:41  User manually clicks "Windows Update"
       → StateTransition NOT recorded (JARVIS didn't do this)
       → UIInspector sees: page="Windows Update", state_sig="wu_def456"

13:42  User says: "Connect Bluetooth"
       → ContextHarvester: state_sig="wu_def456", state_origin="USER", prior_action=""
       → Recall: no state-keyed macro for "wu_def456"
       → DeltaPlanner LLM receives:
           State Provenance: "State reached by: USER (unknown prior action)"
           Current UI: "Settings | Windows Update | Nav: [Bluetooth & devices, ...]"
       → LLM output: [click_element("Bluetooth & devices")]   ← delta only
       → Execute → Success
       → Macro saved:
           starting_state_sig = "wu_def456"
           state_origin = "USER"
           prior_action = ""
       → JARVIS records: "executed click_element at 13:42 → state changed"

13:50  User says: "Connect Bluetooth" again (Settings still open, on Windows Update)
       → state_sig="wu_def456" — PASS 1 HIT → Edge_B found
       → Execute [click_element("Bluetooth & devices")] immediately, no LLM needed ✅
```

### Scenario: JARVIS itself navigated to Windows Update first

```
13:41  JARVIS executes navigate_location("Windows Update") successfully
       → EpisodicMemory records:
           StateTransition(cause="JARVIS", action="executed navigate_location(Windows Update)",
                           skill_used="navigate_location", state_sig="wu_def456")

13:42  User says: "Connect Bluetooth"
       → ContextHarvester queries get_lineage() → finds JARVIS transition
       → state_origin="JARVIS", prior_action="executed navigate_location(Windows Update)"
       → LLM receives higher-confidence context:
           "State reached by: JARVIS — executed navigate_location(Windows Update)"
       → LLM has full certainty about current page → better delta output
```

---

## Verification Plan

### Automated Tests
- `tests/test_ui_inspector.py` — Mock pywinauto, verify `UISnapshot` structure and `state_signature` stability
- `tests/test_state_provenance.py` — Verify `EpisodicMemory.record_state_transition()` and `get_lineage()`
- `tests/test_state_keyed_recall.py` — Pass 1 vs Pass 2 fallback in `MemoryManager`
- `tests/test_delta_planner.py` — Mock LLM, verify UI snapshot + provenance appear in enriched prompt
- `tests/test_preference_router.py` — Verify system context injection format

### Manual Verification Scenarios
1. Open Settings → navigate to **Windows Update** manually → say "Connect Bluetooth"
   - ✅ Expected: JARVIS clicks "Bluetooth & devices" (not re-opens Settings)
2. Say "Connect Bluetooth" from the Desktop
   - ✅ Expected: JARVIS opens Settings, then clicks Bluetooth
3. Say "write a polite email declining the meeting"
   - ✅ Expected: Chrome opens → Gmail URL → Compose button clicked
4. Inspect `jarvis.db` edges table: verify `starting_state_sig`, `state_origin`, `prior_action` are populated
5. Run the same command twice from the same state → verify second execution hits Pass 1 (memory, no LLM)
