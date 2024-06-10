import os
import subprocess
import threading
import time

from pywinauto import Desktop, Application
from pywinauto.findwindows import ElementNotFoundError


# from winrt.windows.devices import radios


def open_system_settings(setting):
    print('Now opened ===>>', setting)
    system_settings_map = {
        'home': "ms-settings:home",
        "system": "ms-settings:system",
        "display": "ms-settings:display",
        "sound": "ms-settings:sound",
        "notifications": "ms-settings:notifications",
        "storage": "ms-settings:storage",
        "about": "ms-settings:about",
        "tablet_mode": "ms-settings:tabletmode",
        "tablet mode": "ms-settings:tabletmode",
        "tablet": "ms-settings:tabletmode",
        "mode": "ms-settings:tabletmode",
        "multitasking": "ms-settings:multitasking",
        "project to this pc": "ms-settings:project",
        "power and sleep": "ms-settings:powersleep",
        "power sleep": "ms-settings:powersleep",
        "power": "ms-settings:powersleep",
        "sleep": "ms-settings:powersleep",
        "focus and Assist": "ms-settings:quiethours",
        "focus Assist": "ms-settings:quiethours",
        "focus": "ms-settings:quiethours",
        "Assist": "ms-settings:quiethours",
        "battery": "ms-settings:batterysaver-settings",
        "Storage": "ms-settings:storagesense",
        "Tablet": "ms-settings:tabletmode",
        "Clipboard": "ms-settings:clipboard",
        "project_to_this_pc": "ms-settings:project",
        # Add more system settings as needed
    }

    if setting.lower() in system_settings_map:
        os.system(f"start {system_settings_map[setting.lower()]}")
        print(f"{setting.capitalize()} Setting opened.")
    else:
        print(f"Unsupported system setting: {setting}")


def open_bluethooth_devices_settings(setting):
    print('Now opened ===>>', setting)
    devices_settings_map = {
        "bluetooth & device": "ms-settings:bluetooth",
        "bluetooth & devices": "ms-settings:bluetooth",
        "bluetooth device": "ms-settings:bluetooth",
        "bluetooth devices": "ms-settings:bluetooth",
        "devices": "ms-settings:bluetooth",
        "device": "ms-settings:bluetooth",
        "bluetooth": "ms-settings:bluetooth",
        "printers_scanners": "ms-settings:printers",
        "printers & scanners": "ms-settings:printers",
        "printers scanners": "ms-settings:printers",
        "printers": "ms-settings:printers",
        "scanners": "ms-settings:printers",
        "mouse_touchpad": "ms-settings:mousetouchpad",
        "mouse & touchpad": "ms-settings:mousetouchpad",
        "mouse touchpad": "ms-settings:mousetouchpad",
        "mouse": "ms-settings:mousetouchpad",
        "touchpad": "ms-settings:devices-touchpad",
        "typing": "ms-settings:typing",
        "Pen & Windows_icon Ink": "ms-settings:pen",
        "autoplay": "ms-settings:autoplay",
        "usb": "ms-settings:usb",
        # Add more devices settings as needed
    }

    if setting.lower() in devices_settings_map:
        os.system(f"start {devices_settings_map[setting.lower()]}")
        print(f"{setting.capitalize()} Setting opened.")
    else:
        print(f"Unsupported Devices setting: {setting}")


def open_network_internet_setting(setting):
    print('Now opened ===>>', setting)
    try:
        settings_map = {
            "network & internet": "ms-settings:network",
            "network internet": "ms-settings:network",
            "network": "ms-settings:network",
            "internet": "ms-settings:network",
            "status": "ms-settings:network-status",
            "wifi": "ms-settings:network-wifi",
            "ethernet": "ms-settings:network-ethernet",
            "dialup": "ms-settings:network-dialup",
            "dial up": "ms-settings:network-dialup",
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
    print('Now opened ===>>', setting)
    try:
        settings_map = {
            "personalization": "ms-settings:personalization",
            "background": "ms-settings:personalization-background",
            "colors": "ms-settings:personalization-colors",
            "lock_screen": "ms-settings:lockscreen",
            "lock & screen": "ms-settings:lockscreen",
            "lock screen": "ms-settings:lockscreen",
            "lock": "ms-settings:lockscreen",
            "screen": "ms-settings:lockscreen",
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


def open_apps_setting(setting):
    print('Now opened ===>>', setting)
    settings_map = {
        "apps": "ms-settings:appsfeatures",
        "app": "ms-settings:appsfeatures",
        "apps_and_features": "ms-settings:appsfeatures",
        "apps & features": "ms-settings:appsfeatures",
        "apps features": "ms-settings:appsfeatures",
        "app_and_features": "ms-settings:appsfeatures",
        "app & features": "ms-settings:appsfeatures",
        "app features": "ms-settings:appsfeatures",
        "features": "ms-settings:appsfeatures",
        "default_apps": "ms-settings:defaultapps",
        "default & apps": "ms-settings:defaultapps",
        "default apps": "ms-settings:defaultapps",
        "default_app": "ms-settings:defaultapps",
        "default & app": "ms-settings:defaultapps",
        "default app": "ms-settings:defaultapps",
        "default": "ms-settings:defaultapps",
        "maps": "ms-settings:maps",
        "apps_for_websites": "ms-settings:appsforwebsites",
        "apps websites": "ms-settings:appsforwebsites",
        "app_for_websites": "ms-settings:appsforwebsites",
        "app websites": "ms-settings:appsforwebsites",
        "websites": "ms-settings:appsforwebsites",
        "apps for websites": "ms-settings:appsforwebsites",
        "app for websites": "ms-settings:appsforwebsites",
        "video_playback": "ms-settings:videoplayback",
        "video & playback": "ms-settings:videoplayback",
        "video playback": "ms-settings:videoplayback",
        "video": "ms-settings:videoplayback",
        "playback": "ms-settings:videoplayback",
        "startup_apps": "ms-settings:startupapps",
        "startup & apps": "ms-settings:startupapps",
        "startup apps": "ms-settings:startupapps",
        "start up apps": "ms-settings:startupapps",
        "start up & apps": "ms-settings:startupapps",
        "startup_app": "ms-settings:startupapps",
        "startup & app": "ms-settings:startupapps",
        "startup app": "ms-settings:startupapps",
        "start up app": "ms-settings:startupapps",
        "start up & app": "ms-settings:startupapps",
        "startup": "ms-settings:startupapps",
        "start up": "ms-settings:startupapps",
        # Add more settings as needed
    }

    setting_uri = settings_map.get(setting.lower())
    if setting_uri:
        os.system(f"start {setting_uri}")
        print(f"{setting.capitalize()} Setting opened.")
    else:
        print(f"Unsupported setting: {setting}")


def open_accounts_setting(setting):
    print('Now opened ===>>', setting)
    settings_map = {
        "accounts": "ms-settings:yourinfo",
        "your_info": "ms-settings:yourinfo",
        "your & info": "ms-settings:yourinfo",
        "your info": "ms-settings:yourinfo",
        "your": "ms-settings:yourinfo",
        "info": "ms-settings:yourinfo",
        "email_and_accounts": "ms-settings:emailandaccounts",
        "email & accounts": "ms-settings:emailandaccounts",
        "email accounts": "ms-settings:emailandaccounts",
        "email": "ms-settings:emailandaccounts",
        "accounts_": "ms-settings:emailandaccounts",
        "sign_in_options": "ms-settings:signinoptions",
        "sign in options": "ms-settings:signinoptions",
        "sign in & options": "ms-settings:signinoptions",
        "sign": "ms-settings:signinoptions",
        "options": "ms-settings:signinoptions",
        "access_work_or_school": "ms-settings:workplace",
        "access work or school": "ms-settings:workplace",
        "access work ": "ms-settings:workplace",
        "school": "ms-settings:workplace",
        "family_and_other_users": "ms-settings:otherusers",
        "family & other users": "ms-settings:otherusers",
        "family other users": "ms-settings:otherusers",
        "family": "ms-settings:otherusers",
        "other users": "ms-settings:otherusers",
        "windows_backup": "ms-settings:backup",
        "windows &  backup": "ms-settings:backup",
        "windows backup": "ms-settings:backup",
        "windows": "ms-settings:backup",
        "backup": "ms-settings:backup",
        # Add more settings as needed
    }

    setting_uri = settings_map.get(setting.lower())
    if setting_uri:
        os.system(f"start {setting_uri}")
        print(f"{setting.capitalize()} Setting opened.")
    else:
        print(f"Unsupported setting: {setting}")


def open_time_and_language_setting(setting):
    print('Now opened ===>>', setting)
    settings_map = {
        "time & language": "ms-settings:dateandtime",
        "time language": "ms-settings:dateandtime",
        "time": "ms-settings:dateandtime",
        "language": "ms-settings:dateandtime",
        "date_and_time": "ms-settings:dateandtime",
        "date & time": "ms-settings:dateandtime",
        "date time": "ms-settings:dateandtime",
        "date": "ms-settings:dateandtime",
        'region language': "ms-settings:regionlanguage",
        'region and language': "ms-settings:regionlanguage",
        "region": "ms-settings:regionlanguage",
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
    print('Now opened ===>>', setting)
    settings_map = {
        "gameingr": "ms-settings:gaming-gamebar",
        "gaming": "ms-settings:gaming-gamebar",
        "game_bar": "ms-settings:gaming-gamebar",
        "game & bar": "ms-settings:gaming-gamebar",
        "game bar": "ms-settings:gaming-gamebar",
        "captures": "ms-settings:gaming-captures",
        "game_mode": "ms-settings:gaming-gamemode",
        "game mode": "ms-settings:gaming-gamemode",
        "game": "ms-settings:gaming-gamemode",
        "mode": "ms-settings:gaming-gamemode",
        # Add more settings as needed
    }

    setting_uri = settings_map.get(setting.lower())
    if setting_uri:
        os.system(f"start {setting_uri}")
        print(f"{setting.capitalize()} Setting opened.")
    else:
        print(f"Unsupported setting: {setting}")


def open_accessibility_setting(setting):
    print('Now opened ===>>', setting)
    settings_map = {
        "accessibility": "ms-settings:easeofaccess-display",
        "ease access": "ms-settings:easeofaccess-display",
        "ease": "ms-settings:easeofaccess-display",
        "access": "ms-settings:easeofaccess-display",
        "display": "ms-settings:easeofaccess-display",
        "mouse_pointer": "ms-settings:easeofaccess-mousepointer",
        "mouse & pointer": "ms-settings:easeofaccess-mousepointer",
        "mouse pointer": "ms-settings:easeofaccess-mousepointer",
        "mouse": "ms-settings:easeofaccess-mousepointer",
        "pointer": "ms-settings:easeofaccess-mousepointer",
        "text_cursor": "ms-settings:easeofaccess-textcursor",
        "text & cursor": "ms-settings:easeofaccess-textcursor",
        "text cursor": "ms-settings:easeofaccess-textcursor",
        "text": "ms-settings:easeofaccess-textcursor",
        "cursor": "ms-settings:easeofaccess-textcursor",
        "magnifier": "ms-settings:easeofaccess-magnifier",
        "color_filters": "ms-settings:easeofaccess-colorfilter",
        "color & filters": "ms-settings:easeofaccess-colorfilter",
        "color filters": "ms-settings:easeofaccess-colorfilter",
        "color": "ms-settings:easeofaccess-colorfilter",
        "filters": "ms-settings:easeofaccess-colorfilter",
        "high_contrast": "ms-settings:easeofaccess-highcontrast",
        "high & contrast": "ms-settings:easeofaccess-highcontrast",
        "high contrast": "ms-settings:easeofaccess-highcontrast",
        "high": "ms-settings:easeofaccess-highcontrast",
        "contrast": "ms-settings:easeofaccess-highcontrast",
        "narrator": "ms-settings:easeofaccess-narrator",
        "audio": "ms-settings:easeofaccess-audio",
        "closed_captions": "ms-settings:easeofaccess-closedcaptions",
        "closed & captions": "ms-settings:easeofaccess-closedcaptions",
        "closed captions": "ms-settings:easeofaccess-closedcaptions",
        "closed": "ms-settings:easeofaccess-closedcaptions",
        "captions": "ms-settings:easeofaccess-closedcaptions",
        # Add more settings as needed
    }

    setting = setting.lower()
    if setting in settings_map:
        os.system(f"start {settings_map[setting]}")
        print(f"{setting.capitalize()} Setting opened.")
    else:
        print(f"Unsupported setting: {setting}")


def open_privacy_security_settings(setting):
    print('Now opened ===>>', setting)
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
    else:
        print(f"Unsupported privacy setting: {setting}")


def open_windows_update_settings(setting):
    print("===>", setting)
    update_security_settings_map = {
        "update_and_security": "ms-settings:windowsupdate",
        "update & security": "ms-settings:windowsupdate",
        "update security": "ms-settings:windowsupdate",
        "windows update": "ms-settings:windowsupdate",
        "update": "ms-settings:windowsupdate",
        "security": "ms-settings:windowsupdate",
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
    else:
        print(f"Unsupported Update & Security setting: {setting}")


async def bluetooth_on_off(turn_on):
    print('Now opened ===>>', turn_on)
    all_radios = await radios.Radio.get_radios_async()
    for this_radio in all_radios:
        if this_radio.kind == radios.RadioKind.BLUETOOTH:
            if turn_on:
                return await this_radio.set_state_async(radios.RadioState.ON)
            else:
                return await this_radio.set_state_async(radios.RadioState.OFF)


# ////////////////////////////////////////////////////////////////////////////

def open_search_settings(setting):
    print('Now opened ===>>', setting)
    settings_map = {
        "search": "ms-settings:cortana",
        "permissions_and_history": "ms-settings:privacy-history",
        "searching_windows": "ms-settings:search"
        # Add more settings as needed
    }

    if setting.lower() in settings_map:
        os.system(f"start {settings_map[setting.lower()]}")
        print(f"{setting.capitalize()} Settings opened.")
    else:
        print(f"Unsupported search setting: {setting}")


def open_phone_settings():
    print('Now opened ===>>')
    try:
        subprocess.run(["start", "ms-settings:phone"], shell=True)
        print("Phone Settings opened.")
    except Exception as e:
        print(f"Failed to open Phone Settings. Error: {e}")


def get_present_location_in_setting(settings_path=r'C:\Windows\ImmersiveControlPanel\SystemSettings.exe',
                                    window_title='Settings', max_depth=5):
    # Function to get element info as a tuple
    def get_element_info(element):
        control_type = element.element_info.control_type
        window_text = element.window_text()
        return control_type, window_text, element

    # Function to traverse elements and store them in a nested list
    def traverse_elements(element, depth=0):
        if depth > max_depth:
            return None
        element_info = get_element_info(element)
        children = []
        for child in element.children():
            child_elements = traverse_elements(child, depth + 1)
            if child_elements:
                children.append(child_elements)
        return [element_info, children, depth]

    # Function to find the first "Group" of depth 3 and retrieve buttons
    def get_first_group_buttons(nested_list):
        def find_first_group_at_depth(nested_list, target_depth):
            element_info, children, depth = nested_list
            if element_info[0] == 'Group' and depth == target_depth:
                return nested_list
            for child in children:
                result = find_first_group_at_depth(child, target_depth)
                if result:
                    return result
            return None

        first_group = find_first_group_at_depth(nested_list, 3)
        buttons = []
        if first_group:
            element_info, children, depth = first_group
            for child in children:
                child_info, _, child_depth = child
                if child_info[0] == 'Button':
                    buttons.append(child_info)
        return buttons

    # Function to find the first "Window" of depth 1 and retrieve its button elements
    def get_first_window_buttons(nested_list):
        def find_first_window_at_depth(nested_list, target_depth):
            element_info, children, depth = nested_list
            if element_info[0] == 'Window' and depth == target_depth:
                return nested_list
            for child in children:
                result = find_first_window_at_depth(child, target_depth)
                if result:
                    return result
            return None

        first_window = find_first_window_at_depth(nested_list, 1)
        buttons = []
        if first_window:
            element_info, children, depth = first_window
            for child in children:
                child_info, _, child_depth = child
                if child_info[0] == 'Button':
                    buttons.append((child_info, child_depth))
        return buttons

    # Function to find the first occurrence of specific elements in the hierarchy
    def find_first_occurrence(nested_list, control_type, window_text=None):
        element_info, children, depth = nested_list
        if element_info[0] == control_type and (window_text is None or element_info[1] == window_text):
            return element_info, depth
        for child in children:
            result = find_first_occurrence(child, control_type, window_text)
            if result:
                return result
        return None

    # Open Settings application
    Application(backend='uia').start(settings_path)
    # time.sleep(3)  # Reduced wait time

    # Connect to the Settings window with the correct title
    try:
        settings_window = Desktop(backend='uia').window(title=window_title, top_level_only=True)
    except ElementNotFoundError:
        print("Settings window not found. Please check the window title and ensure the application is open.")
        return

    # Traverse and save UI elements in a nested list with a limited depth
    ui_hierarchy = traverse_elements(settings_window)

    # Get the buttons within the first "Group" of depth 3
    buttons = get_first_group_buttons(ui_hierarchy)

    # Get the button elements within the first "Window" of depth 1
    window_buttons = get_first_window_buttons(ui_hierarchy)

    # Find the first "Back" button
    back_button_info = find_first_occurrence(ui_hierarchy, 'Button', 'Back')

    # Find the first "Open Navigation" button
    open_navigation_button_info = find_first_occurrence(ui_hierarchy, 'Button', 'Open Navigation')

    # Find the first "Find a setting" text element
    find_a_setting_text_info = find_first_occurrence(ui_hierarchy, 'Text', 'Find a setting')

    # Print the button elements within the first "Window" of depth 1
    window_buttons_ = []
    if back_button_info:
        back_button, back_depth = back_button_info
        window_buttons_.append(back_button)
    if open_navigation_button_info:
        open_navigation_button, open_navigation_depth = open_navigation_button_info
        window_buttons_.append(open_navigation_button)
    if find_a_setting_text_info:
        find_a_setting_text, find_a_setting_depth = find_a_setting_text_info
        window_buttons_.append(find_a_setting_text)
    for element_info, depth in window_buttons:
        window_buttons_.append(element_info)

    # Print the special output
    if buttons:
        button_names = [i[1] for i in buttons]
        if len(button_names) > 1:
            location_output = f"Settings => {' => '.join(button_names)}"
            location_output_single = f"Settings {' '.join(button_names)}"
        else:
            location_output = f"Settings => {button_names[0]}"
            location_output_single = f"Settings {button_names[0]}"
        return location_output, location_output_single, buttons, window_buttons_
    else:
        return "I am not able to find any buttons, there may be various reasons.", [], window_buttons_


def custom_split(text="", isLower=False):
    result = text.split(' => ')
    if isLower:
        for i in range(len(result)):
            result[i] = result[i].lower()
    # text = text.split(" ")
    # pos = 0
    # for i, val in enumerate(text):
    #     if i == pos:
    #         if i + 1 < len(text) and text[i + 1] in ['and', '&']:
    #             pos = i + 3
    #             result.append(" ".join(text[i:i + 3]))
    #         # elif i + 1 < len(text) and 'A' <= (text[i + 1][0]) <= 'Z':
    #         #     pos = i + 2
    #         #     result.append(" ".join(text[i:i + 2]))
    #         else:
    #             pos += 1
    #             result.append(text[i])
    return result


# /////////////////////////////////////////////////////////////////////////////

# notification.notify(
#     title="Sample Notification",
#     message="This is a sample notification",
#     timeout=2
# )
#
# toast = ToastNotifier()
# toast.show_toast(
#     "Notification",
#     "Thippeswamy",
#     duration=3,
#     # icon_path = "icon.ico",
#     threaded=True,
# )
# open windows setting -> locked

# /////////////////////////////////////////////////////////////////////////////

# close windows setting
def MainSettings(multiVals=None, addrs=""):
    if multiVals is None:
        multiVals = [""]
    setting = {"home": "open_system_settings",
               "system": "open_system_settings",
               "bluetooth & devices": 'open_bluethooth_devices_settings',
               "bluetooth & device": 'open_bluethooth_devices_settings',
               "bluetooth": 'open_bluethooth_devices_settings',
               "devices": 'open_bluethooth_devices_settings',
               "device": 'open_bluethooth_devices_settings',
               'network & internet': 'open_network_internet_setting',
               'network': 'open_network_internet_setting',
               'internet': 'open_network_internet_setting',
               'personalization': 'open_personalization_setting',
               'apps': 'open_apps_setting',
               'accounts & account': 'open_accounts_setting',
               'accounts': 'open_accounts_setting',
               'account': 'open_accounts_setting',
               'account & account': 'open_accounts_setting',
               'time & language': 'open_time_and_language_setting',
               'time': 'open_time_and_language_setting',
               'language': 'open_time_and_language_setting',
               'gaming': 'open_gaming_setting',
               'acceibility': 'open_accessibility_setting',
               'privacy & security': 'open_privacy_security_settings',
               'privacy': 'open_privacy_security_settings',
               'security': 'open_privacy_security_settings',
               'windows & update': 'open_windows_update_settings',
               'windows': 'open_windows_update_settings',
               'update': 'open_windows_update_settings'}
    function = None
    setting_ = None
    try:
        function = setting[multiVals[0].lower()]
        function1 = setting[multiVals[-1].lower()]
        if function1 is not None:
            function = function1
            setting_ = multiVals[-1]
    except Exception as e:
        print("error:", e)
    if function != None:
        print("function ===>>", function)
        if len(multiVals) <= 2 or setting_ is not None:
            if setting_ is None:
                setting_ = multiVals[1]
            if function == "open_system_settings":
                open_system_settings(setting_)
                # open_system_settings(" ".join(multiVals[1:]))
            elif function == "open_bluethooth_devices_settings":
                open_bluethooth_devices_settings(setting_)
                # open_bluethooth_devices_settings(" ".join(multiVals[1:]))
            elif function == "open_network_internet_setting":
                open_network_internet_setting(setting_)
                # open_network_internet_setting(" ".join(multiVals[1:]))
            elif function == "open_personalization_setting":
                open_personalization_setting(setting_)
                # open_personalization_setting(" ".join(multiVals[1:]))
            elif function == "open_apps_setting":
                open_apps_setting(setting_)
                # open_apps_setting(" ".join(multiVals[1:]))
            elif function == "open_accounts_setting":
                open_accounts_setting(setting_)
                # open_accounts_setting(" ".join(multiVals[1:]))
            elif function == "open_time_and_language_setting":
                open_time_and_language_setting(setting_)
                # open_time_and_language_setting(" ".join(multiVals[1:]))
            elif function == "open_gaming_setting":
                open_gaming_setting(setting_)
                # open_gaming_setting(" ".join(multiVals[1:]))
            elif function == "open_accessibility_setting":
                open_accessibility_setting(setting_)
                # open_accessibility_setting(" ".join(multiVals[1:]))
            elif function == "open_privacy_security_settings":
                open_privacy_security_settings(setting_)
                # open_privacy_security_settings(" ".join(multiVals[1:]))
            elif function == "open_windows_update_settings":
                open_windows_update_settings(setting_)
                # open_windows_update_settings(" ".join(" ".join(multiVals[1:])))
        else:
            print("Dynamic access", multiVals[-1])
            # activating Dynamic access
            if multiVals[-1] == "home":
                pass
            pass


def invoke_button_action(windowsButtons, userVal):
    global sign, present, buttons, window_buttons
    # Define mappings from MultVal values to button actions
    if userVal in ['back']:
        for button_properties in windowsButtons:
            if button_properties[0] == "Button" and button_properties[1] == 'Back':
                button_properties[2].invoke()
                update()
                return True
    elif userVal in ['open navigation', 'navigation']:
        for button_properties in windowsButtons:
            if button_properties[0] == "Button" and button_properties[1] == 'Open Navigation':
                button_properties[2].invoke()
                update()
                return True
    elif userVal in ['minimize Settings', 'minimize']:
        for button_properties in windowsButtons:
            if button_properties[0] == "Button" and button_properties[1] == 'Minimize Settings':
                button_properties[2].invoke()
                sign, present, buttons, window_buttons = None, None, None, None
                return True
    elif userVal in ['maximize Settings', 'maximize']:
        for button_properties in windowsButtons:
            if button_properties[0] == "Button" and button_properties[1] == 'Maximize Settings':
                button_properties[2].invoke()
                update()
                return True
    elif userVal in ['close Settings', 'close setting', 'close settings', 'close']:
        for button_properties in windowsButtons:
            if button_properties[0] == "Button" and button_properties[1] == 'Close Settings':
                button_properties[2].invoke()
                sign, present, buttons, window_buttons = None, None, None, None
                return True
    else:
        for button_properties in windowsButtons:
            if button_properties[0] == "Button" and button_properties[1].lower() == userVal.lower():
                button_properties[2].invoke()
                update()
                return True
    return False


def open_settings_windows():
    subprocess.run('start ms-settings:', shell=True)
    time.sleep(1)
    update()


sign, present, buttons, window_buttons = None, None, None, []


# def updateWithThread():
#     global sign, present, buttons, window_buttons
#     sign, present, buttons, window_buttons = get_present_location_in_setting()
#     for i in buttons:
#         window_buttons.append(i)
#     print("update ============>>>>>>>>>>>>>", present)


def updateWithThread():
    global sign, present, buttons, window_buttons

    # Define a function to run in a thread
    def thread_function():
        global sign, present, buttons, window_buttons
        sign, present, buttons, window_buttons = get_present_location_in_setting()
        for i in buttons:
            window_buttons.append(i)
        print("update ============>>>>>>>>>>>>>", present)

    # Create and start the thread
    thread = threading.Thread(target=thread_function)
    thread.start()


# Main program


def update():
    global sign, present, buttons, window_buttons
    updateWithThread()
    # thread = threading.Thread(target=updateWithThread)
    # thread.start()
    # thread.join()
    # sign, present, buttons, window_buttons = get_present_location_in_setting()
    # for i in buttons:
    #     window_buttons.append(i)
    # print("update =>", present)


def infinity(user=""):
    global sign, present, buttons, window_buttons
    if user == "":
        while True:
            print('-' * 100)
            user = input("=>>")
            if user in ["", "0", 'exit', 'exit()']:
                exit()
            else:
                MultVal = custom_split(sign + " => " + user)
                print("user full input ===>>>", MultVal)
                print('Present ===>>>', sign)
                if not invoke_button_action(window_buttons, user.lower()):
                    MainSettings(MultVal[1:])
                    update()
    else:
        print('-' * 100)
        M_user = user.split(" ")
        if M_user[0] in ["open", 'move', 'click', 'press']:
            M_user = M_user[1:]
            if len(M_user) > 1:
                user = ' '.join(M_user)
            else:
                user = M_user[0]
        # if M_user[:2] in ["open", 'move', 'click']:
        #     M_user = M_user[2:]
        print(sign + " => " + user)
        MultVal = custom_split(sign + " => " + user)
        print("user full input ===>>>", MultVal)
        print('Present ===>>>', sign)
        if not invoke_button_action(window_buttons, user.lower()):
            MainSettings(MultVal[1:])
            update()
        print('-' * 100)
        pass


# if __name__ == '__main__':
#     thread = threading.Thread(target=update)
#     thread.start()
#     infinity()
#     pass


def OpeningSettings(operation='', addr=''):
    global sign, present
    print('operation =', operation, '  |  sign', sign, '  |  present', present)
    if operation.lower() in ["open setting", "open settings"]:
        open_settings_windows()
    else:
        infinity(user=operation)
    pass
