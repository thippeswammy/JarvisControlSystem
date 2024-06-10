import os
from time import sleep


def open_update_security_settings(setting):
    update_security_settings_map = {
        "update_and_security": "ms-settings:windowsupdate",
        "windows_update": "ms-settings:windowsupdate-action",
        "delivery_optimization": "ms-settings:deliveryoptimization",
        "windows_security": "ms-settings:windowsdefender",
        "file_backup": "ms-settings:backup",
        "troubleshoot": "ms-settings:troubleshoot",
        "recovery": "ms-settings:recovery",
        "activation": "ms-settings:activation",
        "find_my_device": "ms-settings:findmydevice",
        "for_developers": "ms-settings:developers",
        "windows_insider_program": "ms-settings:windowsinsider"
        # Add more settings as needed
    }

    if setting.lower() in update_security_settings_map:
        os.system(f"start {update_security_settings_map[setting.lower()]}")
        print(f"{setting.capitalize()} Setting opened.")
        sleep(1)
    else:
        print(f"Unsupported Update and Security setting: {setting}")


# Open Update and Security settings individually
open_update_security_settings("update_and_security")
open_update_security_settings("windows_update")
open_update_security_settings("delivery_optimization")
open_update_security_settings("windows_security")
open_update_security_settings("file_backup")
open_update_security_settings("troubleshoot")
open_update_security_settings("recovery")
open_update_security_settings("activation")
open_update_security_settings("find_my_device")
open_update_security_settings("for_developers")
open_update_security_settings("windows_insider_program")
