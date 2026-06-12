# Jarvis UI Windows MCP — Implementation Plan
### Aligned with: `skill/plans/autonomous_agent_architecture.md`

---

## What Changed from Previous Plan (All Remarks Applied)

| Remark | Old | Updated |
|---|---|---|
| Name: `windows-ui` | `windows-ui` server | `ui_windows` (Windows desktop) + `ui_browser` (browser) |
| All elements | depth-4, buttons only | **Full DOM** — every control type, every depth |
| LLM context | Raw element list | **Structured context per element** — element tells LLM what it can do |
| LLM query modes | Always full DOM | **3 modes**: FULL / INTERACTIVE_ONLY / TARGETED |
| launch_app | only known_apps.json | **Any app** — any .exe or app name |
| Element ID | index-based | **name+type hash** — stable, deterministic |
| After-action verify | End of plan only | **After every single action** — re-read DOM, verify delta |
| Architecture fit | Partial | Fully aligned with `autonomous_agent_architecture.md` |

---

## Position in the Existing Autonomous Loop

From `autonomous_agent_architecture.md` Section 2, the UI Windows MCP plugs into:

```
CapabilityPlanner  ─►  "ui_interaction" capability  ─►  UIWindowsAgent (Provider)
                                                              │
Execute → MCPBus.call("ui_windows", tool, params)   ◄────────┘
              │
              ▼
        StdioMCPAdapter  →  mcp_ui_windows_server.py  (new stdio process)
              │
        ┌─────┴─────────────────┐
        │  PywinautoBackend     │  ← Works TODAY
        │  CppUIABackend        │  ← Phase 2 (native WinRT Remote Operations)
        └───────────────────────┘

VerifyInvariants → StateComparator.diff()  ←  MCPBus.call("ui_windows", "get_dom")
                                               (automatic after EVERY action)

WorldStateModeler.update_state()  ←  receives UI State tier update
```

The **UI State** tier (tier 2 of the Five-Tier World Model) is maintained by reading the DOM  
before and after every action. The MCP server **owns the UI State** — every DOM read  
goes through it.

---

## New Folder Structure

```
jarvis/
├── mcp/
│   ├── mcp_bus.py                    (existing — UNCHANGED)
│   ├── mcp_interface.py              (existing — UNCHANGED)
│   ├── adapters/
│   │   ├── stdio_adapter.py          (existing — UNCHANGED)
│   │   ├── http_adapter.py           (existing — UNCHANGED)
│   │   └── windows_uia_bridge.py     (existing — UNCHANGED, C++ bridge stays here)
│   └── servers/                      ← NEW folder
│       ├── ui_windows/               ← NEW: Windows desktop UI automation
│       │   ├── __init__.py
│       │   ├── mcp_ui_windows_server.py   ← MCP server process (stdio JSON-RPC)
│       │   ├── backends/
│       │   │   ├── __init__.py
│       │   │   ├── base_backend.py        ← Abstract UIBackend
│       │   │   ├── pywinauto_backend.py   ← Works now
│       │   │   └── cpp_uia_backend.py     ← Phase 2 (wraps WindowsUIABridge)
│       │   ├── dom_builder.py             ← Builds full DOM from backend
│       │   ├── dom_serializer.py          ← DOM → LLM text (3 modes)
│       │   └── element_context.py         ← Per-element: what can the LLM do with it?
│       └── ui_browser/               ← NEW folder (Phase 3 — browser DOM via UIA)
│           └── (future)
│
├── agents/
│   ├── builtin/
│   │   ├── planner_agent.py          (existing — UNCHANGED)
│   │   ├── aggregator_agent.py       (existing — UNCHANGED)
│   │   ├── brave_agent.py            (existing — UNCHANGED)
│   │   └── ui_windows_agent.py       ← NEW: AgentInterface
│   └── agent_bus.py                  ← MODIFY: register UIWindowsAgent in _discover_builtins()
│
└── config/
    └── mcp_servers.yaml              ← MODIFY: add "ui_windows" entry
```

---

## The 9 MCP Tools (`ui_windows` server)

> The LLM calls these via `MCPBus.call("ui_windows", tool_name, params)`.

| Tool | Params | Returns | When LLM Uses It |
|---|---|---|---|
| `get_dom` | `app_title?`, `mode`, `depth?` | Full structured DOM + element context | To **understand** the UI before planning |
| `list_windows` | — | All open windows (title, pid, class) | To discover what apps are running |
| `launch_app` | `app` (any .exe or name) | `{success, pid, window_title}` | To open an app that isn't running |
| `find_elements` | `by`, `value`, `mode?` | Matching elements + their contexts | To locate a specific element by name/id/type |
| `click` | `element_id` | `{success, dom_delta}` | To click a button / invoke an element |
| `type_text` | `element_id`, `text` | `{success, dom_delta}` | To type into an Edit control |
| `set_value` | `element_id`, `value` | `{success, dom_delta}` | To set ComboBox / Slider / CheckBox value |
| `invoke` | `element_id` | `{success, dom_delta}` | To invoke MenuItem / Hyperlink / Button |
| `read_value` | `element_id` | `{text, value, state}` | To read current text/value of an element |

> **`dom_delta`** — Every write action returns the DOM diff automatically.  
> The agent does **NOT** need to call `get_dom` again manually — it's embedded in the response.

---

## Three DOM Modes (Smart Filtering)

The LLM chooses which mode it needs based on the task:

### Mode 1: `FULL` — "I need to understand the whole UI"
```
=== APP: Calculator (PID: 12345) ===
Window [Calculator]
  Pane [Standard]
    Button [Five]        id=btn_Five_calc123   enabled=true   actions=[click, invoke]
    Button [Plus]        id=btn_Plus_calc123   enabled=true   actions=[click, invoke]
    Button [Three]       id=btn_Three_calc123  enabled=true   actions=[click, invoke]
    Button [Equal]       id=btn_Equal_calc123  enabled=true   actions=[click, invoke]
    Text   [Display: 0]  id=txt_Display_calc1  enabled=false  actions=[read_value]
    Button [History]     id=btn_History_calc1  enabled=true   actions=[click]
    Button [Navigation]  id=btn_Nav_calc123    enabled=true   actions=[click]
    Edit   [Memory]      id=edt_Mem_calc123    enabled=true   actions=[type_text, read_value]
```

### Mode 2: `INTERACTIVE_ONLY` — "I need to find what I can click/type"
```
INTERACTIVE ELEMENTS in Calculator:
  [btn_Five_calc123]   Button "Five"    → click / invoke
  [btn_Plus_calc123]   Button "Plus"    → click / invoke
  [btn_Equal_calc123]  Button "Equal"   → click / invoke
  [edt_Mem_calc123]    Edit   "Memory"  → type_text / read_value
```

### Mode 3: `TARGETED` — "I already know the element, just read or act on it"
```
Element: [txt_Display_calc1]
  Name: "Display is 8"
  ControlType: Text
  Value: "8"
  Enabled: false
  Actions available: read_value
```

---

## Element Context (What the LLM Learns Per Element)

The key insight from the remark: *"when LLM wants to understand, it needs full — and it says the button and that says specific action things (button, item, and others) — that info will need to give."*

Each element tells the LLM **what it is** AND **what you can do with it**:

```json
{
  "element_id": "btn_Five_calc123",
  "name": "Five",
  "control_type": "Button",
  "auto_id": "num5Button",
  "enabled": true,
  "offscreen": false,
  "rect": {"x": 110, "y": 200, "w": 50, "h": 50},
  "patterns_supported": ["InvokePattern"],
  "actions_available": ["click", "invoke"],
  "children": [],
  "value": null
}
```

Control-type → available actions mapping (built into `element_context.py`):

| Control Type | Actions Available |
|---|---|
| Button | `click`, `invoke` |
| Edit / Document | `type_text`, `read_value`, `set_value` |
| CheckBox | `toggle`, `read_value` |
| RadioButton | `select`, `read_value` |
| ComboBox | `expand`, `set_value`, `read_value` |
| ListItem / TreeItem / TabItem | `select`, `read_value` |
| MenuItem | `invoke`, `expand` |
| Slider / ScrollBar | `set_value`, `read_value` |
| Text / Pane / Group | `read_value` |
| Hyperlink | `invoke` |
| Window | (container — no direct action) |

---

## After Every Action: Automatic DOM Verify Loop

> From remark: *"yes, each action — after each action (click/type), agent re-reads DOM to verify"*

The `UIWindowsAgent` verifies after **every single step**:

```python
def _execute_with_verify(self, plan, mcp_bus, dom_before):
    for step in plan["steps"]:
        # Execute action
        result = mcp_bus.call("ui_windows", step["action"], step["params"])
        
        # result already contains dom_delta (server sends it automatically)
        dom_delta = result.get("dom_delta", {})
        
        # Verify the action had effect
        if not dom_delta.get("changed"):
            # Action had no effect — element may have been wrong
            # Re-read full DOM and re-plan this step
            dom_now = mcp_bus.call("ui_windows", "get_dom", {"mode": "FULL"})
            re_plan = self._ask_llm_retry(step, dom_now, local_memory)
            result = mcp_bus.call("ui_windows", re_plan["action"], re_plan["params"])
        
        # Log to WorldState UI tier
        shared.observe(f"UI Action [{step['action']}] on [{step['params']['element_id']}]: "
                       f"changed={dom_delta.get('changed')}, "
                       f"new_value={dom_delta.get('new_value', '')}")
```

---

## UIWindowsAgent — AgentInterface (Existing Pattern)

Follows `PlannerAgent` / `AgentInterface` exactly. Registered in `AgentBus._discover_builtins()`.

```
UIWindowsAgent.run(task, context, local_memory, shared):
  1. list_windows → find/launch target app (any .exe allowed)
  2. get_dom(mode=FULL) → capture complete UI State
  3. LLM Call → understand UI, produce action_plan (JSON steps[])
  4. For each step:
       a. mcp_bus.call("ui_windows", action, params)
       b. Check dom_delta → verify changed
       c. If not changed → re-read + re-plan this step (LLM retry)
       d. shared.observe(UI state change for WorldStateModeler)
  5. get_dom(mode=FULL) → final DOM
  6. LLM Call → did the goal succeed? (GoalCheck)
  7. Return AgentResult
```

---

## Config Changes

### [MODIFY] `jarvis/config/mcp_servers.yaml`

```yaml
mcp_servers:
  - name: ui_windows
    transport: stdio
    command: ["python", "jarvis/mcp/servers/ui_windows/mcp_ui_windows_server.py"]
    description: >
      Windows desktop UI automation — capture full DOM, click, type, read any
      element in any application. Provides structured element context for LLM.
```

### [MODIFY] `jarvis/agents/agent_bus.py` — `_discover_builtins()`

```python
try:
    from jarvis.agents.builtin.ui_windows_agent import UIWindowsAgent
    self.register(UIWindowsAgent())
except ImportError as exc:
    logger.debug(f"[AgentBus] UIWindowsAgent not found: {exc}")
```

### [MODIFY] `jarvis/perception/ui_inspector.py`

- Replace shallow depth-4 scan with call to `MCPBus.call("ui_windows", "get_dom", {"mode": "FULL"})`
- Or keep existing as lightweight fast-path and delegate deep scan to MCP server

---

## Parallel Implementation Roadmap (9 Steps)

Build bottom-up so every step is independently testable:

```
Step 1  jarvis/mcp/servers/ui_windows/backends/base_backend.py
          → Abstract class: get_dom, find_elements, click, type, invoke, launch_app, list_windows

Step 2  jarvis/mcp/servers/ui_windows/backends/pywinauto_backend.py
          → Implements base_backend using pywinauto (works TODAY)
          → get_dom walks full tree, ALL control types, name+type hash element IDs

Step 3  jarvis/mcp/servers/ui_windows/element_context.py
          → Control-type → actions_available map
          → Per-element JSON context builder

Step 4  jarvis/mcp/servers/ui_windows/dom_builder.py
          → Builds full DOM tree from backend
          → Attaches element_context to every node
          → Computes dom_delta (before/after diff)

Step 5  jarvis/mcp/servers/ui_windows/dom_serializer.py
          → FULL / INTERACTIVE_ONLY / TARGETED mode renderers
          → Token-budget aware: never exceeds 4000 tokens

Step 6  jarvis/mcp/servers/ui_windows/mcp_ui_windows_server.py
          → JSON-RPC 2.0 over stdio (like StdioMCPAdapter expects)
          → tools/list + tools/call dispatcher for all 9 tools
          → Every write tool embeds dom_delta in response

Step 7  jarvis/config/mcp_servers.yaml
          → Register "ui_windows" server

Step 8  jarvis/agents/builtin/ui_windows_agent.py
          → AgentInterface: run() with full loop + per-action verify
          → LLM prompts: UI understanding → action plan → goal check

Step 9  jarvis/agents/agent_bus.py
          → Register UIWindowsAgent in _discover_builtins()
```

---

## Phase 2: C++ Backend (When WinRT DLL Load is Fixed)

```
Step 10  jarvis/mcp/servers/ui_windows/backends/cpp_uia_backend.py
           → Implements base_backend using existing WindowsUIABridge
           → UIA Remote Operations: single IPC call for full tree (O(1) vs O(N))
           → auto_select_backend(): try C++ first, fall back to pywinauto

Advantage of C++ (from autonomous_agent_architecture.md Section 4):
  - DOM traversal: < 1ms (vs 200-500ms Python)
  - Memory: 2-8MB (vs 80-150MB Python)
  - Remote Operations: entire tree walk in 1 IPC call
```

---

## Phase 3: Browser Backend (`ui_browser`)

```
jarvis/mcp/servers/ui_browser/
  → Accesses RootWebArea element via UIA (Chrome/Edge native)
  → Falls back to IAccessible2 for Firefox
  → Same 9-tool interface as ui_windows
  → Same UIBrowserAgent following AgentInterface pattern
```

---

## Demo Test After Phase 1

```python
# scratch/test_ui_windows_mcp.py
from jarvis.mcp.mcp_bus import MCPBus

bus = MCPBus()
bus.discover()

# 1. List open windows
windows = bus.call("ui_windows", "list_windows", {})
print(windows)

# 2. Launch Calculator
bus.call("ui_windows", "launch_app", {"app": "calc.exe"})

# 3. Get full DOM (FULL mode)
dom = bus.call("ui_windows", "get_dom", {"app_title": "Calculator", "mode": "FULL"})
print(dom["dom_text"])

# 4. Click 5, +, 3, =
for elem_id in ["num5Button", "plusButton", "num3Button", "equalButton"]:
    result = bus.call("ui_windows", "click", {"element_id": elem_id})
    print(f"click {elem_id}: changed={result['dom_delta']['changed']}")

# 5. Read result
val = bus.call("ui_windows", "read_value", {"element_id": "CalculatorResults"})
print(f"Result: {val['text']}")  # → "Display is 8"
```

---

## Verification Plan

| Level | What | How |
|---|---|---|
| Unit | DOM builder, serializer | `tests/test_dom_builder.py` — mock pywinauto |
| Unit | Element context mapping | `tests/test_element_context.py` |
| Unit | MCP server tools/list + tools/call | `tests/test_mcp_ui_windows_server.py` — subprocess pipe |
| Integration | MCPBus → ui_windows → Calculator | `scratch/test_ui_windows_mcp.py` |
| Agent | UIWindowsAgent full loop | Mock LLM + real pywinauto → Calculator 5+3 |
| World Model | DOM delta → WorldStateModeler | Check UI State tier updates correctly |
