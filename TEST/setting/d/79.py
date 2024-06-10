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
    print(control.get('Control Name >>>> '), "==========", control.get('Control Type >>>> '))
    if control.get('Control Type >>>> ') in ["Button", "Hyperlink", "MenuItem", "ListItem"]:
        if input("Enter = ") == "1":
            control['control'].invoke()
            print(f"Clicked on the button: {control.get('Control Name >>>> ')}",
                  ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    if control.get('Control Type >>>> ') in ["CheckBox", "RadioButton"]:
        if input("Enter = ") == "1":
            control['control'].set_check()
            print(f"Clicked on the button: {control.get('Control Name >>>> ')}",
                  ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    if control.get('Control Type >>>> ') in ["Edit"]:
        if input("Enter = ") == "1":
            control['control'].set_text("hi")
            print(f"Clicked on the button: {control.get('Control Name >>>> ')}",
                  ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    # control['control'].click_input()
    # else:
    #     pass
    #     # print(f"Button not clickable: {control.get('Control Name >>>> ')}")


def print_children_components(control, data_list, indent=0):
    # Get information about the control
    try:
        control_type = control.element_info.control_type
        control_name = control.window_text()
    except Exception as e:
        return  # Skip this control if there is an issue

    # Create a dictionary for the control
    control_dict = {'Control Type >>>> ': control_type, 'Control Name >>>> ': control_name, 'control': control}

    # Print information about the control
    print(f"{'  ' * indent}Control Type: {control_type}, Control Name: {control_name}")

    # Recursively process the children
    try:
        for child in control.children():
            print_children_components(child, data_list, indent + 1)
    except Exception as e:
        pass  # Handle any exceptions while processing children

    # Append the control dictionary to the list
    data_list.append(control_dict)


def click_buttons_in_controls(controls):
    for control in controls:
        click_button(control)
        # Recursively check children
        try:
            list = control['control'].children()
            if list is not None:
                click_buttons_in_controls(list)
        except Exception as e:
            pass  # Handle any exceptions while processing children


def print_controls_in_right_side_part():
    # Connect to the desktop
    desktop = pywinauto.Desktop(backend="uia")

    # Try to find the "Settings" window
    system_window = desktop.window(title="Settings", control_type="Window")
    system_window.wait("visible", timeout=10)

    # Initialize a list to store the information
    data_list = []

    # Find and print information about all controls in the right side part of the System category
    try:
        controls = system_window.descendants()
        for control in controls:
            # Call the recursive function to populate the data_list
            print_children_components(control, data_list)
    except Exception as e:
        pass  # Handle any exceptions while processing controls

    return data_list


open_windows_settings()
result_list = print_controls_in_right_side_part()
# Print the resulting data structure
pprint.pprint(result_list)

print("THIPPESWAMY")

# Click buttons directly (corrected)
click_buttons_in_controls(result_list)


