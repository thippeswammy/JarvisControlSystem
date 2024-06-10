import win32com.client


def get_exe_path(lnk_file, addr):
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(lnk_file)
    exe_path = shortcut.Targetpath
    addr = addr + "get_exe_path "
    if exe_path:
        # print(f"The .exe file path is: {exe_path}")
        return exe_path
    else:
        # print("The .exe file path could not be found.")
        return lnk_file

# lnk_file = r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Brave.lnk"

# get_exe_path(lnk_file)
