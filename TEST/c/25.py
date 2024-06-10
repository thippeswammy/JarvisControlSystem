import psutil
import results as results
import win32gui


def get_visible_windows():
    """
    Returns a list of application names for currently visible windows on the screen using psutil and Win32 API.
    """
    visible_processes = []
    enum_window = win32gui.EnumWindows

    def callback(hwnd, results):
        if win32gui.IsWindowVisible(hwnd):
            process_id = win32gui.GetWindowProcessId(hwnd)
            process = psutil.Process(process_id)
            visible_processes.append(process)

    win32gui.EnumWindows(callback, results)
    window_names = [process.name() for process in visible_processes]
    return window_names


if __name__ == "__main__":
    visible_windows = get_visible_windows()
    print("Visible window names:", visible_windows)
