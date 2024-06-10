import time

from Jarvies.SpecificFeature.WindowsFrame import GetActiveWindowsFrame
from Jarvies.SpecificFeature.WindowsFrame import GetActiveWindowsFrameAll

delay = 5


def CloseActiveWindow(addr):
    time.sleep(delay)
    window = GetActiveWindowsFrame(addr)
    window.close()
    print("closing current windows", addr + "COMPLETED")


def CloseActiveWindow(addr, num):
    time.sleep(delay)
    window = GetActiveWindowsFrame(addr, num - 1)
    if window is not None:
        window.close()
    print("closing current windows", addr + "COMPLETED")


def CloseActiveWindowAll(addr):
    time.sleep(delay)
    windows = GetActiveWindowsFrameAll(addr)
    for window in windows:
        window.close()
    print("closing current windows", addr + "COMPLETED")


def maximumActiveWindows(addr):
    time.sleep(delay)
    window = GetActiveWindowsFrame(addr)
    window.maximize()


def minimiseActiveWindows(addr):
    time.sleep(delay)
    window = GetActiveWindowsFrame(addr, 2)
    window.minimize()


def rightActiveWindows(addr):
    time.sleep(delay)
    window = GetActiveWindowsFrame(addr, 2)
    if window is not None:
        window.right()


def leftActiveWindows(addr):
    time.sleep(delay)
    window = GetActiveWindowsFrame(addr, 2)
    window.minimize()


def centerActiveWindows(addr):
    time.sleep(delay)
    window = GetActiveWindowsFrame(addr, 2)
    window.center()


def hideActiveWindows(addr):
    time.sleep(delay)
    window = GetActiveWindowsFrame(addr, 2)
    window.hide()


# CloseActiveWindow()
rightActiveWindows("addr")
# time.sleep(4)
# leftActiveWindows("addr")
