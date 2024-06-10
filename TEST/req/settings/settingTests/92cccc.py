import time
import pywinauto
from pywinauto import Desktop


# Function to get element info as a tuple
def get_element_info(element):
    control_type = element.element_info.control_type
    window_text = element.window_text()
    return (control_type, window_text)


# Function to traverse elements and store them in a nested list
def traverse_elements(element, depth=0):
    element_info = get_element_info(element)
    children = []
    for child in element.children():
        children.append(traverse_elements(child, depth + 1))
    return [element_info, children]


# Function to print the nested list in a readable format
def print_nested_list(nested_list, depth=0):
    indent = ' ' * depth * 4
    element_info, children = nested_list
    print(f"{indent}{element_info[0]}: {element_info[1]}")
    for child in children:
        print_nested_list(child, depth + 1)


# Open Settings application
settings_path = r'C:\Windows\ImmersiveControlPanel\SystemSettings.exe'
app = pywinauto.Application(backend='uia').start(settings_path)
time.sleep(3)  # Wait for the application to open

# Connect to the Settings window
settings_window = Desktop(backend='uia').window(title_re='Settings')

# Traverse and save UI elements in a nested list
ui_hierarchy = traverse_elements(settings_window)

# Close the Settings application
settings_window.close()

# Print the nested list in a readable format
print_nested_list(ui_hierarchy)

'''
Window: Settings
    Window: Settings
        MenuBar: System
            MenuItem: System
        Button: Minimize Settings
        Button: Maximize Settings
        Button: Close Settings
    Window: Settings
        Text: Settings
        Custom: 
            Button: Back
            Window: 
                Button: Thippeswammy k.s thippeswamy636408@gmail.com
                    Image: User profile picture
                    Text: Thippeswammy k.s
                    Text: thippeswamy636408@gmail.com
                Group: 
                    Edit: 
                        Text: Find a setting
                Pane: 
                    Group: 
                        ListItem: Home
                            Image: 
                        ListItem: System
                            Image: 
                        ListItem: Bluetooth & devices
                            Image: 
                        ListItem: Network & internet
                            Image: 
                        ListItem: Personalization
                            Image: 
                        ListItem: Apps
                            Image: 
                        ListItem: Accounts
                            Image: 
                        ListItem: Time & language
                            Image: 
                        ListItem: Gaming
                            Image: 
                        ListItem: Accessibility
                            Image: 
                        ListItem: Privacy & security
                            Image: 
                        ListItem: Windows_icon Update
                            Image: 
                    ScrollBar: Vertical
                Pane: 
                    Group: 
            Group: 
                Button: Home
                    Text: Home
            Group: 
                Pane: 
                    Image: Desktop preview
                    Group: ASUS_Windows
                        Text: ASUS_Windows
                        Text: Vivobook_ASUSLaptop M6500QC_M6500QC
                        Hyperlink: Rename
                    Button: redmi Connected, secured
                        Text: redmi
                        Text: Connected, secured
                    Button: Windows_icon Update Last checked: 1 hour ago
                        Text: Windows_icon Update
                        Text: Last checked: 1 hour ago
                    Group: Recommended settings
                        Text: Recommended settings
                        Text: Recent and commonly used settings
                        List: 
                            ListItem: Wi-Fi
                                Group: Wi-Fi
                                    Text: Wi-Fi
                                    Button: Wi-Fi
                            ListItem: Display
                                Group: Display
                                    Text: Display
                            ListItem: Installed apps
                                Group: Installed apps
                                    Text: Installed apps
                    Group: Cloud storage
                        Text: Cloud storage
                        Text: With available storage, you can back up files or send and receive email on Outlook.
                        Text: < 0.1 GB used of 5 GB (1%)
                        Button: PC backup
                            Text: PC backup
                            Text: Partially backed up
                        Button: Manage cloud storage
                            Text: Manage cloud storage
                    Group: Bluetooth devices
                        Text: Bluetooth devices
                        Text: Manage, add, and remove devices
                        Text: Bluetooth
                        Text: Bluetooth is turned off
                        Button: Bluetooth
                        List: 
                            ListItem: Realme C35, Category Phone, Battery Unknown, State Bluetooth is turned off, 
                                Group: Realme C35, Category Phone, Battery Unknown, State Bluetooth is turned off, 
                                    Text: Realme C35
                                    Text: Bluetooth is turned off
                                    Button: More options
                        Group: View all devices
                            Text: View all devices
                            Button: Add device
                            Button: More
                    Group: Personalize your device
                        Text: Personalize your device
                        List: Select a theme to apply
                            ListItem: Windows_icon (light), 1 images
                                Group: Windows_icon (light), 1 images
                            ListItem: Windows_icon (dark), 1 images
                                Group: Windows_icon (dark), 1 images
                            ListItem: Windows_icon spotlight, dynamic images
                                Group: Windows_icon spotlight, dynamic images
                                    Image: Windows_icon spotlight icon
                            ListItem: Glow, 4 images
                                Group: Glow, 4 images
                            ListItem: Captured Motion, 4 images
                                Group: Captured Motion, 4 images
                            ListItem: Sunrise, 4 images
                                Group: Sunrise, 4 images
                        Text: Color mode
                        ComboBox: Color mode
                            ListItem: Dark
                                Text: Dark
                        Group: Browse more backgrounds, colors, and themes
                            Text: Browse more backgrounds, colors, and themes
                            Button: More
                    Group: Microsoft Copilot Pro
                        Text: Microsoft Copilot Pro
                        Text: Experience exclusive productivity features when you unlock Copilot in Word, PowerPoint, and more.
                        Button: Try Copilot Pro
                            Text: Try Copilot Pro
                        Hyperlink: What’s included in Copilot Pro?
                            Text: What’s included in Copilot Pro?
                    Group: Get help
                        Hyperlink: Get help
                            Text: Get help
                    Group: Give feedback
                        Hyperlink: Give feedback
                            Text: Give feedback
                    ScrollBar: Vertical
                        Button: Vertical Small Decrease
                        Button: Vertical Large Decrease
                        Button: Vertical Large Increase
                        Button: Vertical Small Increase
    Pane: 

Process finished with exit code 0
i want like: Window: Settings =[]
'''
