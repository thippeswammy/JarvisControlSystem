import os


def open_notification_settings():
    try:
        os.system("start ms-settings:notifications")
        print("Notification settings opened.")
    except Exception as e:
        print(f"Failed to open notification settings. Error: {e}")


# Call the function to open notification settings
open_notification_settings()
