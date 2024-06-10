import winreg

key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")

installed_apps = []
for i in range(winreg.QueryInfoKey(key)[0]):
    subkey = winreg.OpenKey(key, str(i))
    try:
        display_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
        installed_apps.append(display_name)
    except:
        pass
    finally:
        winreg.CloseKey(subkey)

winreg.CloseKey(key)

print("Installed applications:", installed_apps)
