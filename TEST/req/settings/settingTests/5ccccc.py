import time
import keyboard
import pywinauto
from pywinauto import mouse


def open_windows_settings():
    # Send the keyboard shortcut to open Windows_icon Settings (Win + I)
    keyboard.press_and_release('win+i')
    time.sleep(2)  # Wait for the Settings app to open


def move_mouse_to_button(control):
    rect = control.rectangle()
    x = (rect.left + rect.right) // 2
    y = (rect.top + rect.bottom) // 2
    # if control['Control Type'] in ['ListItem'] and x>1000:
    # scroll vertical
    # print("x =", x, "y =", y)
    mouse.move(coords=(x, y))


def click_button(control):
    control_type = control.get('Control Type')
    control_name = control.get('Control Name')
    control_ = control.get('control')

    if control_type in ["Button", "Hyperlink", "MenuItem", "ListItem", "CheckBox", "RadioButton", "Edit", "Slider"]:
        print('<' * 80, '>' * 80)
    try:
        if control_type in ["Button", "Hyperlink", "MenuItem", "ListItem"]:
            move_mouse_to_button(control['control'])
            control['control'].invoke()
            rect = control['control'].rectangle()
            print("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<",
                  f"Triggered action on: {control_name} at position: {rect}",
                  ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
            return True
        elif control_type in ["CheckBox", "RadioButton"]:
            move_mouse_to_button(control['control'])
            control['control'].set_check()
            rect = control['control'].rectangle()
            print("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<",
                  f"Triggered action on: {control_name} at position: {rect}",
                  ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
            return True
        elif control_type == "Edit":
            text = input(f"Enter text to input into {control_name} >>> ")
            move_mouse_to_button(control['control'])
            control_.set_text(text)
            rect = control['control'].rectangle()
            print("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<",
                  f"Triggered action on: {control_name} at position: {rect}",
                  ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
            return True
        elif control_type == "Slider":
            value = input(f"Enter value to set the slider {control_name} >>> ")
            move_mouse_to_button(control['control'])
            control_.set_value(int(value))
            rect = control['control'].rectangle()
            print("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<",
                  f"Set slider value on: {control_name} at position: {rect}",
                  ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
            return True
    except Exception as e:
        print(
            f"----------------------  Not able to perform action on | control_name = {control_name} | control_type = "
            f"{control_type} | control = {control_} | ",
            "Error ", e,
            "----------------------")
        return False


def click_button_by_value(control, _input):
    control_type = control.get('Control Type')
    control_name = control.get('Control Name')
    control_ = control.get('control')
    try:
        if control_type in ["Button", "Hyperlink", "ListItem"]:
            if _input.lower() == control_name.lower():
                move_mouse_to_button(control['control'])
                control['control'].invoke()
                rect = control['control'].rectangle()
                print(f"Triggered action on: {control_name} at position: {rect}",
                      ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
                return True
        elif control_type in ["CheckBox", "RadioButton"]:
            if _input.lower() == control_name.lower():
                move_mouse_to_button(control['control'])
                control['control'].set_check(input("Enter true or false for 1") == "1")
                rect = control['control'].rectangle()
                print(f"Triggered action on: {control_name} at position: {rect}",
                      ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
                return True
        elif control_type == "Edit":
            text = input(f"Enter text to input into {control_name} >>> ")
            move_mouse_to_button(control['control'])
            control_.set_text(text)
            rect = control['control'].rectangle()
            print(f"Triggered action on: {control_name} at position: {rect}",
                  ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
            return True
        elif control_type == "Slider":
            value = input(f"Enter value to set the slider {control_name} >>> ")
            move_mouse_to_button(control['control'])
            control_.set_value(int(value))
            rect = control['control'].rectangle()
            print(f"Set slider value on: {control_name} at position: {rect}",
                  ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
            return True
        if control_type == "MenuItem" and 'Invoke' in control['control'].patterns():
            if _input.lower() == control_name.lower():
                move_mouse_to_button(control['control'])
                control['control'].invoke()
                rect = control['control'].rectangle()
                print(f"Clicked on the MenuItem: {control_name} at position: {rect}",
                      ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
                return True
    except Exception as e:
        print(
            f"----------------------  Not able to perform action on | control_name = {control_name} | control_type = "
            f"{control_type} | control = {control_} | ",
            "Error ", e,
            "----------------------")
        return False


def print_children_components(control, data_list, data_list_main, seen_controls, indent=0):
    try:
        control_type = control.element_info.control_type
        control_name = control.window_text()
    except Exception:
        return  # Skip this control if there is an issue

    if control_type in ["Text", 'Group', 'Custom'] or control_name in ['']:
        return  # Skip adding Text type controls
    if control_type in ["Text"] or control_name in ['']:
        return
    control_dict = {'Control Type': control_type, 'Control Name': control_name, 'control': control}

    if (control_name, control_type) not in seen_controls:
        seen_controls.add((control_name, control_type))
        data_list.append(control_dict)

    try:
        for child in control.children():
            print_children_components(child, data_list, seen_controls, indent + 1)
    except Exception:
        pass  # Handle any exceptions while processing children


def click_buttons_in_controls(controls, _input):
    for control in controls:
        res = click_button_by_value(control, _input) if _input else click_button(control)
        if res:
            return True
        try:
            children = control['control'].children()
            if children:
                if click_buttons_in_controls(children, _input):
                    return True
        except Exception:
            pass  # Handle any exceptions while processing children


def print_controls_in_right_side_part():
    desktop = pywinauto.Desktop(backend="uia")
    system_window = desktop.window(title="Settings", control_type="Window")

    try:
        system_window.wait("visible", timeout=10)
    except Exception:
        print("Window not found. Open Settings and try again")
        return []

    data_list = []
    data_list_main = []
    seen_controls = set()

    try:
        controls = system_window.descendants()
        for control in controls:
            print_children_components(control, data_list, data_list_main, seen_controls)
    except Exception:
        pass  # Handle any exceptions while processing controls

    return data_list, data_list_main


def remove_item(AllControls):
    remove_item = ["Window Settings", 'MenuBar System', 'MenuItem System', 'Button Minimize Settings',
                   'Button Maximize Settings', 'Button Close Settings', 'ListItem Apps',
                   'Button Thippeswammy k.s thippeswamy636408@gmail.com', 'Image User profile picture',
                   'ListItem Home', 'ListItem System', 'ListItem Bluetooth & devices', 'ListItem Network & internet',
                   'ListItem Personalization', 'ListItem Accounts', 'ListItem Time & language', 'ListItem Gaming',
                   'ListItem Accessibility', 'ListItem Privacy & security', 'ListItem Windows_icon Update']
    new_control = []
    for i in AllControls:
        if i["Control Type"] + " " + i["Control Name"] not in remove_item:
            new_control.append(i)
    return new_control


def main():
    time.sleep(5)
    while True:
        AllControls, MainControls = print_controls_in_right_side_part()
        new_control = remove_item(AllControls)
        if len(new_control) > 0:
            AllControls = new_control
        for i, val in enumerate(AllControls):
            print(i + 1, ":", val["Control Type"], "|", val["Control Name"])
        #     move_mouse_to_button(val['control'])
        #     time.sleep(2)
        inputVal = 0
        while True:
            try:
                inputVal = int(input("Thippeswamy ===>>>"))
                print('<' * 80, '>' * 80)
                if 0 < inputVal <= len(AllControls):
                    break
            except:
                pass
        click_button(AllControls[inputVal - 1])
        print('<' * 80, '>' * 80)


if __name__ == "__main__":
    open_windows_settings()
    main()
