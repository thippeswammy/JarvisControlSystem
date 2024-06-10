import os

from win32com.client import Dispatch


def get_taskbar_apps():
    taskbar_apps = []

    # Get the path where taskbar shortcuts are stored in Windows
    path = os.path.join(os.environ['APPDATA'], 'Microsoft\\Internet Explorer\\Quick Launch\\User Pinned\\TaskBar')

    # Get the list of files (shortcuts) in the taskbar directory
    files = os.listdir(path)

    # Extract the application names from the shortcuts
    for file in files:
        if file.endswith('.lnk'):
            # Construct the absolute path of the shortcut file
            file_path = os.path.join(path, file)

            # Use win32com to access the shortcut properties
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(file_path)

            # Get the application name from the shortcut
            app_name = os.path.basename(shortcut.Targetpath)

            # Append the application name to the list
            taskbar_apps.append(app_name)

    return taskbar_apps


# Get the list of taskbar applications
taskbar_applications = get_taskbar_apps()

# Print the list
print(taskbar_applications)
