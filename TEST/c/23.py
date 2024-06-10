from pywinauto import Application


def get_visible_windows():
    """
    Returns a list of window objects for currently visible windows on the screen.
    """
    return Application().get_visible_windows()


if __name__ == "__main__":
    visible_windows = get_visible_windows()
    for window in visible_windows:
        print(f"Visible window title: {window.window_element().name}")
