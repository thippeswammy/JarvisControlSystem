import win32gui


def get_visible_windows():
    """
    Returns a list of titles of currently visible windows on the screen.
    """
    windows = []
    enum_window = win32gui.EnumWindows
    window_title = win32gui.GetWindowText

    def callback(hwnd, results):
        if win32gui.IsWindowVisible(hwnd):
            windows.append(window_title(hwnd))
        return True

    win32gui.EnumWindows(callback, windows)
    return windows


if __name__ == "__main__":
    visible_windows = get_visible_windows()
    print("Visible windows on screen:", visible_windows)
