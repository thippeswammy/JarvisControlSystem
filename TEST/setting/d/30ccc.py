import os


def open_focus_assist_settings():
    try:
        os.system("start ms-settings:quiethours")
        print("Focus Assist settings opened.")
    except Exception as e:
        print(f"Failed to open Focus Assist settings. Error: {e}")


# Call the function to open Focus Assist settings
open_focus_assist_settings()
