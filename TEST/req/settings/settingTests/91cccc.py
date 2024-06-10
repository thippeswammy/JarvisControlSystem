import time
import pywinauto
from pywinauto import Desktop
from pywinauto.controls.uiawrapper import UIAWrapper


def print_element_info(element, depth=0):
    indent = ' ' * depth * 4
    control_type = element.element_info.control_type
    window_text = element.window_text()
    print(f"{indent}{control_type}: {window_text}")


def traverse_elements(element, depth=0):
    print_element_info(element, depth)
    for child in element.children():
        traverse_elements(child, depth + 1)


# Open Settings application
settings_path = r'C:\Windows\ImmersiveControlPanel\SystemSettings.exe'
app = pywinauto.Application(backend='uia').start(settings_path)
time.sleep(3)  # Wait for the application to open

# Connect to the Settings window
settings_window = Desktop(backend='uia').window(title_re='Settings')

# Traverse and print UI elements
traverse_elements(settings_window)

# Close the Settings application
settings_window.close()
