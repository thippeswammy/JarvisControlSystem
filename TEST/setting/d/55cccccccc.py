import os


def open_system_settings(setting):
    system_settings_map = {
        "system": "ms-settings:system",
        "display": "ms-settings:display",
        "notifications": "ms-settings:notifications",
        "storage": "ms-settings:storage",
        "about": "ms-settings:about",
        "tablet_mode": "ms-settings:tabletmode",
        "multitasking": "ms-settings:multitasking",
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
        "devices": "ms-settings:devices",
        "bluetooth": "ms-settings:bluetooth",
        "printers_scanners": "ms-settings:printers",
        "mouse_touchpad": "ms-settings:mousetouchpad",
        "typing": "ms-settings:typing",
        # Add more devices settings as needed
    }

    if setting.lower() in devices_settings_map:
        os.system(f"start {devices_settings_map[setting.lower()]}")
        print(f"{setting.capitalize()} Setting opened.")
    else:
        print(f"Unsupported Devices setting: {setting}")


def open_phone_settings():
    try:
        os.system("start ms-settings:phone")
        print("Phone Settings opened.")
    except Exception as e:
        print(f"Failed to open Phone Settings. Error: {e}")


def open_network_internet_settings(setting):
    network_internet_settings_map = {
        "network_internet": "ms-settings:network",
        "wifi": "ms-settings:network-wifi",
        "ethernet": "ms-settings:network-ethernet",
        "vpn": "ms-settings:network-vpn",
        "mobile_hotspot": "ms-settings:network-mobilehotspot",
        # Add more network and internet settings as needed
    }

    if setting.lower() in network_internet_settings_map:
        os.system(f"start {network_internet_settings_map[setting.lower()]}")
        print(f"{setting.capitalize()} Setting opened.")
    else:
        print(f"Unsupported Network and Internet setting: {setting}")


def open_personalization_settings(setting):
    personalization_settings_map = {
        "personalization": "ms-settings:personalization",
        "background": "ms-settings:personalization-background",
        "colors": "ms-settings:personalization-colors",
        "lock_screen": "ms-settings:lockscreen",
        "themes": "ms-settings:themes",
        "fonts": "ms-settings:fonts",
        "start": "shell:::{2559a1f3-21d7-11d4-bdaf-00c04f60b9f0}",
        "taskbar": "ms-settings:taskbar",
        # Add more personalization settings as needed
    }

    if setting.lower() in personalization_settings_map:
        os.system(f"start {personalization_settings_map[setting.lower()]}")
        print(f"{setting.capitalize()} Setting opened.")
    else:
        print(f"Unsupported Personalization setting: {setting}")


def open_apps_settings(setting):
    apps_settings_map = {
        "apps": "ms-settings:appsfeatures",
        "default_apps": "ms-settings:defaultapps",
        "offline_maps": "ms-settings:maps",
        "apps_for_websites": "ms-settings:appsforwebsites",
        "video_playback": "ms-settings:videoplayback",
        "startup": "ms-settings:startupapps",
        # Add more apps settings as needed
    }

    if setting.lower() in apps_settings_map:
        os.system(f"start {apps_settings_map[setting.lower()]}")
        print(f"{setting.capitalize()} Setting opened.")
    else:
        print(f"Unsupported Apps setting: {setting}")


def open_accounts_settings(setting):
    accounts_settings_map = {
        "accounts": "ms-settings:yourinfo",
        "email_accounts": "ms-settings:emailandaccounts",
        "sign_in_options": "ms-settings:signinoptions",
        "access_work_school": "ms-settings:workplace",
        "family_other_users": "ms-settings:otherusers",
        "windows_backup": "ms-settings:backup",
        # Add more accounts settings as needed
    }

    if setting.lower() in accounts_settings_map:
        os.system(f"start {accounts_settings_map[setting.lower()]}")
        print(f"{setting.capitalize()} Setting opened.")
    else:
        print(f"Unsupported Accounts setting: {setting}")


def open_time_language_settings(setting):
    time_language_settings_map = {
        "time_language": "ms-settings:dateandtime",
        "region": "ms-settings:regionlanguage",
        "language": "ms-settings:regionlanguage-languageoptions",
        "speech": "ms-settings:speech",
        # Add more time and language settings as needed
    }

    if setting.lower() in time_language_settings_map:
        os.system(f"start {time_language_settings_map[setting.lower()]}")
        print(f"{setting.capitalize()} Setting opened.")
    else:
        print(f"Unsupported Time and Language setting: {setting}")


def open_gaming_settings(setting):
    gaming_settings_map = {
        "gaming": "ms-settings:gaming",
        "xbox_game_bar": "ms-settings:gaming-xboxgamebar",
        "captures": "ms-settings:gaming-gameclips",
        "game_mode": "ms-settings:gaming-gamemode",
        # Add more gaming settings as needed
    }

    if setting.lower() in gaming_settings_map:
        os.system(f"start {gaming_settings_map[setting.lower()]}")
        print(f"{setting.capitalize()} Setting opened.")
    else:
        print(f"Unsupported Gaming setting: {setting}")


def open_ease_of_access_settings(setting):
    ease_of_access_settings_map = {
        "ease_of_access": "ms-settings:easeofaccess",
        "display": "ms-settings:easeofaccess-display",
        "mouse_pointer": "ms-settings:easeofaccess-mousepointer",
        "text_cursor": "ms-settings:easeofaccess-cursorandpointer",
        "magnifier": "ms-settings:easeofaccess-magnifier",
        "color_filters": "ms-settings:easeofaccess-highcontrast",
        "high_contrast": "ms-settings:easeofaccess-highcontrast",
        "narrator": "ms-settings:easeofaccess-narrator",
        # Add more ease of access settings as needed
    }

    if setting.lower() in ease_of_access_settings_map:
        os.system(f"start {ease_of_access_settings_map[setting.lower()]}")
        print(f"{setting.capitalize()} Setting opened.")
    else:
        print(f"Unsupported Ease of Access setting: {setting}")


def open_search_settings(setting):
    search_settings_map = {
        "search": "ms-settings:cortana",
        "permissions_history": "ms-settings:search-history",
        "searching_windows": "ms-settings:search-windows",
        # Add more search settings as needed
    }

    if setting.lower() in search_settings_map:
        os.system(f"start {search_settings_map[setting.lower()]}")
        print(f"{setting.capitalize()} Setting opened.")
    else:
        print(f"Unsupported Search setting: {setting}")


def open_privacy_settings(setting):
    privacy_settings_map = {
        "privacy": "ms-settings:privacy",
        "general": "ms-settings:privacy-general",
        "speech": "ms-settings:privacy-speech",
        "inking_typing_personalization": "ms-settings:privacy-activityhistory",
        "diagnostics_feedback": "ms-settings:privacy-feedback",
        "activity_history": "ms-settings:privacy-activityhistory",
        "location": "ms-settings:privacy-location",
        "camera": "ms-settings:privacy-webcam",
        "microphone": "ms-settings:privacy-microphone",
        "voice_activation": "ms-settings:privacy-speech-microphone",
        "notifications": "ms-settings:privacy-notifications",
        "account_info": "ms-settings:privacy-accountinfo",
        "contacts": "ms-settings:privacy-contacts",
        "calendar": "ms-settings:privacy-calendar",
        "phone_calls": "ms-settings:privacy-phonecall",
        "call_history": "ms-settings:privacy-callhistory",
        "email": "ms-settings:privacy-email",
        "tasks": "ms-settings:privacy-tasks",
        "messaging": "ms-settings:privacy-messaging",
        "radios": "ms-settings:privacy-radios",
        "other_devices": "ms-settings:privacy-customdevices",
        "background_apps": "ms-settings:privacy-backgroundapps",
        "app_diagnostics": "ms-settings:privacy-appdiagnostics",
        "automatic_file_downloads": "ms-settings:privacy-automaticfiledownloads",
        "documents": "ms-settings:privacy-documents",
        "pictures": "ms-settings:privacy-pictures",
        "videos": "ms-settings:privacy-videos",
        "file_system": "ms-settings:privacy-filesystem",
        # Add more privacy settings as needed
    }

    if setting.lower() in privacy_settings_map:
        os.system(f"start {privacy_settings_map[setting.lower()]}")
        print(f"{setting.capitalize()} Setting opened.")
    else:
        print(f"Unsupported Privacy setting: {setting}")


def open_update_security_settings(setting):
    update_security_settings_map = {
        "update_security": "ms-settings:windowsupdate",
        "windows_update": "ms-settings:windowsupdate-action",
        "delivery_optimization": "ms-settings:deliveryoptimization",
        "windows_security": "ms-settings:windowsdefender",
        "file_backup": "ms-settings:backup",
        "troubleshoot": "ms-settings:troubleshoot",
        "recovery": "ms-settings:recovery",
        "activation": "ms-settings:activation",
        "find_my_device": "ms-settings:findmydevice",
        "for_developers": "ms-settings:developers",
        "windows_insider_program": "ms-settings:windowsinsider",
        # Add more update and security settings as needed
    }

    if setting.lower() in update_security_settings_map:
        os.system(f"start {update_security_settings_map[setting.lower()]}")
        print(f"{setting.capitalize()} Setting opened.")
    else:
        print(f"Unsupported Update and Security setting: {setting}")


# Add functions for additional categories in a similar way

# Example usage:
open_system_settings("system")
open_devices_settings("bluetooth")
open_phone_settings()
open_network_internet_settings("wifi")
open_personalization_settings("start")
open_apps_settings("apps")
open_accounts_settings("accounts")
open_time_language_settings("time_language")
open_gaming_settings("gaming")
open_ease_of_access_settings("display")
open_search_settings("search")
open_privacy_settings("privacy")
open_update_security_settings("update_security")
