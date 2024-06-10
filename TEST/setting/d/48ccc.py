import os
from time import sleep


def open_setting(setting):
    settings_map = {
        "date_and_time": "ms-settings:dateandtime",
        "region": "ms-settings:regionlanguage",
        "language": "ms-settings:regionlanguage-language",
        "speech": "ms-settings:speech"
        # Add more settings as needed
    }

    setting_uri = settings_map.get(setting.lower())
    if setting_uri:
        os.system(f"start {setting_uri}")
        print(f"{setting.capitalize()} Setting opened.")
        sleep(1)
    else:
        print(f"Unsupported setting: {setting}")


# Example usage:
open_setting("date_and_time")
open_setting("region")
open_setting("language")
open_setting("speech")
# Add more calls as needed
