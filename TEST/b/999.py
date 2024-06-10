import time

import psutil


def get_running_apps_with_paths():
    apps = {}
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            pid = proc.info['pid']
            app_name = proc.info['name']
            app_path = proc.info['exe']

            apps[pid] = {'name': app_name, 'path': app_path}
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
            pass
    return apps


# Record apps every x seconds (adjust interval as needed)
record_interval = 5

while True:
    running_apps = get_running_apps_with_paths()

    # Save the file paths of currently running applications to a text file
    with open('opened_apps_record.txt', 'a') as file:
        file.write(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        listName = []
        listPath = []

        for app in running_apps.values():
            file.write(f"App Name: {app['name']}  --->")
            file.write(f"App Path: {app['path']}\n")
            if not listPath.__contains__(app['name']):
                listName.append(app['name'])
                listPath.append(app['path'])
        file.write("\n")
    listName = list(set(listName))
    listPath = list(set(listPath))
    with open('opened_apps_record2.txt', 'a') as file:
        file.write(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        for i in range(len(listName)):
            file.write(f"App Name: {listName[i]}  --->  ")
            file.write(f"{listPath[i]}\n")

    time.sleep(record_interval)
