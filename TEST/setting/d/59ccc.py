def open_brightness_and_color_setting():
    try:
        os.system("start ms-settings:display-brightnesscolor")
        print("Brightness and Color Setting opened.")
    except Exception as e:
        print(f"Failed to open Brightness and Color Setting. Error: {e}")


# Call the function to open the Brightness and Color settings
# open_brightness_and_color_setting()

import os


def open_multiple_display_settings():
    try:
        os.system("start ms-settings:display-advanced")
        print("Multiple displays settings opened.")
    except Exception as e:
        print(f"Failed to open Multiple displays settings. Error: {e}")


# Call the function to open the Multiple displays settings
open_multiple_display_settings()
