# Jarvis UI Windows MCP Server — Walkthrough

We have successfully designed and built the complete, scalable, and app-agnostic **Jarvis UI Windows MCP Server** (`ui_windows`) to enable deep desktop UI automation.

---

## 🏗️ Architecture & Component Design

The implementation adheres fully to the JARVIS autonomous architecture:

1. **`backends/base_backend.py`**: Defines abstract `UIBackend` contracts for window discovery, application spawning, UIA DOM tree traversal, and element action execution.
2. **`backends/pywinauto_backend.py`**: Implements UIA automation using `pywinauto`. It features:
   - Safe, fast retrieval of UIA control properties (name, type, bounding box, states) directly from `element_info` to prevent wrappers from raising `AttributeError` exceptions.
   - A recursive traversal algorithm to discover all control types and sub-branches at arbitrary depths.
3. **`element_context.py`**: Maps standard Windows UIA Control Types to allowed logical actions (e.g. `Button` allows `click` and `invoke`; `Edit` allows `type_text`, `read_value`, and `set_value`), informing the LLM about valid interactions.
4. **`dom_builder.py`**:
   - Recursively enriches nodes with their allowed actions.
   - Implements `compute_dom_delta` to compare UI trees before and after write actions, tracing additions, removals, and modifications.
5. **`dom_serializer.py`**: Renders trees to text for LLM consumption in three modes:
   - `FULL`: Structured, indented hierarchy with aligned metadata.
   - `INTERACTIVE_ONLY`: Compact, flat list of actionable items.
   - `TARGETED`: Property dump of a single node.
   - Enforces token-budget truncation limit (capping at 15k characters).
6. **`mcp_ui_windows_server.py`**: The stdio JSON-RPC 2.0 subprocess wrapper. It handles tool execution, dynamically manages before/after snapshots for write actions to calculate `dom_delta`, and routes stderr logs away from stdout.
7. **`config/mcp_servers.yaml`**: Registers the `ui_windows` server in the Jarvis MCP registry.
8. **`agents/builtin/ui_windows_agent.py`**: Implements the `AgentInterface` execution loop:
   - Uses list_windows and LLM decisions to find or launch target applications.
   - Walks through sequential planning steps, verifying active DOM changes after every action.
   - Feeds UI State observers into `shared.observe(...)` to update the world model.
9. **`agents/agent_bus.py`**: Integrates `UIWindowsAgent` into the standard built-in discovery logic.

---

## 🔒 Stable Element ID Generation

Element IDs are generated using a deterministic hashing algorithm:
```
{control_type_abbreviation}_{cleaned_name_or_autoid}_{cleaned_parent_name}
```
By prioritizing `automation_id` over the dynamic `name` field, element IDs remain completely stable even when the text contents of the control change dynamically (e.g. standard display screen changing from `"Display is 0"` to `"Display is 8"`).

---

## 🧪 Validation Results

The system was validated using the integration test script `scratch/test_ui_windows_mcp.py`:
- Spawns the stdio MCP server subprocess.
- Automatically launches `calc.exe`.
- Dynamically resolves UIA button IDs via DOM lookups.
- Performs clicks for the expression `5 + 3 =`.
- Verifies DOM changes (`changed=True`) after each button click.
- Successfully reads back the calculation output `"Display is 8"`.

```bash
=== UI Windows MCP Demo Integration Test ===
[*] Terminating any existing Calculator instances...
[*] Initializing MCPBus...
[*] Calling tools/list_windows...
    Available Windows: [...]
[*] Calling tools/launch_app for 'calc.exe'...
    Launch status: True (PID: 14384)
[*] Calling tools/get_dom for 'Calculator' (FULL mode)...
    Fetched DOM of length 5982 characters.
--- DOM Tree Snippet ---
Window [Calculator]                     id=win_Calculator_root  enabled=true  actions=['read_value']
  Window [Calculator]                   id=win_Calculator_Calculator  enabled=true  actions=['read_value']
    ...
    Group [Standard functions]          id=grp_StandardFunc_Calculator  enabled=true  actions=['read_value']
      Button [Five]                     id=btn_num5Button_Numberpad  enabled=true  actions=['click', 'invoke']
      Button [Plus]                     id=btn_plusButton_Standardoper  enabled=true  actions=['click', 'invoke']
      Button [Three]                    id=btn_num3Button_Numberpad  enabled=true  actions=['click', 'invoke']
      Button [Equals]                   id=btn_equalButton_Standardoper  enabled=true  actions=['click', 'invoke']
------------------------
[*] Dynamically resolved element IDs:
    - 'Five' Button ID: btn_num5Button_Numberpad
    - 'Plus' Button ID: btn_plusButton_Standardoper
    - 'Three' Button ID: btn_num3Button_Numberpad
    - 'Equal' Button ID: btn_equalButton_Standardoper
    - 'Results' Display ID: txt_CalculatorRe_Calculator
[*] Performing click on 'Five' (btn_num5Button_Numberpad)...
    Click success: True
    UI Changed (Delta): True
[*] Performing click on 'Plus' (btn_plusButton_Standardoper)...
    Click success: True
    UI Changed (Delta): True
[*] Performing click on 'Three' (btn_num3Button_Numberpad)...
    Click success: True
    UI Changed (Delta): True
[*] Performing click on 'Equal' (btn_equalButton_Standardoper)...
    Click success: True
    UI Changed (Delta): True
[*] Reading display results...
    Display Read Text: 'Display is 8'
    Display Read Value: 'Display is 8'
=== Demo integration test complete ===
```

---

## 🎭 Scenario 18: Telegram Calculator & Settings Integration Test

We created a live integration test scenario in [scenario_18_telegram_calculator_settings.py](file:///f:/RunningProjects/JarvisControlSystem/tests/live/scenario_18_telegram_calculator_settings.py) to simulate user interactions over Telegram:
1. **Initial Greeting (`hi`)**: Checks initial NLU routing and communication with Jarvis.
2. **Calculator Calculation (`calculator_5_plus_3`)**: Automates UIA Calculator to perform and verify a basic math operation (5 + 3 = 8).
3. **Display Settings Navigation (`open_display`)**: Uses deep-link support (`ms-settings:display`) to open the Display subpage in Windows Settings.
4. **Sound Settings Navigation (`open_sound`)**: Navigates directly to the Sound subpage in Windows Settings (`ms-settings:sound`).

All test phases completed successfully. The `AppFinder` mapping resolving `"calculator"` -> `"calc.exe"` and settings aliases ensures seamless operation.
