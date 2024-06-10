# With psutil
# With winapps
import psutil
from winapps import list_installed

installed_apps = [app.name() for app in psutil.process_iter()]

print("Installed applications:", installed_apps)

installed_apps = list_installed()

print("Installed applications:", installed_apps)
