import time
import keyboard
import pywinauto


def open_windows_settings():
    # Send the keyboard shortcut to open Windows Settings (Win + I)
    keyboard.press_and_release('win+i')
    time.sleep(2)  # Wait for the Settings app to open


def click_button_by_name(window, button_name):
    # Find the button by its name
    button = window.child_window(title=button_name, control_type="Button")

    if button.exists():
        # Click the button
        button.click_input()
        print(f"Clicked on the button: {button_name}")
    else:
        print(f"Button not found: {button_name}")


def navigate_to_system_category():
    # Send keyboard shortcuts to navigate to the "System" category
    keyboard.press_and_release('tab')  # Move to the categories list
    time.sleep(1)
    keyboard.press_and_release('down')  # Select the first category
    time.sleep(1)
    keyboard.press_and_release('down')  # Select the second category (System)
    time.sleep(1)
    keyboard.press_and_release('enter')  # Open the selected category


if __name__ == "__main__":
    open_windows_settings()
    # navigate_to_system_category()

    # Connect to the desktop
    desktop = pywinauto.Desktop(backend="uia")

    # Try to find the "System" window
    system_window = desktop.window(title="Settings", control_type="Window")
    system_window.wait("visible", timeout=10)

    # Click on a button (replace "Your Button Name" with the actual name of the button)
    button_name_to_click = "Apps"
    click_button_by_name(system_window, button_name_to_click)
