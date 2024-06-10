import subprocess


def open_bluetooth_settings():
    subprocess.run(["control", "bthprops.cpl"])


def enable_bluetooth_windows():
    command = 'powershell -Command "Start-Process btmcpowerswitch -Verb runAs"'
    subprocess.run(command, shell=True)


enable_bluetooth_windows()
open_bluetooth_settings()
