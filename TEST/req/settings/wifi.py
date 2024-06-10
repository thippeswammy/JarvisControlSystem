import os
import sys
import ctypes
import subprocess
import asyncio


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


async def enable_wifi_windows():
    try:
        subprocess.run(["netsh", "interface", "set", "interface", "Wi-Fi", "admin=enable"], check=True)
        print("Wi-Fi is enabled.")
    except subprocess.CalledProcessError:
        print("Failed to enable Wi-Fi.")


def disable_wifi_windows():
    try:
        subprocess.run(["netsh", "interface", "set", "interface", "Wi-Fi", "admin=disable"], check=True)
        print("Wi-Fi is disabled.")
    except subprocess.CalledProcessError:
        print("Failed to disable Wi-Fi.")


if __name__ == "__main__":
    if is_admin():
        # Uncomment the line corresponding to the action you want
        # asyncio.run(enable_wifi_windows())
        # disable_wifi_windows()
        # asyncio.run(enable_wifi_windows())
        pass
    else:
        # Re-run the program with admin rights
        script = os.path.abspath(sys.argv[0])
        params = ' '.join([script] + sys.argv[1:])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
