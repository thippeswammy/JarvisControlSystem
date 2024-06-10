import os
from time import sleep


def open_setting(setting):
    settings_map = {
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
        sleep(1)
    else:
        print(f"Unsupported setting: {setting}")


# Example usage:
open_setting("your_info")
open_setting("email_and_accounts")
open_setting("sign_in_options")
open_setting("access_work_or_school")
open_setting("family_and_other_users")
open_setting("windows_backup")
# Add more calls as needed
