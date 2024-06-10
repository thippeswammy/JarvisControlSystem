import pywinauto
import time
import keyboard

def open_windows_settings():
    # Send the keyboard shortcut to open Windows Settings (Win + I)
    keyboard.press_and_release('win+i')
    time.sleep(2)  # Wait for the Settings app to open

def navigate_to_system_category():
    # Send keyboard shortcuts to navigate to the "System" category
    keyboard.press_and_release('tab')  # Move to the categories list
    time.sleep(1)
    keyboard.press_and_release('down')  # Select the first category
    time.sleep(1)
    keyboard.press_and_release('down')  # Select the second category (System)
    time.sleep(1)
    keyboard.press_and_release('enter')  # Open the selected category

def print_buttons_in_system_category():
    # Connect to the desktop
    desktop = pywinauto.Desktop(backend="uia")

    # Try to find the "System" window
    system_window = desktop.window(title="Settings", control_type="Window")
    system_window.wait("visible", timeout=10)

    # Find and print the names of all buttons in the System category
    buttons = system_window.descendants(control_type="Button")

    lable = system_window.descendants(control_type="Lable")
    for button in buttons:
        button_name = button.window_text()
        print(f"Button Name: {button_name}")

if __name__ == "__main__":
    open_windows_settings()
    navigate_to_system_category()
    print_buttons_in_system_category()
