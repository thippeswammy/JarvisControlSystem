import os
from time import sleep


def open_privacy_settings(setting):
    privacy_settings_map = {
        "privacy": "ms-settings:privacy",
        "general": "ms-settings:privacy-general",
        "speech": "ms-settings:privacy-speechtyping",
        "inking_and_typing_personalization": "ms-settings:privacy-speechtyping",
        "diagnostics_and_feedback": "ms-settings:privacy-feedback",
        "activity_history": "ms-settings:privacy-activityhistory",
        "location": "ms-settings:privacy-location",
        "camera": "ms-settings:privacy-webcam",
        "microphone": "ms-settings:privacy-microphone",
        "voice_activation": "ms-settings:privacy-speechtyping",
        "notifications": "ms-settings:privacy-notifications",
        "account_info": "ms-settings:privacy-accountinfo",
        "contacts": "ms-settings:privacy-contacts",
        "calendar": "ms-settings:privacy-calendar",
        "phone_calls": "ms-settings:privacy-radios",
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
        "file_system": "ms-settings:privacy-files"
        # Add more settings as needed
    }

    if setting.lower() in privacy_settings_map:
        os.system(f"start {privacy_settings_map[setting.lower()]}")
        print(f"{setting.capitalize()} Privacy Setting opened.")
        sleep(1)
    else:
        print(f"Unsupported privacy setting: {setting}")


# Open privacy settings individually
open_privacy_settings("privacy")
open_privacy_settings("general")
open_privacy_settings("speech")
open_privacy_settings("inking_and_typing_personalization")
open_privacy_settings("diagnostics_and_feedback")
open_privacy_settings("activity_history")
open_privacy_settings("location")
open_privacy_settings("camera")
open_privacy_settings("microphone")
open_privacy_settings("voice_activation")
open_privacy_settings("notifications")
open_privacy_settings("account_info")
open_privacy_settings("contacts")
open_privacy_settings("calendar")
open_privacy_settings("phone_calls")
open_privacy_settings("call_history")
open_privacy_settings("email")
open_privacy_settings("tasks")
open_privacy_settings("messaging")
open_privacy_settings("radios")
open_privacy_settings("other_devices")
open_privacy_settings("background_apps")
open_privacy_settings("app_diagnostics")
open_privacy_settings("automatic_file_downloads")
open_privacy_settings("documents")
open_privacy_settings("pictures")
open_privacy_settings("videos")
open_privacy_settings("file_system")
