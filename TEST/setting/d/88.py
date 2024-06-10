import subprocess


def enable_bluetooth():
    subprocess.run(["control", "bthprops.cpl"])


if __name__ == "__main__":
    enable_bluetooth()
#
# try:
#     key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Bluetooth\Parameters")
# except FileNotFoundError:
#     key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Bluetooth\Parameters")
#
# winreg.SetValueEx(key, "Enable", 0, winreg.REG_DWORD, 1)
# winreg.CloseKey(key)
