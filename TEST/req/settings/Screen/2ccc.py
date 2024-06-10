import time

import pyautogui


def open_windows_settings():
    try:
        time.sleep(5)
        # Capture the screen and get the coordinates of the Windows_icon icon on the taskbar
        screen = pyautogui.screenshot()
        windows_icon_location = pyautogui.locateOnScreen(r'F:\Pycham_programs\Jarvis55\Windows\Setting\setting_change_brightness_for_the_built_in_display.png')

        if windows_icon_location is not None:
            # Calculate the center coordinates of the Windows_icon icon
            windows_icon_center = pyautogui.center(windows_icon_location)

            # Move the mouse to the Windows_icon icon and click
            pyautogui.moveTo(windows_icon_center)
            pyautogui.click()

            # Wait for the Start menu to open
            time.sleep(1)

            # Type "Settings" in the search bar
            # pyautogui.write("Settings")
            #
            # # Press Enter to open the Settings
            # pyautogui.press('enter')

            print("Windows_icon Settings opened.")
        else:
            print("Windows_icon icon not found on the taskbar.")

    except Exception as e:
        print(f"Failed to open Windows_icon Settings. Error: {e}")


# Call the function to open the Windows_icon Settings
open_windows_settings()
