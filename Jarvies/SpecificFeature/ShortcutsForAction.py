import pyautogui


def minimiseAllWindows(addr):
    pyautogui.hotkey(["win", "d"])


def openSetting(addr):
    pyautogui.hotkey(["win", "i"])


def moveToNextTab(addr):
    pyautogui.hotkey(["alt", "i"])
