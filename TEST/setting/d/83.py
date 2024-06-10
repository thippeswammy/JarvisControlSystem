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
                print(f"Clicked on the button: {control.get('Control Name >>>> ')}",
                      ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
        elif control.get('Control Type >>>> ') in ["CheckBox", "RadioButton"]:
            if input("Enter = ") == "1":
                control['control'].set_check()
                print(f"Clicked on the button: {control.get('Control Name >>>> ')}",
                      ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
        elif control.get('Control Type >>>> ') in ["Edit"]:
            if input("Enter = ") == "1":
                control['control'].set_text("hi")
                print(f"Clicked on the button: {control.get('Control Name >>>> ')}",
                      ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    except Exception as e:
        control['control'].click_input()
        print(f"Clicked on the button: {control.get('Control Name >>>> ')}",
              "--------------------------------------------")
        pass


def print_controls_in_right_side_part():
    # Connect to the desktop
    desktop = pywinauto.Desktop(backend="uia")

    # Try to find the "Settings" window
    system_window = desktop.window(title="Settings", control_type="Window")
    system_window.wait("visible", timeout=10)

    # Find and print information about all controls on the right side part of the System category
    try:
        controls = system_window.descendants()
        for control in controls:
            # Call the recursive function to populate the data_list
            click_button(control)
            # Recursively check children
            try:
                list = control['control'].children()
                if list is not None:
                    click_button(list)
            except Exception as e:
                pass  # Handle any exceptions while processing children
    except Exception as e:
        pass  # Handle any exceptions while processing controls


def main():
    open_windows_settings()
    print_controls_in_right_side_part()


main()
