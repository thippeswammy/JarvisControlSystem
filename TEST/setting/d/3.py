import time

import pyautogui


def open_settings():
    # Simulate opening the settings window (example for Windows)
    pyautogui.hotkey('win', 'i')  # Press Windows + I to open Settings
    time.sleep(2)  # Add a delay to ensure the Settings window opens


def toggle_bluetooth():
    # Simulate navigating to Bluetooth settings and toggling the switch
    # Adjust the coordinates based on your screen resolution and UI elements
    pyautogui.moveTo(100, 100)  # Example: Move to a specific coordinate (Bluetooth settings)
    pyautogui.click()  # Simulate a click to open Bluetooth settings
    time.sleep(1)
    pyautogui.moveTo(150, 150)  # Example: Move to the toggle switch for Bluetooth
    pyautogui.click()  # Simulate a click to toggle Bluetooth


open_settings()
toggle_bluetooth()
