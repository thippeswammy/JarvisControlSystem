import os


def open_display_settings(setting):
    display_settings_map = {
        "display": "ms-settings:display",
        "screen_resolution": "ms-settings:display-advancedprovisioning",
        "orientation": "ms-settings:display-orientation",
        "night_light": "ms-settings:nightlight",
        "project_to_this_pc": "ms-settings:project",
        # Add more display settings as needed
    }

    if setting.lower() in display_settings_map:
        os.system(f"start {display_settings_map[setting.lower()]}")
        print(f"{setting.capitalize()} Setting opened.")
    else:
        print(f"Unsupported Display setting: {setting}")


def open_sound_settings(setting):
    sound_settings_map = {
        "sound": "ms-settings:sound",
        "volume": "ms-settings:volume",
        "input_devices": "ms-settings:sound-input",
        "output_devices": "ms-settings:sound-output",
        # Add more sound settings as needed
    }

    if setting.lower() in sound_settings_map:
        os.system(f"start {sound_settings_map[setting.lower()]}")
        print(f"{setting.capitalize()} Setting opened.")
    else:
        print(f"Unsupported Sound setting: {setting}")


# Define functions for other categories (e.g., network, system, etc.) in a similar way

# Example usage:
open_display_settings("night_light")
# open_sound_settings("volume")
