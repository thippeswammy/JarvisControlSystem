import os
import time

import pandas as pd
import psutil

from Jarvis.Data.JSON_Information_Center import AddDate

# Constants
FILE_NAME = r"F:/RunningProjects/JarvisControlSystem/Jarvis/Data/Data_Information_Value/RecentAppName"
TEXT_LOG_1 = r"Data/Data_Information_Value/newly_opened_apps45.txt"
TEXT_LOG_2 = r"Data/Data_Information_Value/newly_opened_apps54.txt"
EXCEL_LOG = r"Data/Data_Information_Value/newly_opened_apps.xlsx"


def append_to_excel(new_apps, new_paths, excel_file):
    os.makedirs(os.path.dirname(excel_file), exist_ok=True)
    df = pd.DataFrame({'AppName': new_apps, 'Path': new_paths})
    try:
        existing_df = pd.read_excel(excel_file)
        combined_df = pd.concat([existing_df, df], ignore_index=True)
    except FileNotFoundError:
        combined_df = df
    combined_df.to_excel(excel_file, index=False)


def get_opened_apps():
    apps, paths = set(), set()
    for proc in psutil.process_iter(['name', 'exe']):
        try:
            apps.add(proc.info['name'])
            if proc.info['exe']:
                paths.add(proc.info['exe'])
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
            continue
    return apps, paths


# Initial snapshot
previous_apps, previous_paths = get_opened_apps()


def RecentAppPerformanceMonitorFun():
    global previous_apps, previous_paths

    current_apps, current_paths = get_opened_apps()

    new_apps = current_apps - previous_apps
    new_paths = current_paths - previous_paths

    if new_apps:
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')

        # Log app names
        with open(TEXT_LOG_1, 'a') as f1:
            f1.write(f"Timestamp: {timestamp}\nNewly Opened Apps:\n")
            for app in new_apps:
                f1.write(f"- {app}\n")
            f1.write("\n")

        # Prepare matching paths for new apps
        matched_paths = list(new_paths)[:len(new_apps)]
        app_list = list(new_apps)

        # Log app names with paths
        with open(TEXT_LOG_2, 'a') as f2:
            for app, path in zip(app_list, matched_paths):
                f2.write(f"{app} ---> {path}\n")
            f2.write("\n")

        # Append to Excel
        append_to_excel(app_list, matched_paths, EXCEL_LOG)

        # Update JSON
        for app, path in zip(app_list, matched_paths):
            AddDate(FILE_NAME, app, [path])

    previous_apps.clear()
    previous_apps.update(current_apps)
    previous_paths.clear()
    previous_paths.update(current_paths)

    time.sleep(1)
