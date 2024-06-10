import wmi

products = wmi.WMI().query("select Name, Version from Win32_Product")

installed_apps = [(product.Name, product.Version) for product in products]

print("Installed applications:", installed_apps)
