import time
import keyboard
import pywinauto


def open_windows_settings():
    # Send the keyboard shortcut to open Windows_icon Settings (Win + I)
    keyboard.press_and_release('win+i')
    time.sleep(2)  # Wait for the Settings app to open


def click_button(control):
    control_type = control.get('Control Type >>>> ')
    control_name = control.get('Control Name >>>> ')

    if control_type in ["Button", "Hyperlink", "MenuItem", "ListItem", "CheckBox", "RadioButton", "Edit"]:
        print(control_name, "==========", control_type)

    try:
        if control_type in ["Button", "Hyperlink", "MenuItem", "ListItem"]:
            if input("Enter = ") == "1":
                control['control'].invoke()
                print(f"triggered on the button: {control_name}", ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
                return True
        elif control_type in ["CheckBox", "RadioButton"]:
            if input("Enter = ") == "1":
                control['control'].set_check()
                print(f"triggered on the button: {control_name}", ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
                return True
        elif control_type == "Edit":
            if input("Enter = ") == "1":
                control['control'].set_text("hi")
                print(f"triggered on the button: {control_name}", ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
                return True
    except Exception as e:
        print(f"not able to click. because I think it doesn't support invoke. Clicked on the button: {control_name}",
              "Error:", e, "--------------------------------------------")
        return False


def click_buttonByValue(control, _input):
    control_type = control.get('Control Type >>>> ')
    control_name = control.get('Control Name >>>> ')

    try:
        if control_type in ["Button", "Hyperlink", "ListItem", "MenuItem"] and _input.lower() == control_name.lower():
            control['control'].invoke()
            print(f"triggered on the button: {control_name}", ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
            return True
        elif control_type in ["CheckBox", "RadioButton"] and _input.lower() == control_name.lower():
            control['control'].set_check(input("enter true or false for 1") == "1")
            print(f"triggered on the button: {control_name}", ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
            return True
        elif control_type == "Edit" and _input.lower() == control_name.lower():
            control['control'].set_text(input("enter text: "))
            print(f"triggered on the button: {control_name}", ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
            return True
    except Exception as e:
        print(f"not able to click. because I think it doesn't support invoke. Clicked on the button: {control_name}",
              "Error:", e, "--------------------------------------------")
        return False


def print_children_components(control, data_list, indent=0):
    try:
        control_type = control.element_info.control_type
        control_name = control.window_text()
    except Exception:
        return  # Skip this control if there is an issue

    control_dict = {'Control Type >>>> ': control_type, 'Control Name >>>> ': control_name, 'control': control}

    try:
        for child in control.children():
            print_children_components(child, data_list, indent + 1)
    except Exception:
        pass  # Handle any exceptions while processing children

    data_list.append(control_dict)


def click_buttons_in_controls(controls, _input):
    for control in controls:
        res = click_buttonByValue(control, _input) if _input else click_button(control)
        if res:
            return True
        try:
            child_controls = control['control'].children()
            if click_buttons_in_controls(child_controls, _input):
                return True
        except Exception:
            pass  # Handle any exceptions while processing children


def print_controls_in_right_side_part():
    desktop = pywinauto.Desktop(backend="uia")
    system_window = desktop.window(title="Settings", control_type="Window")
    try:
        system_window.wait("visible", timeout=10)
    except Exception:
        print("Window not found. Open settings and try again.")
        return []

    data_list = []
    try:
        controls = system_window.descendants()
        for control in controls:
            print_children_components(control, data_list)
    except Exception:
        pass  # Handle any exceptions while processing controls

    return data_list


def main(_input):
    result_list = print_controls_in_right_side_part()
    click_buttons_in_controls(result_list, _input)


if __name__ == "__main__":
    while True:
        _input = input("<<<<<<<<<<<<<<<<<<<<<<<<<<Thippeswamy>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
        main(_input)
