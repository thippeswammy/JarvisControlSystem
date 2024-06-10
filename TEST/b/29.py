from pywinauto import Application

# Start the Settings app
app = Application(backend='uia').start('ms-settings:')

# Wait for the Settings window to be ready
settings_window = app.window(title='Settings')
settings_window.wait('ready')

# Access all buttons in the Settings window
buttons = settings_window.descendants(control_type='Button')

# Retrieve and print the names of all buttons
button_names = [button.window_text() for button in buttons]
for name in button_names:
    print(name)
