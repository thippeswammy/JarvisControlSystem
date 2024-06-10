import pywinauto
import time
import keyboard

def open_windows_settings():
    """Opens the Windows Settings app using keyboard shortcuts."""
    keyboard.press_and_release('win+i')
    time.sleep(2)  # Wait for the Settings app to open

def navigate_to_system_category():
    """Navigates to the "System" category using keyboard shortcuts."""
    keyboard.press_and_release('tab')  # Move to the categories list
    time.sleep(1)
    keyboard.press_and_release('down')  # Select the first category
    time.sleep(1)
    keyboard.press_and_release('down')  # Select the second category (System)
    time.sleep(1)
    keyboard.press_and_release('enter')  # Open the selected category

def store_children_components(control, result_dict, indent=0):
    """Recursively stores information about a control and its children in a dictionary."""
    control_type = control.element_info.control_type
    control_name = control.window_text()
    result_dict[control_name] = {
        "control_type": control_type,
        "children": []
    }

    for child in control.children():
        store_children_components(child, result_dict[control_name], indent + 1)  # Pass the control dictionary itself

def get_controls_in_right_side_part():
    """Retrieves information about controls in the right side part of the System category and stores it in a dictionary."""
    desktop = pywinauto.Desktop(backend="uia")
    system_window = desktop.window(title="Settings", control_type="Window")
    system_window.wait("visible", timeout=10)

    controls = system_window.descendants()
    controls_data = {}

    for control in controls:
        if control.rectangle().left > system_window.rectangle().left:
            store_children_components(control, controls_data)

    return controls_data

if __name__ == "__main__":
    open_windows_settings()
    # navigate_to_system_category()  # Uncomment if navigation is needed
    controls_data = get_controls_in_right_side_part()
    print(controls_data)  # Print the structured data
