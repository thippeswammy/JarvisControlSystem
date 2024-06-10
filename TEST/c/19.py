from pywinauto import Application


def get_taskbar_apps():
    """
    Returns a list of names of pinned applications on the taskbar.
    """
    apps = []
    taskbar = Application().taskbar
    for app in taskbar.applications():
        apps.append(app.window_element().name)
    return apps


if __name__ == "__main__":
    taskbar_apps = get_taskbar_apps()
    print("Taskbar applications:", taskbar_apps)
