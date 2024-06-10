import win32com.client

wmi = win32com.client.GetObject("winmgmts://./CIMv2:Win32_Product")

installed_apps = []
for app in wmi:
    if not app.UninstallPath:
        continue
    installed_apps.append((app.Name, app.Version))

print("Installed applications:", installed_apps)
