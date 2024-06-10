import os
from time import sleep


def open_personalization_setting(setting):
    try:
        settings_map = {
            "personalization": "ms-settings:personalization",
            "background": "ms-settings:personalization-background",
            "colors": "ms-settings:personalization-colors",
            "lock_screen": "ms-settings:lockscreen",
            "themes": "ms-settings:themes",
            "fonts": "ms-settings:fonts",
            "start": "ms-settings:start",
            "taskbar": "ms-settings:taskbar"
            # Add more settings as needed
        }

        if setting.lower() in settings_map:
            os.system(f"start {settings_map[setting.lower()]}")
            print(f"{setting.capitalize()} Settings opened.")
            sleep(2)
        else:
            print(f"Unsupported personalization setting: {setting}")


    except Exception as e:
        print(f"Failed to open personalization settings. Error: {e}")


# Examples:
open_personalization_setting("personalization")
open_personalization_setting("background")
open_personalization_setting("colors")
open_personalization_setting("lock_screen")
open_personalization_setting("themes")
open_personalization_setting("fonts")
open_personalization_setting("start")
open_personalization_setting("taskbar")
