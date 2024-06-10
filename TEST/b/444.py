import psutil


def get_exe_path_from_window_name(window_name):
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            print(proc)
            if proc.info['name'] == "explorer.exe":
                print(proc.info['name'], "2222")
                p = psutil.Process(proc.info['pid'])
                print(p, "2222", psutil)
                print(window_name.lower(), "3333", p.name().lower())
                if window_name.lower() in p.name().lower():
                    return p.exe()
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
            pass
    return None


# Example: Replace 'FrameName' with the name of your window
exe_path = get_exe_path_from_window_name('Untitled - Notepad')
if exe_path:
    print(f"Executable path for 'FrameName': {exe_path}")
else:
    print("Window not found or executable path not available.")
