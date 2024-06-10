import os
from time import sleep


def open_setting(setting):
    settings_map = {
        "apps_and_features": "ms-settings:appsfeatures",
        "default_apps": "ms-settings:defaultapps",
        "offline_maps": "ms-settings:maps",
        "apps_for_websites": "ms-settings:appsforwebsites",
        "video_playback": "ms-settings:videoplayback",
        "startup_apps": "ms-settings:startupapps"
        # Add more settings as needed
    }

    setting_uri = settings_map.get(setting.lower())
    if setting_uri:
        os.system(f"start {setting_uri}")
        print(f"{setting.capitalize()} Setting opened.")
        sleep(2)
    else:
        print(f"Unsupported setting: {setting}")


# Example usage:
open_setting("apps_and_features")
open_setting("default_apps")
open_setting("offline_maps")
open_setting("apps_for_websites")
open_setting("video_playback")
open_setting("startup_apps")
# Add more calls as needed
