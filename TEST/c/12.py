import psutil


def get_window_titles():
    """
    Returns a list of titles of all open windows.
    """
    titles = []
    for process in psutil.process_iter():
        try:
            window_title = process.name().replace(".exe", "")
            titles.append(window_title)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return titles


# Get the list of window titles
window_titles = get_window_titles()

# Print the list
print(window_titles)
