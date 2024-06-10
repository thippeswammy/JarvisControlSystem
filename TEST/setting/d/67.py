import pywinauto
import time
import keyboard

def open_windows_settings():
    # Send the keyboard shortcut to open Windows Settings (Win + I)
    keyboard.press_and_release('win+i')
    time.sleep(2)  # Wait for the Settings app to open

def navigate_to_system_category():
    # Send keyboard shortcuts to navigate to the "System" category
    keyboard.press_and_release('tab')  # Move to the categories list
    time.sleep(1)
    keyboard.press_and_release('down')  # Select the first category
    time.sleep(1)
    keyboard.press_and_release('down')  # Select the second category (System)
    time.sleep(1)
    keyboard.press_and_release('enter')  # Open the selected category

def print_children_components(control, indent=0):
    # Print information about the control and its children
    control_type = control.element_info.control_type
    control_name = control.window_text()
    print(f"{'  ' * indent}Control Type: {control_type}, Control Name: {control_name}")

    # Recursively print information about the children
    for child in control.children():
        print_children_components(child, indent + 1)

def print_controls_in_system_category():
    # Connect to the desktop
    desktop = pywinauto.Desktop(backend="uia")

    # Try to find the "System" window
    system_window = desktop.window(title="Settings", control_type="Window")
    system_window.wait("visible", timeout=10)

    # Find and print information about all controls in the System category
    controls = system_window.descendants()
    for control in controls:
        print_children_components(control)

if __name__ == "__main__":
    open_windows_settings()
    navigate_to_system_category()
    print_controls_in_system_category()
