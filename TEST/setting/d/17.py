import subprocess


async def enable_wifi_windows():
    try:
        subprocess.run(["netsh", "interface", "set", "interface", "Wi-Fi", "admin=enable"], check=True)
        print("Wi-Fi is enabled.")
    except subprocess.CalledProcessError:
        print("Failed to disable Wi-Fi.")


def disable_wifi_windows():
    try:
        subprocess.run(["netsh", "interface", "set", "interface", "Wi-Fi", "admin=disable"], check=True)
        print("Wi-Fi is disabled.")
    except subprocess.CalledProcessError:
        print("Failed to disable Wi-Fi.")


# Uncomment the line corresponding to the action you want
# asyncio.run(enable_wifi_windows())
# disable_wifi_windows()
enable_wifi_windows()
