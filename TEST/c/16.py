import pygetwindow as gw


def get_taskbar_apps():
    taskbar_apps = []

    # Get all windows
    windows = gw.getAllWindows()

    # Filter windows associated with the taskbar
    for window in windows:
        if "taskbar" in window.title.lower():  # Check if 'taskbar' is in the window title
            taskbar_apps.append(window.title)

    return taskbar_apps


# Get the list of taskbar applications
taskbar_applications = get_taskbar_apps()

# Print the list
print(taskbar_applications)
