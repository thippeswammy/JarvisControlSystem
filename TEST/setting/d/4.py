# Example for Linux using pydbus
from pydbus import SystemBus


def enable_bluetooth():
    bus = SystemBus()
    bluez = bus.get('org.bluez', '/org/bluez')
    adapter = bluez.Adapter1
    adapter.Powered = True  # Set the 'Powered' property to True to enable Bluetooth


def disable_bluetooth():
    bus = SystemBus()
    bluez = bus.get('org.bluez', '/org/bluez')
    adapter = bluez.Adapter1
    adapter.Powered = False  # Set the 'Powered' property to False to disable Bluetooth


enable_bluetooth()
