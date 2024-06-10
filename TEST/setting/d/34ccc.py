import os


def open_tablet_settings():
    try:
        os.system("start ms-settings:tabletmode")
        print("Tablet settings opened.")
    except Exception as e:
        print(f"Failed to open Tablet settings. Error: {e}")


# Call the function to open Tablet settings
open_tablet_settings()
