import subprocess


def enable_wifi_windows():
    subprocess.run('netsh interface set interface "Wi-Fi" admin=enable', shell=True)
    print("Wi-Fi enabled")


def disable_wifi_windows():
    subprocess.run('netsh interface set interface "Wi-Fi" admin=disable', shell=True)
    print("Wi-Fi disabled")


enable_wifi_windows()
# disable_wifi_windows()
