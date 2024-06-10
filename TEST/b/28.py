from pywinauto import Application

# Open the Settings app manually and get its window handle
settings_app = Application(backend='uia').connect(title='Settings')

# Access the Settings window
settings_window = settings_app.window(title='Settings')

# Access all the buttons in the Settings window
buttons = settings_window.descendants(control_type='Button')

# Get the names of all the buttons
button_names = [button.window_text() for button in buttons]

# Print the names of all the buttons
for name in button_names:
    print(name)
