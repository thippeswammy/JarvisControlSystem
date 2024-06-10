from pywinauto import Application

# Connect to the Windows Settings window
settings_app = Application(backend='uia').connect(title='Settings')

# Access the Settings window
settings_window = settings_app.window(title='Settings')

# Get all buttons and labels within the Settings window
buttons = settings_window.descendants(control_type='Button')
labels = settings_window.descendants(control_type='Text')


# Function to find and interact with specific buttons
def find_and_click_button(button_text):
    for button in buttons:
        if button.window_text() == button_text:
            button.click()
            break


# List all the labels
print("Labels:")
for label in labels:
    print(label.window_text())

# Click specific buttons
# find_and_click_button('Minimize Settings')
find_and_click_button('Maximize Settings')
# find_and_click_button('Close Settings')
find_and_click_button("Let's go!")
