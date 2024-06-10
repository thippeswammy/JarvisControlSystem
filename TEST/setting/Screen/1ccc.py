import time

import pyautogui


def open_windows_settings():
    try:
        # Capture the screen and get the coordinates of the Windows icon on the taskbar
        screen = pyautogui.screenshot()
        windows_icon_location = pyautogui.locateOnScreen(r'F:\Pycham_programs\Jarvis55\Windows\cmd_logo.png')

        if windows_icon_location is not None:
            # Calculate the center coordinates of the Windows icon
            windows_icon_center = pyautogui.center(windows_icon_location)

            # Move the mouse to the Windows icon and click
            pyautogui.moveTo(windows_icon_center)
            pyautogui.click()

            # Wait for the Start menu to open
            time.sleep(1)

            # Type "Settings" in the search bar
            pyautogui.write("Settings")

            # Press Enter to open the Settings
            pyautogui.press('enter')

            print("Windows Settings opened.")
        else:
            print("Windows icon not found on the taskbar.")

    except Exception as e:
        print(f"Failed to open Windows Settings. Error: {e}")


# Call the function to open the Windows Settings
open_windows_settings()
