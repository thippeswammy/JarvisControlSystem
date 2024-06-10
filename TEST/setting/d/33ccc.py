import os


def open_storage_settings():
    try:
        os.system("start ms-settings:storagesense")
        print("Storage settings opened.")
    except Exception as e:
        print(f"Failed to open Storage settings. Error: {e}")


# Call the function to open Storage settings
open_storage_settings()
