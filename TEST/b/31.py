from pywinauto import Application

# Connect to the Windows Settings window
settings_app = Application(backend='uia').connect(title='Settings')

# Access the Settings window
settings_window = settings_app.window(title='Settings')

# Get all elements within the Settings window
elements = settings_window.children()

# Iterate through the elements and print their names
for element in elements:
    try:
        element_name = element.window_text()
        control_type = element.element_info.control_type
        print(f"Control Type: {control_type}, Name/Text: {element_name}")
    except Exception as e:
        print(f"Error accessing element: {e}")
