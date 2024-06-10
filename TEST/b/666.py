import winreg


def decode_if_bytes(value):
    return value.decode('utf-8') if isinstance(value, bytes) else value


def get_recently_opened_apps():
    recent_apps_key = r"Software\Microsoft\Windows\CurrentVersion\Explorer\RecentDocs"
    apps = []

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, recent_apps_key) as key:
            for i in range(winreg.QueryInfoKey(key)[1]):
                app = winreg.EnumValue(key, i)[1]
                apps.append(decode_if_bytes(app))
    except FileNotFoundError:
        pass

    return apps


# Get the list of recently opened applications
recently_opened_apps = get_recently_opened_apps()

# Save the file paths of recently opened applications to a text file
file_path = "recently_opened_apps.txt"
with open(file_path, 'w', encoding='utf-8') as file:
    for app in recently_opened_apps:
        file.write(app + '\n')

print(f"Recently opened applications saved to {file_path}")
