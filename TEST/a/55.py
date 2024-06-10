import pygetwindow as gw


def SwitchingWindows(addr, FrameNumber):
    # Get all currently open windows
    windows = gw.getAllTitles()

    # Filter out background or non-visible windows
    visible_windows = [window for window in windows if gw.getWindowsWithTitle(window)[0].visible]
    '''
    visible_windows1 = [window for window in windows if gw.getWindowsWithTitle(window)[0].isActive]
    visible_windows2 = [window for window in windows if gw.getWindowsWithTitle(window)[0].isMinimized]
    visible_windows3 = [window for window in windows]
    print(visible_windows1)
    print(visible_windows2)
    print(visible_windows3)
    
    '''
    print(visible_windows)
    # Check if there are at least two visible windows
    if len(visible_windows) >= 2:
        # Activate the second visible window
        second_window = gw.getWindowsWithTitle(visible_windows[FrameNumber])[0]
        second_window.activate()
        print(f"Switched focus to: {second_window.title}")
    else:
        print("Not enough visible windows to switch to the second window.")


SwitchingWindows("", 2)


def SwitchingFocusToNextActiveWindow(addr):
    SwitchingWindows(addr, 2)


def SwitchingFocusToSecondActiveWindow(addr):
    SwitchingWindows(addr, 2)
