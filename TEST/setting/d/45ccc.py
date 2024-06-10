import os


def open_personalization_setting(setting):
    try:
        settings_map = {
            "personalization": "ms-settings:personalization",
            "background": "ms-settings:personalization-background",
            "colors": "ms-settings:personalization-colors",
            "lock_screen": "ms-settings:lockscreen",
            "themes": "ms-settings:themes",
            "fonts": "ms-settings:fonts",
            "start": "shell:::{2559a1f3-21d7-11d4-bdaf-00c04f60b9f0}",
            "taskbar": "ms-settings:taskbar"
            # Add more settings as needed
        }

        if setting.lower() in settings_map:
            os.system(f"start {settings_map[setting.lower()]}")
            print(f"{setting.capitalize()} Settings opened.")
        else:
            print(f"Unsupported personalization setting: {setting}")

    except Exception as e:
        print(f"Failed to open personalization settings. Error: {e}")


# Example:
open_personalization_setting("start")
