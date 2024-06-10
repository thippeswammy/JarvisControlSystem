import pywinauto
from pywinauto import Desktop, Application
from pywinauto.findwindows import ElementNotFoundError
import time


# Function to get element info as a tuple
def get_element_info(element):
    control_type = element.element_info.control_type
    window_text = element.window_text()
    return control_type, window_text, element


# Function to traverse elements and store them in a nested list
def traverse_elements(element, depth=0):
    element_info = get_element_info(element)
    children = []
    for child in element.children():
        children.append(traverse_elements(child, depth + 1))
    return [element_info, children, depth]


# Function to print the nested list in a readable format
def print_nested_list(nested_list, filter_types=None):
    element_info, children, depth = nested_list
    if filter_types is None or element_info[0] in filter_types:
        indent = ' ' * depth * 4
        print(f"{indent}{element_info[0]}: {element_info[1]} [Depth: {depth}]")
    for child in children:
        print_nested_list(child, filter_types)


# Function to print all buttons within the first "Group" of depth 3
def print_first_group_buttons(nested_list):
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
    if first_group:
        element_info, children, depth = first_group
        for child in children:
            child_info, _, child_depth = child
            if child_info[0] == 'Button':
                indent = ' ' * child_depth * 4
                print(f"{indent}{child_info[0]}: {child_info[1]} [Depth: {child_depth}]")


# Open Settings application
settings_path = r'C:\Windows\ImmersiveControlPanel\SystemSettings.exe'
app = Application(backend='uia').start(settings_path)
time.sleep(5)  # Wait for the application to open

# Connect to the Settings window with the correct title
try:
    settings_window = Desktop(backend='uia').window(title='Settings', top_level_only=True)
except ElementNotFoundError:
    print("Settings window not found. Please check the window title and ensure the application is open.")
    exit(1)

# Traverse and save UI elements in a nested list
ui_hierarchy = traverse_elements(settings_window)

# Close the Settings application
settings_window.close()

# Print the nested list in a readable format, filtering only for 'Button' and 'Group' elements
print_nested_list(ui_hierarchy, filter_types={'Button', 'Group'})

# Print all buttons within the first "Group" of depth 3
print("\nSpecial Output: Buttons within the first 'Group' of depth 3")
print_first_group_buttons(ui_hierarchy)
