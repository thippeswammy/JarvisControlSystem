import os

from Data.XLSX_Information_Center import FileLocationHandeling  # Import the class from the module
from Jarvies.LnkIntoExe import converter

filelist = []
namelist = []

FileType_Application = ['.exe', '.lnk']

# path1 = ['C:/ProgramData/Microsoft/Windows/Start Menu/Programs']

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
    FLH_.File_save("AppNameList")
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
                        return converter.get_exe_path(os.path.join(root, file), addr + "get_exe_path -> ")
                    else:
                        return ""
    addr = addr + "GetFilePath -> "
    return ""


# print(GetAllFilePath("hhh"))
