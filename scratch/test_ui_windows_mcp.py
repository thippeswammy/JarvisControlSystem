import os
import sys
import time
from pathlib import Path

# Ensure project root is in python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from jarvis.mcp.mcp_bus import MCPBus

def find_id_by_name_or_autoid(node, query, control_type_filter=None):
    """Recursively search DOM tree for an element matching a query string."""
    if not node:
        return None
    
    node_name = node.get("name", "")
    node_autoid = node.get("auto_id", "")
    node_ct = node.get("control_type", "")
    
    match = (query.lower() in node_name.lower()) or (query.lower() in node_autoid.lower())
    if match:
        if not control_type_filter or control_type_filter.lower() in node_ct.lower():
            return node.get("element_id")
            
    for child in node.get("children", []):
        res = find_id_by_name_or_autoid(child, query, control_type_filter)
        if res:
            return res
    return None

def main():
    print("=== UI Windows MCP Demo Integration Test ===")
    
    # Clean up Calculator process before starting to prevent window collisions
    print("[*] Terminating any existing Calculator instances...")
    os.system("taskkill /f /im CalculatorApp.exe >nul 2>&1")
    os.system("taskkill /f /im Calculator.exe >nul 2>&1")
    time.sleep(0.5)

    # 1. Initialize MCPBus
    print("[*] Initializing MCPBus...")
    bus = MCPBus()
    bus.discover()
    
    # 2. List windows
    print("[*] Calling tools/list_windows...")
    windows_res = bus.call("ui_windows", "list_windows", {})
    print(f"    Available Windows: {[w['title'] for w in windows_res.get('windows', []) if w.get('title')]}")
    
    # 3. Launch Calculator App
    print("[*] Calling tools/launch_app for 'calc.exe'...")
    launch_res = bus.call("ui_windows", "launch_app", {"app_path": "calc.exe"})
    print(f"    Launch status: {launch_res.get('success')} (PID: {launch_res.get('pid')})")
    time.sleep(2.0)
    
    # 4. Fetch the DOM
    print("[*] Calling tools/get_dom for 'Calculator' (FULL mode)...")
    dom_res = bus.call("ui_windows", "get_dom", {"app_title": "Calculator", "mode": "FULL"})
    
    dom_text = dom_res.get("dom_text", "")
    print(f"    Fetched DOM of length {len(dom_text)} characters.")
    
    # Save a snippet of DOM for debug
    print("--- DOM Tree Snippet ---")
    lines = dom_text.split("\n")
    for line in lines[:30]:
        print(line)
    if len(lines) > 30:
        print(f"... and {len(lines) - 30} more lines.")
    print("------------------------")
    
    # 5. Dynamically extract button element IDs
    dom_tree = dom_res.get("dom_tree", {})
    
    id_5 = find_id_by_name_or_autoid(dom_tree, "num5Button") or find_id_by_name_or_autoid(dom_tree, "Five", "Button")
    id_plus = find_id_by_name_or_autoid(dom_tree, "plusButton") or find_id_by_name_or_autoid(dom_tree, "Plus", "Button")
    id_3 = find_id_by_name_or_autoid(dom_tree, "num3Button") or find_id_by_name_or_autoid(dom_tree, "Three", "Button")
    id_equal = find_id_by_name_or_autoid(dom_tree, "equalButton") or find_id_by_name_or_autoid(dom_tree, "Equal", "Button")
    id_results = find_id_by_name_or_autoid(dom_tree, "CalculatorResults") or find_id_by_name_or_autoid(dom_tree, "Results", "Text")
    
    print(f"[*] Dynamically resolved element IDs:")
    print(f"    - 'Five' Button ID: {id_5}")
    print(f"    - 'Plus' Button ID: {id_plus}")
    print(f"    - 'Three' Button ID: {id_3}")
    print(f"    - 'Equal' Button ID: {id_equal}")
    print(f"    - 'Results' Display ID: {id_results}")
    
    if not (id_5 and id_plus and id_3 and id_equal):
        print("[red][x] Failed to resolve one or more essential button IDs from the DOM tree.[/red]")
        sys.exit(1)
        
    # 6. Click 5, +, 3, =
    steps = [
        ("Five", id_5),
        ("Plus", id_plus),
        ("Three", id_3),
        ("Equal", id_equal)
    ]
    
    for name, eid in steps:
        print(f"[*] Performing click on '{name}' ({eid})...")
        click_res = bus.call("ui_windows", "click", {"element_id": eid, "app_title": "Calculator"})
        print(f"    Click success: {click_res.get('success')}")
        delta = click_res.get("dom_delta", {})
        print(f"    UI Changed (Delta): {delta.get('changed')}")
        time.sleep(0.5)
        
    # 7. Read display results
    print("[*] Reading display results...")
    if id_results:
        val_res = bus.call("ui_windows", "read_value", {"element_id": id_results})
        print(f"    Display Read Text: '{val_res.get('text')}'")
        print(f"    Display Read Value: '{val_res.get('value')}'")
    else:
        print("[!] Display Results element ID was not resolved. Cannot read final value.")
        
    # Shutdown bus
    bus.shutdown_all()
    print("=== Demo integration test complete ===")

if __name__ == "__main__":
    main()
