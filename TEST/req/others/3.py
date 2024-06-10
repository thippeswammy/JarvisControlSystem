import wmi


def search_processes(process_name):
    c = wmi.WMI()
    for process in c.Win32_Process():
        # if process.Name == process_name:
        #     print(f"Process {process_name} found with PID: {process.ProcessId}")
        print(process.Name)


search_processes("google.exe")
