import os


def open_clipboard_settings():
    try:
        os.system("start ms-settings:clipboard")
        print("Clipboard Settings opened.")
    except Exception as e:
        print(f"Failed to open Clipboard Settings. Error: {e}")


# Call the function to open Clipboard Settings
open_clipboard_settings()
