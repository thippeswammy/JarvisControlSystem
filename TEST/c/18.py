import win32gui


def get_taskbar_apps():
    """
    Returns a list of names of pinned applications on the taskbar.
    """
    apps = []
    enum_window = win32gui.EnumWindows
    window_title = win32gui.GetWindowText

    def callback(hwnd, results):
        if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
            apps.append(window_title(hwnd))
        return True

    win32gui.EnumWindows(callback, apps)
    return apps


if __name__ == "__main__":
    taskbar_apps = get_taskbar_apps()
    print("Taskbar applications:", taskbar_apps)
