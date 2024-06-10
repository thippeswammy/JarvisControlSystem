import os


def open_projection_settings():
    try:
        os.system("start ms-settings:project")
        print("Projection to this PC Settings opened.")
    except Exception as e:
        print(f"Failed to open Projection to this PC Settings. Error: {e}")


# Call the function to open Projection to this PC Settings
open_projection_settings()
