import os
from time import sleep


def open_setting(setting):
    settings_map = {
        "game_bar": "ms-settings:gaming-gamebar",
        "captures": "ms-settings:gaming-captures",
        "game_mode": "ms-settings:gaming-gamemode"
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
# open_setting("game_bar")
open_setting("captures")
# open_setting("game_mode")
# Add more calls as needed



import subprocess


def open_system_settings(setting):
    system_settings_map = {
        "system": "ms-settings:display",
        "display": "ms-settings:display",
        "notifications": "ms-settings:notifications",
        "storage": "ms-settings:storage",
        "about": "ms-settings:about",
        "tablet_mode": "ms-settings:tabletmode",
        "multitasking": "ms-settings:multitasking",
        "project to this pc": "ms-settings:project",
        "power & sleep": "ms-settings:powersleep",
        "focus Assist": "ms-settings:quiethours",
        "battery": "ms-settings:batterysaver-settings",
        "Storage": "ms-settings:storagesense",
        "Tablet": "ms-settings:tabletmode",
        "multitasking": "ms-settings:multitasking",
        "Clipboard": "ms-settings:clipboard",
        "project_to_this_pc": "ms-settings:project",
        # Add more system settings as needed
    }

    if setting.lower() in system_settings_map:
        os.system(f"start {system_settings_map[setting.lower()]}")
        print(f"{setting.capitalize()} Setting opened.")
    else:
        print(f"Unsupported System setting: {setting}")


def open_devices_settings(setting):
    devices_settings_map = {
        "devices": "ms-settings:bluetooth",
        "bluetooth": "ms-settings:bluetooth",
        "printers_scanners": "ms-settings:printers",
        "mouse_touchpad": "ms-settings:mousetouchpad",
        "touchpad": "ms-settings:devices-touchpad",
        "typing": "ms-settings:typing",
        "Pen and Windows Ink": "ms-settings:pen",
        "autoplay": "ms-settings:autoplay",
        "usb": "ms-settings:usb",
        # Add more devices settings as needed
    }

    if setting.lower() in devices_settings_map:
        os.system(f"start {devices_settings_map[setting.lower()]}")
        print(f"{setting.capitalize()} Setting opened.")
    else:
        print(f"Unsupported Devices setting: {setting}")


def open_phone_settings():
    try:
        subprocess.run(["start", "ms-settings:phone"], shell=True)
        print("Phone Settings opened.")
    except Exception as e:
        print(f"Failed to open Phone Settings. Error: {e}")


def open_network_setting(setting):
    try:
        settings_map = {
            "network and internet": "ms-settings:network",
            "status": "ms-settings:network-status",
            "wifi": "ms-settings:network-wifi",
            "ethernet": "ms-settings:network-ethernet",
            "dialup": "ms-settings:network-dialup",
            "vpn": "ms-settings:network-vpn",
            "airplane": "ms-settings:network-airplanemode",
            "hotspot": "ms-settings:network-mobilehotspot",
            "proxy": "ms-settings:network-proxy"
            # Add more settings as needed
        }

        if setting.lower() in settings_map:
            os.system(f"start {settings_map[setting.lower()]}")
            print(f"{setting.capitalize()} Settings opened.")
        else:
            print(f"Unsupported network setting: {setting}")

    except Exception as e:
        print(f"Failed to open network settings. Error: {e}")


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
        else:
            print(f"Unsupported personalization setting: {setting}")
    except Exception as e:
        print(f"Failed to open personalization settings. Error: {e}")


def open_setting(setting):
    settings_map = {
        "apps": "ms-settings:appsfeatures",
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
    else:
        print(f"Unsupported setting: {setting}")


def open_accounts_setting(setting):
    settings_map = {
        "accounts": "ms-settings:yourinfo",
        "your_info": "ms-settings:yourinfo",
        "email_and_accounts": "ms-settings:emailandaccounts",
        "sign_in_options": "ms-settings:signinoptions",
        "access_work_or_school": "ms-settings:workplace",
        "family_and_other_users": "ms-settings:otherusers",
        "windows_backup": "ms-settings:backup"
        # Add more settings as needed
    }

    setting_uri = settings_map.get(setting.lower())
    if setting_uri:
        os.system(f"start {setting_uri}")
        print(f"{setting.capitalize()} Setting opened.")
    else:
        print(f"Unsupported setting: {setting}")


def open_time_and_language_setting(setting):
    settings_map = {
        "time and language": "ms-settings:dateandtime",
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
    else:
        print(f"Unsupported setting: {setting}")


def open_gaming_setting(setting):
    settings_map = {
        "gameingr": "ms-settings:gaming-gamebar",
        "game_bar": "ms-settings:gaming-gamebar",
        "captures": "ms-settings:gaming-captures",
        "game_mode": "ms-settings:gaming-gamemode"
        # Add more settings as needed
    }

    setting_uri = settings_map.get(setting.lower())
    if setting_uri:
        os.system(f"start {setting_uri}")
        print(f"{setting.capitalize()} Setting opened.")
    else:
        print(f"Unsupported setting: {setting}")


import os


def open_ease_of_access_setting(setting):
    settings_map = {
        "display": "ms-settings:easeofaccess-display",
        "mouse_pointer": "ms-settings:easeofaccess-mousepointer",
        "text_cursor": "ms-settings:easeofaccess-textcursor",
        "magnifier": "ms-settings:easeofaccess-magnifier",
        "color_filters": "ms-settings:easeofaccess-colorfilter",
        "high_contrast": "ms-settings:easeofaccess-highcontrast",
        "narrator": "ms-settings:easeofaccess-narrator",
        "audio": "ms-settings:easeofaccess-audio",
        "closed_captions": "ms-settings:easeofaccess-closedcaptions"
        # Add more settings as needed
    }

    setting = setting.lower()
    if setting in settings_map:
        os.system(f"start {settings_map[setting]}")
        print(f"{setting.capitalize()} Setting opened.")
    else:
        print(f"Unsupported setting: {setting}")


# Example usage:
open_ease_of_access_setting("display")
open_ease_of_access_setting("mouse_pointer")
open_ease_of_access_setting("text_cursor")
open_ease_of_access_setting("magnifier")
open_ease_of_access_setting("color_filters")
open_ease_of_access_setting("high_contrast")
open_ease_of_access_setting("narrator")
open_ease_of_access_setting("audio")
open_ease_of_access_setting("closed_captions")
# Add more calls as needed
