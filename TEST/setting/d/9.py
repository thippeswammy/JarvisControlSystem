import pybluez

adapter = pybluez.find_first_adapter()
adapter.power_on()
print("Bluetooth is now enabled.")
