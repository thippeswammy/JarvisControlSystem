import os
import sys
import ctypes
import subprocess
import win32com.client


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def enable_wifi():
    try:
        subprocess.run(['netsh', 'interface', 'set', 'interface', 'Wi-Fi', 'admin=enabled'], check=True)
        print("Wi-Fi is enabled.")
    except subprocess.CalledProcessError:
        print("Failed to enable Wi-Fi.")


def disable_wifi():
    try:
        subprocess.run(['netsh', 'interface', 'set', 'interface', 'Wi-Fi', 'admin=disabled'], check=True)
        print("Wi-Fi is disabled.")
    except subprocess.CalledProcessError:
        print("Failed to disable Wi-Fi.")


def enable_bluetooth():
    shell = win32com.client.Dispatch("WScript.Shell")
    shell.SendKeys("{F15}")  # Replace with the actual key for your system
    print("Bluetooth is enabled.")


def disable_bluetooth():
    shell = win32com.client.Dispatch("WScript.Shell")
    shell.SendKeys("{F14}")  # Replace with the actual key for your system
    print("Bluetooth is disabled.")


if __name__ == "__main__":
    if is_admin():
        # Uncomment the function you want to test
        # enable_wifi()
        disable_wifi()
        # enable_bluetooth()
        # disable_bluetooth()
    else:
        script = os.path.abspath(sys.argv[0])
        params = ' '.join([script] + sys.argv[1:])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
