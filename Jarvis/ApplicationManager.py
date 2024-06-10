import os
import psutil
import subprocess
from Jarvis.SystemFilePathScanner import GetFilePath
from typing import Optional


def open_application(app_name: str, app_name_adders: Optional[str], addr: str) -> Optional[str]:
    if app_name_adders == "":
        app_path = GetFilePath(app_name, addr + "GetFilePath -> ")
    else:
        app_path = app_name_adders

    if app_path == "":
        return "Search by windows"

    try:
        if os.path.exists(app_path):
            subprocess.Popen(app_path, shell=True)
            return True
            # print(f"Opened application at path: {app_path}", addr + "COMPLETED")
        else:
            print(f"Application not found at path: {app_path}", addr)
            return False
    except Exception as e:
        print(f"Error opening application: {e} Running Application at =", addr)
        return False


def close_application_by_name(app_name: str, addr: str) -> bool:
    for process in psutil.process_iter(['pid', 'name']):
        if process.info['name'] == app_name + ".exe":
            app_name += ".exe"
            pid = process.info['pid']
            process = psutil.Process(pid)
            process.terminate()
            # print(f"Application '{app_name}' with PID {pid} has been terminated.", addr + " .exe COMPLETED")
            return True
        if process.info['name'] == app_name + ".lnk":
            app_name += ".lnk"
            pid = process.info['pid']
            process = psutil.Process(pid)
            process.terminate()
            # print(f"Application '{app_name}' with PID {pid} has been terminated.", addr + ".lnk COMPLETED")
            return True
    # print(f"Application '{app_name}' not found.", addr)
    return False


def close_application(app_name: str, addr: str) -> None:
    app_path = GetFilePath(app_name, addr + "GetFilePath -> ")
    # print("path = ", app_path)
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            if proc.info['exe'] == app_path:
                pid = proc.pid
                os.kill(pid, 9)
                return True
                # print(f"Closed application with path: {app_path}", addr + "COMPLETED")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # print("Error Running Application at =", addr)
            return False
