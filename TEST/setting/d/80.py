import time

import keyboard
import pywinauto


def open_windows_settings():
    # Send the keyboard shortcut to open Windows Settings (Win + I)
    keyboard.press_and_release('win+i')
    time.sleep(2)  # Wait for the Settings app to open


def click_button(control):
    if control.get('Control Type >>>> ') in ["Button", "Hyperlink", "MenuItem", "ListItem", "CheckBox", "RadioButton",
                                             "Edit"]:
        print(control.get('Control Name >>>> '), "==========", control.get('Control Type >>>> '))
    try:
        if control.get('Control Type >>>> ') in ["Button", "Hyperlink", "MenuItem", "ListItem"]:
            if input("Enter = ") == "1":
                control['control'].invoke()
                print(f"triggered on the button: {control.get('Control Name >>>> ')}",
                      ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
                return True
        elif control.get('Control Type >>>> ') in ["CheckBox", "RadioButton"]:
            if input("Enter = ") == "1":
                control['control'].set_check()
                print(f"triggered on the button: {control.get('Control Name >>>> ')}",
                      ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
                return True
        elif control.get('Control Type >>>> ') in ["Edit"]:
            if input("Enter = ") == "1":
                control['control'].set_text("hi")
                print(f"triggered on the button: {control.get('Control Name >>>> ')}",
                      ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
                return True
    except Exception as e:
        # control['control'].click_input()
        print(f"not able to click."
              f"because i think it dont support the invoke Clicked on the button: {control.get('Control Name >>>> ')}",
              "Error :", e,
              "--------------------------------------------")
        return False


def click_buttonByValue(control, _input):
    try:
        if control.get('Control Type >>>> ') in ["Button", "Hyperlink", "ListItem"]:
            if _input.lower() == control.get('Control Name >>>> ').lower():
                control['control'].invoke()
                print(f"triggered on the button: {control.get('Control Name >>>> ')}",
                      ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
                return True
        elif control.get('Control Type >>>> ') in ["CheckBox", "RadioButton"]:
            if _input.lower() == control.get('Control Name >>>> ').lower():
                control['control'].set_check(input("enter true or false for 1") == "1")
                print(f"triggered on the button: {control.get('Control Name >>>> ')}",
                      ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
                return True
        elif control.get('Control Type >>>> ') in ["Edit"]:
            if _input.lower() == control.get('Control Name >>>> ').lower():
                control['control'].set_text(input("enter text: "))
                print(f"triggered on the button: {control.get('Control Name >>>> ')}",
                      ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
                return True
        elif control.get('Control Type >>>> ') in ["MenuItem"] and 'Invoke' in control['control'].patterns():
            if _input.lower() == control.get('Control Name >>>> ').lower():
                control['control'].invoke()
                print(f"Clicked on the button: {control.get('Control Name >>>> ')}",
                      ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
                return True
        elif control.get('Control Type >>>> ') in ["MenuItem"] and 'Invoke' in control['control'].patterns():
            if _input.lower() == control.get('Control Name >>>> ').lower():
                control['control'].click_input()
                print(f"Clicked on the button: {control.get('Control Name >>>> ')}",
                      ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
                return True
    except Exception as e:
        # control['control'].click_input()
        print(f"not able to click."
              f"because i think it dont support the invoke Clicked on the button: {control.get('Control Name >>>> ')}",
              "Error :", e,
              "--------------------------------------------")
        return False


def print_children_components(control, data_list, indent=0):
    # Get information about the control
    try:
        control_type = control.element_info.control_type
        control_name = control.window_text()
    except Exception:
        return  # Skip this control if there is an issue

    # Create a dictionary for the control
    control_dict = {'Control Type >>>> ': control_type, 'Control Name >>>> ': control_name, 'control': control}

    # Print information about the control
    # print(f"{'  ' * indent}Control Type: {control_type}, Control Name: {control_name}")

    # Recursively process the children
    try:
        for child in control.children():
            print_children_components(child, data_list, indent + 1)
    except Exception:
        pass  # Handle any exceptions while processing children

    # Append the control dictionary to the list
    data_list.append(control_dict)


def click_buttons_in_controls(controls, _input):
    for control in controls:
        if _input == "":
            res = click_button(control)
        else:
            res = click_buttonByValue(control, _input)
        # res = click_button(control)
        if res: return True
        # Recursively check children
        try:
            lists = control['control'].children()
            if lists is not None:
                if click_buttons_in_controls(lists):
                    return True
        except Exception:
            pass  # Handle any exceptions while processing children


def print_controls_in_right_side_part():
    # Connect to the desktop
    desktop = pywinauto.Desktop(backend="uia")

    # Try to find the "Settings" window
    system_window = desktop.window(title="Settings", control_type="Window")
    try:
        system_window.wait("visible", timeout=10)
    except Exception:
        print("Window not found. open settings and try again")
        pass
    # Initialize a list to store the information
    data_list = []

    # Find and print information about all controls on the right side part of the System category
    try:
        controls = system_window.descendants()
        for control in controls:
            # Call the recursive function to populate the data_list
            print_children_components(control, data_list)
    except Exception:
        pass  # Handle any exceptions while processing controls

    return data_list


def main(_input):
    # open_windows_settings()
    result_list = print_controls_in_right_side_part()
    # Print the resulting data structure
    # pprint.pprint(result_list)
    # Click buttons directly (corrected)
    click_buttons_in_controls(result_list, _input)


while True:
    _input = input("<<<<<<<<<<<<<<<<<<<<<<<<<<Thippeswamy>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    main(_input)
