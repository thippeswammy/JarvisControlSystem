import os


def open_network_setting(setting):
    try:
        settings_map = {
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


# Examples:
open_network_setting("status")
open_network_setting("wifi")
open_network_setting("ethernet")
open_network_setting("dialup")
open_network_setting("vpn")
open_network_setting("airplane")
open_network_setting("hotspot")
open_network_setting("proxy")
