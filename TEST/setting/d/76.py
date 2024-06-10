import pprint
import time

import keyboard
import pywinauto


def open_windows_settings():
    # Send the keyboard shortcut to open Windows Settings (Win + I)
    keyboard.press_and_release('win+i')
    time.sleep(2)  # Wait for the Settings app to open


def click_button(control):
    # Check if the control is a button and is enabled
    try:
        if control.window_text() == 'Sound' and control.is_enabled():
            # Click the button
            control.click_input()
            print(f"Clicked on the button: {control.window_text()}", ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
        else:
            print(f"Button not clickable: {control.window_text()}")
    except Exception as e:
        pass


def print_children_components(control, data_dict, indent=0):
    # Get information about the control
    control_type = control.element_info.control_type
    control_name = control.window_text()

    # Create a dictionary for the control
    control_dict = {'Control Type >>>> ': control_type, 'Control Name >>>> ': control_name}

    # Initialize an empty list for the current indent level if not present
    if control_dict['Control Type >>>> '] == 'Button' or control_dict['Control Name >>>> '] == 'Hyperlink' or \
            control_dict['Control Name >>>> '] == 'List' or control_dict['Control Name >>>> '] == 'ListItem':
        data_dict.setdefault(indent, []).append(control_dict)

    # Recursively process the children
    for child in control.children():
        print_children_components(child, data_dict, indent + 1)


def print_controls_in_right_side_part():
    # Connect to the desktop
    desktop = pywinauto.Desktop(backend="uia")

    # Try to find the "Settings" window
    system_window = desktop.window(title="Settings", control_type="Window")
    system_window.wait("visible", timeout=10)

    # Initialize a dictionary to store the information
    data_dict = {}

    # Find and print information about all controls in the right side part of the System category
    controls = system_window.descendants()
    for control in controls:
        # Start with an empty list for the current indent level
        data_dict[control] = []

        # Call the recursive function to populate the data_dict
        print_children_components(control, data_dict)

    return data_dict


if __name__ == "__main__":
    open_windows_settings()
    result_dict = print_controls_in_right_side_part()
    # Print the resulting data structure
    pprint.pprint(result_dict)

    print("THIPPESWAMY")

    # Click buttons directly (corrected)
    for control in result_dict:  # Iterate over controls directly
        click_button(control)

    # Print the clickable items (if needed)
    # pprint.pprint(clickable_items)
