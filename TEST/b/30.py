from pywinauto import Application

# Connect to the Windows Settings window
settings_app = Application(backend='uia').connect(title='Settings')

# Access the Settings window
settings_window = settings_app.window(title='Settings')

# Get all buttons, labels, and panels within the Settings window
buttons = settings_window.descendants(control_type='Button')
labels = settings_window.descendants(control_type='Text')
panels = settings_window.descendants(control_type='Pane')

# Print the names of buttons
print("Buttons:")
for button in buttons:
    print(button.window_text())

# Print the names of labels
print("\nLabels:")
for label in labels:
    print(label.window_text())

# Print the names of panels
print("\nPanels:")
for panel in panels:
    print(panel.window_text())
