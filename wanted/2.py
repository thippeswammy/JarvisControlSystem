import subprocess

import win32com.client


def enable_wifi():
    # Enable WiFi
    subprocess.run(['netsh', 'interface', 'set', 'interface', 'Wi-Fi', 'enabled'])


def disable_wifi():
    # Disable WiFi
    subprocess.run(['netsh', 'interface', 'set', 'interface', 'Wi-Fi', 'disabled'])


def enable_bluetooth():
    # Create a Shell object
    shell = win32com.client.Dispatch("WScript.Shell")

    # Enable Bluetooth (assuming F15 is the key to enable Bluetooth)
    shell.SendKeys("{F15}")


def disable_bluetooth():
    # Create a Shell object
    shell = win32com.client.Dispatch("WScript.Shell")

    # Disable Bluetooth (assuming F14 is the key to disable Bluetooth)
    shell.SendKeys("{F14}")


# Test the functions
# enable_wifi()
# disable_wifi()
# enable_bluetooth()
disable_bluetooth()
