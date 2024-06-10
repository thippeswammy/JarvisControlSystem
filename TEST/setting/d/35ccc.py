import os


def open_multitasking_settings():
    try:
        os.system("start ms-settings:multitasking")
        print("Multitasking settings opened.")
    except Exception as e:
        print(f"Failed to open Multitasking settings. Error: {e}")


# Call the function to open Multitasking settings
open_multitasking_settings()
