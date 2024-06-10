from pywinauto import Application
import time

def open_windows_settings():
    # Run the Windows Settings app
    app = Application(backend='uia')
    app.start('ms-settings:')

    # Wait for the Settings app to open
    time.sleep(2)

def navigate_to_system_category():
    # Specify the title of the main window
    main_window_title = "Settings"

    # Connect to the desktop
    desktop = Application(backend="uia").connect(title=main_window_title)

    # Navigate to the "System" category
    system_button = desktop[main_window_title].System
    system_button.click()

def print_buttons_in_system_category():
    # Connect to the desktop
    desktop = Application(backend="uia").connect(title="Settings")

    # Get the System category window
    system_window = desktop.window(title="System", control_type="Window")

    # Find and print the names of all buttons in the System category
    buttons = system_window.descendants(control_type="Button")
    for button in buttons:
        button_name = button.window_text()
        print(f"Button Name: {button_name}")

if __name__ == "__main__":
    open_windows_settings()
    navigate_to_system_category()
    print_buttons_in_system_category()
