import glob
import os


def find_app_by_partial_name(partial_name):
    # Path where applications are installed on Windows
    app_paths = [
        os.path.join(os.environ["ProgramFiles"], "*"),
        os.path.join(os.environ["ProgramFiles(x86)"], "*")
    ]

    found_apps = set()
    for path in app_paths:
        search_pattern = os.path.join(path, f"*{partial_name}*")
        matching_apps = glob.glob(search_pattern, recursive=True)
        found_apps.update(matching_apps)

    return found_apps


partial_name = "notepad"  # Replace this with the partial name you have

matching_apps = find_app_by_partial_name(partial_name)
if matching_apps:
    print("Matching applications found:")
    for app in matching_apps:
        print(app)
else:
    print("No matching applications found.")
