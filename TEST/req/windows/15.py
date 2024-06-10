import win32gui


def get_visible_window_titles():
    """
    Returns a list of titles of all visible windows on the screen.
    """
    titles = []

    def enum_callback(hwnd, results):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title:
                titles.append(title)
        return True

    win32gui.EnumWindows(enum_callback, None)
    return titles


# Get the list of window titles
window_titles = get_visible_window_titles()

# Print the list
print(window_titles)
