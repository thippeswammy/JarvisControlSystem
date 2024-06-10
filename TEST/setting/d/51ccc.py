import os
from time import sleep


def open_search_settings(setting):
    settings_map = {
        "search": "ms-settings:cortana",
        "permissions_and_history": "ms-settings:privacy-history",
        "searching_windows": "ms-settings:search"
        # Add more settings as needed
    }

    if setting.lower() in settings_map:
        os.system(f"start {settings_map[setting.lower()]}")
        print(f"{setting.capitalize()} Settings opened.")
        sleep(1)
    else:
        print(f"Unsupported search setting: {setting}")


# Example usage:
# open_search_settings("search")
# open_search_settings("permissions_and_history")
open_search_settings("searching_windows")
# Add more calls as needed
