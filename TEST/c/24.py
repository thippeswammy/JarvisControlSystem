import psutil


def get_visible_windows():
    """
    Returns a list of application names for currently visible windows on the screen using psutil.
    """
    visible_processes = [process for process in psutil.process_iter() if process.windows()]
    window_names = [process.name() for process in visible_processes]
    return window_names


if __name__ == "__main__":
    visible_windows = get_visible_windows()
    print("Visible window names:", visible_windows)
