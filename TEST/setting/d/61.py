from pywinauto import Desktop

# Specify the title of the window you want to interact with (e.g., "Settings")
window_title = "Settings"

# Connect to the desktop
desktop = Desktop(backend="uia")

# Find the window by title
window = desktop[window_title]

# Get information about the window
print(f"Window Title: {window.window_text()}")
print(f"Class Name: {window.class_name()}")
print(f"Control Count: {len(window.children())}")

# Iterate through child controls
for control in window.children():
    control_type = control.class_name()
    control_text = control.window_text()
    control_rect = control.rectangle()

    print(f"Control Type: {control_type}")
    print(f"Control Text: {control_text}")
    print(f"Control Rect: {control_rect}")
    print("-" * 30)
