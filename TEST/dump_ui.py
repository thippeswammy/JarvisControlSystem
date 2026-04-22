import sys
import time
from pywinauto import Desktop
import pygetwindow as gw

def dump_settings_ui():
    print("Dumping UI tree of active window...")
    # Wait for settings to be active
    for _ in range(5):
        w = gw.getActiveWindow()
        if w and "Settings" in w.title:
            break
        time.sleep(1)
        
    active_win = gw.getActiveWindow()
    if not active_win:
        print("No active window.")
        return
        
    print(f"Active window: {active_win.title}")
    
    desk = Desktop(backend="uia")
    # wrap the active window's handle
    w = desk.window(handle=active_win._hWnd)
    
    # Dump tree to file
    with open("ui_tree_dump.txt", "w", encoding="utf-8") as f:
        # Redirect stdout internally
        import sys
        old_stdout = sys.stdout
        sys.stdout = f
        try:
            w.print_control_identifiers(depth=5)
        finally:
            sys.stdout = old_stdout
            
    print("Dump complete. Saved to ui_tree_dump.txt")

if __name__ == "__main__":
    dump_settings_ui()
