import pyautogui
# from aiohttp.web_app import Application
import pygetwindow as gw


# from pywinauto import Application


def GetActiveWindowsName(addr):
    active_window = gw.getActiveWindow()
    if active_window is not None:
        return active_window.title
    else:
        print("No active window found.")
        return None
    addr = addr + "GetActiveWindowName ->"


def GetActiveWindowFrame(addr):
    windowName = GetActiveWindowsName(addr)
    if windowName is not None:
        print("Active window title:", windowName)
        window = gw.getWindowsWithTitle(windowName)[0]
        return window
    else:
        print("No active window found.")
    addr = addr + "GetActiveWindowName ->"


def GetActiveWindowsFrameAll(addr):
    windowName = GetActiveWindowsName(addr)
    if windowName is not None:
        print("Active window title:", windowName)
        window = gw.getWindowsWithTitle(windowName)
        return window
    else:
        print("No active window found.")
    addr = addr + "GetActiveWindowName ->"


def GetActiveWindowsFrame(addr, num):
    windowName = GetActiveWindowsName(addr)
    if windowName is not None:
        try:
            print("Active window title:", windowName)
            window = gw.getWindowsWithTitle(windowName)
            if num >= len(window): num = len(window) - 1
            return window[num]
        except Exception:
            print("Error = ", addr)
            return None
    else:
        print("No active window found.")
        return None
    addr = addr + "GetActiveWindowName ->"


def minimiseAllWindows(addr):
    pyautogui.hotkey(["win", "d"])


#
# def AAAAAAA():
#     app = Application(backend="uia").start("path_to_your_application.exe")
#     window = app.window(title="Your Window Title")
#
#     # Switching to a frame or panel if it's recognized as a separate element
#     frame = window.child_window(title="Your Frame Title", control_type="Frame")
#     frame.click()  # Perform actions within the frame


def SwitchingWindows(addr, FrameNumber):
    # Get all currently open windows
    windows = gw.getAllTitles()

    # Filter out background or non-visible windows
    visible_windows = [window for window in windows if gw.getWindowsWithTitle(window)[0].visible]
    print(visible_windows)
    # Check if there are at least two visible windows
    if len(visible_windows) >= 2:
        # Activate the second visible window
        second_window = gw.getWindowsWithTitle(visible_windows[FrameNumber])[0]
        second_window.activate()
        print(f"Switched focus to: {second_window.title}")
    else:
        print("Not enough visible windows to switch to the second window.")


def SwitchingFocusToNextActiveWindow(addr):
    SwitchingWindows(addr, 2)


def SwitchingFocusToSecondActiveWindow(addr):
    SwitchingWindows(addr, 2)

# SwitchingWindows("", 2)
minimiseAllWindows("addr")