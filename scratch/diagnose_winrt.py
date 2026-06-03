import ctypes
from ctypes import wintypes
import os

dll_path = r"F:\RunningProjects\JarvisControlSystem\native\Microsoft-UI-UIAutomation\src\UIAutomation\x64\Release\Microsoft.UI.UIAutomation.dll"
print(f"[*] Checking DLL existence at: {dll_path}")
if not os.path.exists(dll_path):
    print("[x] Error: DLL file not found!")
    exit(1)

# Add DLL directory to search path
if hasattr(os, 'add_dll_directory'):
    os.add_dll_directory(os.path.dirname(dll_path))

try:
    print("[*] Loading DLL via ctypes...")
    dll = ctypes.WinDLL(dll_path)
    print("[+] DLL loaded successfully!")
    
    # WinRT DllGetActivationFactory function prototype:
    # HRESULT DllGetActivationFactory(HSTRING activatableClassId, IActivationFactory** factory)
    print("[*] Locating DllGetActivationFactory export...")
    try:
        DllGetActivationFactory = dll.DllGetActivationFactory
        DllGetActivationFactory.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
        DllGetActivationFactory.restype = ctypes.c_long  # HRESULT
        print("[+] Found DllGetActivationFactory export!")
    except AttributeError:
        print("[x] Error: DllGetActivationFactory export not found in DLL!")
        exit(1)
        
    # Set up Windows Ole32 / WinRT HSTRING APIs
    print("[*] Setting up WinRT HSTRING helper APIs...")
    ole32 = ctypes.WinDLL('ole32')
    combase = ctypes.WinDLL('combase')
    
    # Initialize COM / WinRT apartment
    # HRESULT RoInitialize(RO_INIT_TYPE initType)
    # RO_INIT_MULTITHREADED = 1
    combase.RoInitialize.argtypes = [wintypes.DWORD]
    combase.RoInitialize.restype = ctypes.c_long
    hr_init = combase.RoInitialize(1)
    print(f"[+] RoInitialize returned HRESULT: 0x{hr_init & 0xffffffff:08X}")
    
    # WindowsCreateString prototype:
    # HRESULT WindowsCreateString(const wchar_t* sourceString, UINT32 length, HSTRING* string)
    combase.WindowsCreateString.argtypes = [ctypes.c_wchar_p, wintypes.UINT, ctypes.POINTER(ctypes.c_void_p)]
    combase.WindowsCreateString.restype = ctypes.c_long
    
    # WindowsDeleteString prototype:
    # HRESULT WindowsDeleteString(HSTRING string)
    combase.WindowsDeleteString.argtypes = [ctypes.c_void_p]
    combase.WindowsDeleteString.restype = ctypes.c_long

    class_name = "Microsoft.UI.UIAutomation.AutomationRemoteOperation"
    print(f"[*] Creating WinRT HSTRING for class: '{class_name}'...")
    hstring = ctypes.c_void_p(0)
    hr_str = combase.WindowsCreateString(class_name, len(class_name), ctypes.byref(hstring))
    
    if hr_str != 0:
        print(f"[x] WindowsCreateString failed with HRESULT: 0x{hr_str & 0xffffffff:08X}")
        exit(1)
    print("[+] HSTRING created successfully!")
    
    print("[*] Invoking DllGetActivationFactory to activate class factory...")
    factory_ptr = ctypes.c_void_p(0)
    
    # This might throw or crash if registration-free WinRT fails or raises a fail-fast exception
    hr_act = DllGetActivationFactory(hstring, ctypes.byref(factory_ptr))
    
    print(f"[+] DllGetActivationFactory returned HRESULT: 0x{hr_act & 0xffffffff:08X}")
    if hr_act == 0:
        print("[+] SUCCESS! Class factory resolved successfully. Registration-Free WinRT works!")
    else:
        print(f"[!] Warning: HRESULT indicates failure (e.g. 0x80040154 - REGDB_E_CLASSNOTREG)")
        
    # Cleanup HSTRING
    combase.WindowsDeleteString(hstring)
    combase.RoUninitialize()

except Exception as e:
    print(f"[x] Diagnostic run failed with exception: {e}")
