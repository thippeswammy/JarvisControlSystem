import time

import pyautogui


def turn_on_bluetooth():
    # Open the Windows Settings
    pyautogui.hotkey('win', 'i')
    time.sleep(1)

    # Type "Bluetooth" in the search box
    pyautogui.write('Bluetooth')
    time.sleep(1)

    # Press Enter to open Bluetooth settings
    pyautogui.press('enter')
    time.sleep(1)

    # Check if Bluetooth is already on
    if "Bluetooth" in pyautogui.screenshot().getdata():
        print("Bluetooth is already turned on.")
        return

    # Turn on Bluetooth
    pyautogui.press('space')
    time.sleep(1)

    print("Bluetooth is turned on.")


if __name__ == "__main__":
    turn_on_bluetooth()
