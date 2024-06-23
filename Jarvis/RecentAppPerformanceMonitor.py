import os
import time
import psutil
import pandas as pd

from Jarvis.Data.JSON_Information_Center import AddDate

FileName = r"F:/RunningProjects/JarvisControlSystem/Jarvis/Data/Data_Information_Value/RecentAppName"


def append_to_excel(new_apps, new_path, excel_file):
    os.makedirs(os.path.dirname(excel_file), exist_ok=True)
    data = {'AppName': new_apps, 'Path': new_path}
    df = pd.DataFrame(data)
    try:
        existing_df = pd.read_excel(excel_file)
        combined_df = pd.concat([existing_df, df], ignore_index=True)
    except FileNotFoundError:
        combined_df = df
    combined_df.to_excel(excel_file, index=False)


def get_opened_apps():
    current_apps = []
    current_path = []
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            current_apps.append(proc.info['name'])
            current_path.append(proc.info['exe'])
            current_apps = list(set(current_apps))
            current_path = list(set(current_path))
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
            pass

    return [set(current_apps), set(current_path)]


previous_apps = get_opened_apps()


def RecentAppPerformanceMonitorFun():
    global previous_apps  # Declare previous_apps as a global variable

    current_apps = get_opened_apps()

    # Identify newly opened apps
    new_apps = current_apps[0] - previous_apps[0]
    new_path = current_apps[1] - previous_apps[1]

    if new_apps:
        with open('Data\Data_Information_Value/newly_opened_apps45.txt',
                  'a') as file:
            file.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            file.write("Newly Opened Apps:\n")
            for app in new_apps:
                file.write(f"- {app}\n")
            file.write("\n")
        new_apps = list(new_apps)
        new_path = list(new_path)
        with open('Data\Data_Information_Value/newly_opened_apps54.txt',
                  'a') as file:
            for i in range(len(new_apps)):
                file.write(new_apps[i])
                file.write(" --->  " + new_path[i] + " \n")
            file.write("\n")
        append_to_excel(new_apps, new_path[:len(new_apps)],
                        r"Data\Data_Information_Value/newly_openedḍ_apps.xlsx")

        for i in range(len(new_apps)):
            AddDate(FileName, new_apps[i], [new_path[i]])

    previous_apps = current_apps
    time.sleep(1)  # Adjust the interval as needed
