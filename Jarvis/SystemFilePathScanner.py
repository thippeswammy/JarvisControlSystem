import os
from Jarvis.Data.XLSX_Information_Center import FileLocationHandeling

filelist = []
namelist = []

FileType_Application = ['.exe', '.lnk']

path = ['C:/ProgramData', r'C:\Program Files\WindowsApps'
                          r'C:\Users\Default\AppData',
        r'C:\Users\thipp\AppData\Roaming\Microsoft\Windows\Start Menu\Programs',
        r'C:\Windows']


def GetAllFilePath(addr):
    FLH_ = FileLocationHandeling()
    number = 1
    for n in range(0, len(path)):
        for root, dirs, files in os.walk(path[n]):
            for file in files:
                if file[-4:] == ".lnk":
                    FLH_.AddElements(AppName=file, PathFile=os.path.join(root, file), Count=number, i=number)
                    number += 1
                elif file[-4:] == ".exe":
                    FLH_.AddElements(AppName=file, PathFile=os.path.join(root, file), Count=number, i=number)
                    number += 1
    File_save("AppNameList")
    addr = addr + "GetAllFilePath -> "
    return addr


def GetFilePath(file_name, addr):
    for n in range(0, len(path), 1):
        _filename = file_name
        for root, dirs, files in os.walk(path[n]):
            for file in files:
                # append the file name to the list
                if _filename.lower() == file.lower()[:-4] and file.lower()[-4:] in FileType_Application:
                    if file[-4:] == ".exe":
                        return os.path.join(root, file)
                    elif file[-4:] == ".lnk":
                        return get_exe_path(os.path.join(root, file), addr + "get_exe_path -> ")
                    else:
                        return ""
    addr = addr + "GetFilePath -> "
    return ""

# print(GetAllFilePath("hhh"))
