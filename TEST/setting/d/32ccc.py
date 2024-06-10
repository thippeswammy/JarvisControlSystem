import os


def open_battery_settings():
    try:
        os.system("start ms-settings:batterysaver-settings")
        print("Battery settings opened.")
    except Exception as e:
        print(f"Failed to open Battery settings. Error: {e}")


# Call the function to open Battery settings
open_battery_settings()
