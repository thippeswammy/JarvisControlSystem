import pywinauto

# Connect to desktop and open Settings
desktop = pywinauto.Desktop(backend="uia")
system_window = desktop.window(title="Settings", control_type="Window")

# Get all elements in the "System" category
elements = system_window.descendants()

# Print labels of all buttons
for element in elements:
    control_info = element.element_info
    if control_info.control_type == "Button":
        print(f"Button Label: {element.window_text()}")

# Find and click the "About" button
about_button = system_window.child_window(title="About", control_type="Button")
about_button.click()

# Get all panels within the current context
panels = system_window.children(control_type="Pane")

# Print names of all panels
for panel in panels:
    print(f"Panel Name: {panel.window_text()}")
