import wmi


def enable_bluetooth():
    c = wmi.WMI()
    # Enable Bluetooth service
    bt_service = c.Win32_Service(Name='bthserv')[0]
    bt_service.ChangeStartMode(StartMode="Auto")
    bt_service.StartService()


def disable_bluetooth():
    c = wmi.WMI()
    bt_service = c.Win32_Service(Name='bthserv')[0]
    bt_service.StopService()


enable_bluetooth()

# disable_bluetooth()
