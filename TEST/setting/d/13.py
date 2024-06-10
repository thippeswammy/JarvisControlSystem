import ctypes


def turn_on_bluetooth():
    # Load the necessary DLL
    shell32 = ctypes.windll.shell32

    # Execute the control panel command to open Bluetooth settings
    shell32.ShellExecuteW(None, "open", "control.exe", "bthprops.cpl", None, 1)


if __name__ == "__main__":
    turn_on_bluetooth()
