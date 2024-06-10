import win32com

adapter = win32com.GetObject(f"winmgmts://./CIMv2:Win32_PnPSignedDriver?Description='{your_adapter_name}'")
adapter.Enabled = True
print(f"Bluetooth adapter '{your_adapter_name}' is now enabled.")
