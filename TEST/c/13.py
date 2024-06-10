import pygetwindow as gw

# Get the currently active (visible) window
active_window = gw.getActiveWindow()

# Get the title of the active window
if active_window:
    print("Active Window Title:", active_window.title)
else:
    print("No active window found.")
