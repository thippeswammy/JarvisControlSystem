import os


def open_power_and_sleep_settings():
    try:
        os.system("start ms-settings:powersleep")
        print("Power & sleep settings opened.")
    except Exception as e:
        print(f"Failed to open Power & sleep settings. Error: {e}")


# Call the function to open Power & sleep settings
open_power_and_sleep_settings()
