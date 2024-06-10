import os
import subprocess

import psutil

from Jarvies.SystemFilePathScanner import GetFilePath


def open_application(app_name, app_name_addrs, addr):
    if app_name_addrs == "":
        app_path = GetFilePath(app_name, addr + "GetFilePath -> ")
    else:
        app_path = app_name_addrs
    if app_path == "":
        return "Search by windows"
    try:
        if os.path.exists(app_path):
            subprocess.Popen(app_path, shell=True)
            print(f"Opened application at path: {app_path}", addr + "COMPLETED")
        else:
            print(f"Application not found at path: {app_path}", addr)
    except Exception as e:
        print(f"Error opening application: {e} Running Application at =", addr)


def close_application_by_name(app_name, addr):
    for process in psutil.process_iter(['pid', 'name']):
        if process.info['name'] == app_name + ".exe":
            app_name += ".exe"
            pid = process.info['pid']
            process = psutil.Process(pid)
            process.terminate()
            print(f"Application '{app_name}' with PID {pid} has been terminated.", addr + " .exe COMPLETED")
            return
        if process.info['name'] == app_name + ".lnk":
            app_name += ".lnk"
            pid = process.info['pid']
            process = psutil.Process(pid)
            process.terminate()
            print(f"Application '{app_name}' with PID {pid} has been terminated.", addr + ".lnk COMPLETED")
            return
    print(f"Application '{app_name}' not found.", addr)


def close_application(app_name, addr):
    # Get the process ID (PID) of the application by its path
    app_path = GetFilePath(app_name, addr + "GetFilePath -> ")
    print("path = ", app_path)
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            if proc.info['exe'] == app_path:
                pid = proc.pid
                # Terminate the process by PID
                os.kill(pid, 9)
                print(f"Closed application with path: {app_path}", addr + "COMPLETED")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            print("Error Running Application at =", addr)
