import os


def open_system_settings():
    try:
        os.system("start ms-settings:")
        print("System Settings opened.")
    except Exception as e:
        print(f"Failed to open System Settings. Error: {e}")


def open_devices_settings():
    try:
        os.system("start ms-settings:devices")
        print("Devices Settings opened.")
    except Exception as e:
        print(f"Failed to open Devices Settings. Error: {e}")


def open_phone_settings():
    try:
        os.system("start ms-settings:phone")
        print("Phone Settings opened.")
    except Exception as e:
        print(f"Failed to open Phone Settings. Error: {e}")


def open_network_and_internet_settings():
    try:
        os.system("start ms-settings:network")
        print("Network and Internet Settings opened.")
    except Exception as e:
        print(f"Failed to open Network and Internet Settings. Error: {e}")


def open_personalization_settings():
    try:
        os.system("start ms-settings:personalization")
        print("Personalization Settings opened.")
    except Exception as e:
        print(f"Failed to open Personalization Settings. Error: {e}")


def open_apps_settings():
    try:
        os.system("start ms-settings:apps")
        print("Apps Settings opened.")
    except Exception as e:
        print(f"Failed to open Apps Settings. Error: {e}")


def open_accounts_settings():
    try:
        os.system("start ms-settings:accounts")
        print("Accounts Settings opened.")
    except Exception as e:
        print(f"Failed to open Accounts Settings. Error: {e}")


def open_time_and_language_settings():
    try:
        os.system("start ms-settings:dateandtime")
        print("Time and Language Settings opened.")
    except Exception as e:
        print(f"Failed to open Time and Language Settings. Error: {e}")


def open_gaming_settings():
    try:
        os.system("start ms-settings:gaming")
        print("Gaming Settings opened.")
    except Exception as e:
        print(f"Failed to open Gaming Settings. Error: {e}")


def open_ease_of_access_settings():
    try:
        os.system("start ms-settings:easeofaccess")
        print("Ease of Access Settings opened.")
    except Exception as e:
        print(f"Failed to open Ease of Access Settings. Error: {e}")


def open_search_settings():
    try:
        os.system("start ms-settings:cortana-notifications")
        print("Search Settings opened.")
    except Exception as e:
        print(f"Failed to open Search Settings. Error: {e}")


def open_privacy_settings():
    try:
        os.system("start ms-settings:privacy")
        print("Privacy Settings opened.")
    except Exception as e:
        print(f"Failed to open Privacy Settings. Error: {e}")


def open_update_and_security_settings():
    try:
        os.system("start ms-settings:windowsupdate")
        print("Update and Security Settings opened.")
    except Exception as e:
        print(f"Failed to open Update and Security Settings. Error: {e}")


# Call the functions to open the corresponding settings
open_system_settings()
# open_devices_settings()
# open_phone_settings()
# open_network_and_internet_settings()
# open_personalization_settings()
# open_apps_settings()
# open_accounts_settings()
# open_time_and_language_settings()
# open_gaming_settings()
# open_ease_of_access_settings()
# open_search_settings()
# open_privacy_settings()
# open_update_and_security_settings()
