import os


def open_bluetooth_settings():
    try:
        os.system("start ms-settings:bluetooth")
        print("Bluetooth and Other Devices Settings opened.")
    except Exception as e:
        print(f"Failed to open Bluetooth and Other Devices Settings. Error: {e}")


def open_printers_and_scanners_settings():
    try:
        os.system("start ms-settings:printers")
        print("Printers and Scanners Settings opened.")
    except Exception as e:
        print(f"Failed to open Printers and Scanners Settings. Error: {e}")


def open_mouse_settings():
    try:
        os.system("start ms-settings:mousetouchpad")
        print("Mouse Settings opened.")
    except Exception as e:
        print(f"Failed to open Mouse Settings. Error: {e}")


def open_touchpad_settings():
    try:
        os.system("start ms-settings:devices-touchpad")
        print("Touchpad Settings opened.")
    except Exception as e:
        print(f"Failed to open Touchpad Settings. Error: {e}")


def open_typing_settings():
    try:
        os.system("start ms-settings:typing")
        print("Typing Settings opened.")
    except Exception as e:
        print(f"Failed to open Typing Settings. Error: {e}")


def open_pen_and_windows_ink_settings():
    try:
        os.system("start ms-settings:pen")
        print("Pen and Windows Ink Settings opened.")
    except Exception as e:
        print(f"Failed to open Pen and Windows Ink Settings. Error: {e}")


def open_autoplay_settings():
    try:
        os.system("start ms-settings:autoplay")
        print("AutoPlay Settings opened.")
    except Exception as e:
        print(f"Failed to open AutoPlay Settings. Error: {e}")


def open_usb_settings():
    try:
        os.system("start ms-settings:usb")
        print("USB Settings opened.")
    except Exception as e:
        print(f"Failed to open USB Settings. Error: {e}")


# Call the functions to open the corresponding settings
open_bluetooth_settings()
open_printers_and_scanners_settings()
open_mouse_settings()
open_touchpad_settings()
open_typing_settings()
open_pen_and_windows_ink_settings()
open_autoplay_settings()
open_usb_settings()
