from pywinauto import Application

# Connect to the Windows Settings window
settings_app = Application(backend='uia').connect(title='Settings')

# Access the Settings window
settings_window = settings_app.window(title='Settings')

# Get all labels and panes within the Settings window
labels = settings_window.descendants(control_type='Text')
panes = settings_window.descendants(control_type='Pane')
buttons = settings_window.descendants(control_type='Button')


# Define a function to click on a label or pane by text
def click_label_or_pane(label_text):
    for label in labels:
        if label.window_text() == label_text:
            label.click_input()  # Try clicking on the label
            break

    for pane in panes:
        if pane.window_text() == label_text:
            pane.click_input()  # Try clicking on the pane
            break

    for pane in buttons:
        if pane.window_text() == label_text:
            pane.click_input()  # Try clicking on the pane
            break


# Label or Pane texts to interact with
elements_to_click = [
    'My Microsoft account',
    'System',
    'Personalization'
    # Add more label or pane texts as needed based on your requirements
]

click_label_or_pane(elements_to_click[0])
# Click the specified labels or panes
"""  

for element_text in elements_to_click:
    click_label_or_pane(element_text)
    
"""
