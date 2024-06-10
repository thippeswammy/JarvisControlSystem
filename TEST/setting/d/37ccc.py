import os


def open_system_settings():
    try:
        os.system("start ms-settings:system")
        print("System Settings opened.")
    except Exception as e:
        print(f"Failed to open System Settings. Error: {e}")


# Call the function to open System Settings
open_system_settings()
