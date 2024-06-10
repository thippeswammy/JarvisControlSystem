import subprocess


def open_phone_settings():
    try:
        subprocess.run(["start", "ms-settings:phone"], shell=True)
        print("Phone Settings opened.")
    except Exception as e:
        print(f"Failed to open Phone Settings. Error: {e}")


# Call the function to open the Phone settings
open_phone_settings()
