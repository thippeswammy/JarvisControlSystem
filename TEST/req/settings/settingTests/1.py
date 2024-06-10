import pywinauto
from pywinauto import Desktop, Application
from pywinauto.findwindows import ElementNotFoundError


def get_present_location_in_setting(settings_path=r'C:\Windows\ImmersiveControlPanel\SystemSettings.exe',
                                    window_title='Settings', max_depth=5):
    # Function to get element info as a tuple
    def get_element_info(element):
        control_type = element.element_info.control_type
        window_text = element.window_text()
        return control_type, window_text, element

    # Function to traverse elements and store them in a nested list
    def traverse_elements(element, depth=0):
        if depth > max_depth:
            return None
        element_info = get_element_info(element)
        children = []
        for child in element.children():
            child_elements = traverse_elements(child, depth + 1)
            if child_elements:
                children.append(child_elements)
        return [element_info, children, depth]

    # Function to find the first "Group" of depth 3 and retrieve buttons
    def get_first_group_buttons(nested_list):
        def find_first_group_at_depth(nested_list, target_depth):
            element_info, children, depth = nested_list
            if element_info[0] == 'Group' and depth == target_depth:
                return nested_list
            for child in children:
                result = find_first_group_at_depth(child, target_depth)
                if result:
                    return result
            return None

        first_group = find_first_group_at_depth(nested_list, 3)
        buttons = []
        if first_group:
            element_info, children, depth = first_group
            for child in children:
                child_info, _, child_depth = child
                if child_info[0] == 'Button':
                    buttons.append(child_info)
        return buttons

    # Function to find the first "Window" of depth 1 and retrieve its button elements, including "Back" button
    def get_first_window_buttons(nested_list):
        def find_first_window_at_depth(nested_list, target_depth):
            element_info, children, depth = nested_list
            if element_info[0] == 'Window' and depth == target_depth:
                return nested_list
            for child in children:
                result = find_first_window_at_depth(child, target_depth)
                if result:
                    return result
            return None

        first_window = find_first_window_at_depth(nested_list, 1)
        buttons = []
        if first_window:
            element_info, children, depth = first_window
            for child in children:
                child_info, _, child_depth = child
                if child_info[0] == 'Button' and (child_info[1] == 'Back' or depth == 1):
                    buttons.append((child_info, child_depth))
        return buttons

    # Open Settings application
    Application(backend='uia').start(settings_path)
    # time.sleep(3)  # Reduced wait time

    # Connect to the Settings window with the correct title
    try:
        settings_window = Desktop(backend='uia').window(title=window_title, top_level_only=True)
    except ElementNotFoundError:
        print("Settings window not found. Please check the window title and ensure the application is open.")
        return

    # Traverse and save UI elements in a nested list with a limited depth
    ui_hierarchy = traverse_elements(settings_window)

    # Get the buttons within the first "Group" of depth 3
    buttons = get_first_group_buttons(ui_hierarchy)

    # Get the button elements within the first "Window" of depth 1
    window_buttons = get_first_window_buttons(ui_hierarchy)

    # Print the button elements within the first "Window" of depth 1
    window_buttons_output = []
    for element_info, depth in window_buttons:
        indent = ' ' * depth * 4
        window_buttons_output.append(f"{indent}{element_info[0]}: {element_info[1]} [Depth: {depth}]")

    # Print the special output
    if buttons:
        button_names = [i[1] for i in buttons]
        if len(button_names) > 1:
            location_output = f"Settings => {' => '.join(button_names)}"
            location_output_sign = f"Settings {' '.join(button_names)}"
        else:
            location_output = f"Settings => {button_names[0]}"
            location_output_sign = f"Settings {button_names[0]}"
        return location_output, location_output_sign, buttons, window_buttons_output
    else:
        return "I am not able to find any buttons, there may be various reasons.", [], window_buttons_output


# Example usage:
result = get_present_location_in_setting()
if result:
    location_output, location_output_sign, buttons, window_buttons_output = result
    print(location_output)
    print(location_output_sign)
    for element in window_buttons_output:
        print(element)
