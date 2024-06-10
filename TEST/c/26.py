from pywinauto import Application


def get_visible_windows():
    """
    Returns a list of window titles for currently visible windows on the screen using pywinauto.
    """
    # Choose one of the following options to connect before getting visible windows:

    # Option 1: Start the application object for the active desktop
    app = Application().start()

    # Option 2: Connect to the desktop window by title or handle
    app = Application()
    app.connect(title="Microsoft Windows")  # Replace with actual title or handle

    visible_windows = app.get_visible_windows()
    window_titles = [window.window_element().name for window in visible_windows]
    return window_titles


if __name__ == "__main__":
    visible_windows = get_visible_windows()
    print("Visible window titles:", visible_windows)
