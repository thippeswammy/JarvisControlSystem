import subprocess
import time
import pprint
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from jarvis.mcp.adapters.windows_uia_bridge import WindowsUIABridge

def run_demo():
    print("Starting UIA Bridge Demo...")
    
    # Ensure no JARVIS_ALLOW_MOCK to get real data if available
    os.environ["JARVIS_ALLOW_MOCK"] = "false"
    
    bridge = WindowsUIABridge()
    connected = bridge.connect()
    if not connected:
        print("Failed to connect to UIA Server")
        return
    print(f"Bridge connected: {bridge._connected}")
    print(f"Mock mode: {os.environ.get('JARVIS_ALLOW_MOCK')}")
    
    print("\nLaunching Calculator...")
    calc_process = subprocess.Popen("calc.exe")
    time.sleep(2) # Wait for it to open
    
    try:
        print("\nGetting Focused Element (should be Calculator or near it)...")
        focused = bridge.get_focused_element()
        pprint.pprint(focused)
        
        print("\nFinding Calculator Element...")
        calc_elem = bridge.find_element(by="name", value="Calculator")
        pprint.pprint(calc_elem)
        
        if calc_elem and "element_id" in calc_elem:
            elem_id = calc_elem["element_id"]
            
            print("\nGetting Calculator Properties...")
            props = bridge.get_element_properties(elem_id)
            pprint.pprint(props)
            
            print("\nGetting Calculator Patterns...")
            patterns = bridge.get_element_patterns(elem_id)
            pprint.pprint(patterns)
            
            print("\nGetting Calculator Rect...")
            rect = bridge.get_element_rect(elem_id)
            pprint.pprint(rect)
            
    finally:
        print("\nClosing Calculator and disconnecting...")
        calc_process.terminate()
        calc_process.kill()
        bridge.disconnect()

if __name__ == "__main__":
    run_demo()
