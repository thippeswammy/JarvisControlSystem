import win32com.client


def get_app_name_from_file_path(file_path):
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(file_path)
    app_name = shortcut.Targetpath.split('\\')[-1].split('.')[0]
    return app_name


# Example file path
file_path = r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\JetBrains\PyCharm Edu 2022.2.2.lnk"

app_name = get_app_name_from_file_path(file_path)
print(f"Application Name: {app_name}")
