import os

def open_multiple_display_settings():
    try:
        os.system("start ms-settings:display-multiple")
        print("Multiple displays settings opened.")
    except Exception as e:
        print(f"Failed to open Multiple displays settings. Error: {e}")

# Call the function to open the Multiple displays settings
# open_multiple_display_settings()
import os

def open_scale_and_layout_settings():
    try:
        os.system("start ms-settings:display")
        print("Scale and layout settings opened.")
    except Exception as e:
        print(f"Failed to open Scale and layout settings. Error: {e}")

# Call the function to open the Scale and layout settings
open_scale_and_layout_settings()

