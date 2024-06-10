import winreg

key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Bluetooth\Parameters")
winreg.SetValueEx(key, "Enable", winreg.REG_DWORD, 1)
winreg.CloseKey(key)
print("Bluetooth is now enabled.")
