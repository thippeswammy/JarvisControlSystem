from Data.JSON_Information_Center import loadDate
from Jarvies.KeyBoard_Controls import hold_key
from Jarvies.KeyBoard_Controls import press_key
from Jarvies.KeyBoard_Controls import release_key
from Jarvies.KeyBoard_Controls import type_text
from Jarvies.RunningApplication import close_application_by_name
from Jarvies.RunningApplication import open_application
from Jarvies.SpecificFeature.WINDOWS import Control_Windows
from Jarvies.SpecificFeature.WINDOWS import OpenByWindows_search as OpenByWindows_search
from Jarvies.SpecificFeature.WINDOWS import SearchByWindowsFiles as SearchByWindowsFiles
from Jarvies.SpecificFeature.WINDOWS import windows_search
from Jarvies.Speech_Recognition import ClosingSpeaker
from Jarvies.Speech_Recognition import OpeningSpeaker
from Jarvies.Speech_Recognition import PressingSpeaker
from Jarvies.Speech_Recognition import Speaker
from Jarvies.Speech_Recognition import TypingSpeaker
from Jarvies.Speech_Recognition import holdingSpeaker
from Jarvies.Speech_Recognition import releasingSpeaker

_IsJarvisCalled = False
_IsTypingActivated = False
_openByWindowsSearch = False
_delay = 3

# from Jarvies.Main import _IsTypingActivated
# from Jarvies.Main import _openByWindows
# from Jarvies.Main import _delay

File_Name1 = r"..\Data\Data_Information_Value/Data1.json"

DATA = loadDate(File_Name1)

activating_jarvis = ['hi', 'hi jarvis', 'jarvis', 'start jarvis', 'jarvis start']
deactivating_jarvis = ['jarvis close', 'close jarvis', 'jarvis stop', 'stop jarvis']

typing_jarvies = ['start typing', 'typing start', 'activate typing', 'typing activate']
stop_typing_jarvies = ['stop typing', 'typing stop', 'deactivate typing', 'typing deactivateactivate']

press_key_jarvis = ['press']
press_key_jarvis1 = ['press', 'press key', 'key press']

hold_key_jarvis = ['hold', 'holdkey', 'hold key', 'keydown']
release_key_jarvis = ['release', 'releasekey', 'release key']

OpenApp_jarvis = ['open', 'start', 'run']
CloseApp_jarvis = ['close', 'exit', 'terminate']

SearchApp_jarvis = ['search', 'find', 'windows search', 'window search', 'search windows', 'search window',
                    'search by windows', 'search by window']

WindowsSearchBarAccess_jarvis = ['open by search', 'open by windows', 'open by windows search']

closeByWindows_jarvis = ['stop by search', 'stop by windows', 'stop by windows search']


class ActivationFunction:
    def __init__(self):
        pass


def MainActivation(operation, addr):
    if operation in activating_jarvis:
        _IsJarvisCalled = True
        Speaker("activating jarvis", addr + "activating_jarvis -> ")
        print("activating jarvis", addr + "COMPLETED")
    elif operation in deactivating_jarvis:
        _IsJarvisCalled = False
        Speaker("destroying jarvis", addr + "deactivating_jarvis -> ")
        print("destroying jarvis", addr + "COMPLETED")
    elif operation in typing_jarvies:
        _IsTypingActivated = True
        Speaker("activating typing", addr + "typing_jarvies -> ")
        print("activating typing", addr + "COMPLETED")
    elif operation in stop_typing_jarvies:
        _IsTypingActivated = False
        Speaker("deactivate typing", addr + "stop_typing_jarvies -> ")
        print("deactivate typing", addr + "COMPLETED")
    elif operation in WindowsSearchBarAccess_jarvis:
        _openByWindows = False
        Speaker("Activating opening by windows search bar", addr + "WindowsSearchBarAccess_jarvis -> ")
        print("Activating opening by windows search bar", addr + "COMPLETED")
    elif operation in closeByWindows_jarvis:
        _openByWindows = False
        Speaker("opening by windows file", addr + "closeByWindows_jarvis -> ")
        print("Deactivating opening by windows search bar", addr + "COMPLETED")
    else:
        SubActivation(operation, addr + "SubActivation -> ")


def SubActivation(operation, addr):
    if operation == "SubActivation ":
        return
    if Control_Search(operation, addr + " Control_Search -> "):
        return
    if Control_Keyboard(operation, addr + "Control_Keyboard -> "):
        return
    if Control_AppOpening(operation, addr + "Control_AppOpening -> "):
        return
    if Control_AppClosing(operation, addr + "Control_AppClosing -> "):
        return
    if Control_Windows(operation, addr + "Control_Windows -> ") == True:
        return


def Control_Search(operation, addr):
    Multi_operation = operation.split()
    if Multi_operation[0] in SearchApp_jarvis or (
            len(Multi_operation) > 2 and (Multi_operation[0] + " " + Multi_operation[1])) in SearchApp_jarvis or (
            len(Multi_operation) > 3 and
            Multi_operation[0] + " " + Multi_operation[1] + " " + Multi_operation[2]) in SearchApp_jarvis:
        windows_search(Multi_operation, addr + "windows_search -> ")
        return True
    return False


def Control_Keyboard(operation, addr):
    Multi_operation = operation.split()
    if _IsTypingActivated:
        TypingSpeaker(operation, addr + "_IsTypingActivated -> TypingSpeaker -> ")
        type_text(operation, addr + "_IsTypingActivated -> type_operation -> ")
        return True
    if Multi_operation[0] in hold_key_jarvis:
        try:
            Multi_operation = Multi_operation[1:]
        except Exception:
            print("Error = ", addr + "holdkey_jarvis")
            return
        if Multi_operation.__contains__("key"):
            Multi_operation.remove("key")
        if Multi_operation.__contains__("keys"):
            Multi_operation.remove("keys")
        holdingSpeaker(Multi_operation, addr + "holdkey_jarvis -> holdingSpeaker -> ")
        hold_key(Multi_operation, addr + "holdkey_jarvis -> hold_key -> ")
        return True
    elif Multi_operation[0] in release_key_jarvis:
        try:
            Multi_operation = Multi_operation[1:]
        except Exception:
            print("Error = ", addr + "holdkey_jarvis")
            return
        if Multi_operation.__contains__("key"):
            Multi_operation.remove("key")
        if Multi_operation.__contains__("keys"):
            Multi_operation.remove("keys")
        releasingSpeaker(Multi_operation, addr + "relasekey_jarvis -> releasingSpeaker -> ")
        release_key(Multi_operation, addr + "relasekey_jarvisv -> release_key -> ")
        return True
    elif Multi_operation[0] in press_key_jarvis:
        try:
            Multi_operation = Multi_operation[1:]
        except Exception:
            print("Error = ", addr + "holdkey_jarvis")
            return
        if Multi_operation.__contains__("key"):
            Multi_operation.remove("key")
        if Multi_operation.__contains__("keys"):
            Multi_operation.remove("keys")
        PressingSpeaker(Multi_operation, addr + "presskey_jarvis -> PressingSpeaker ->")
        press_key(Multi_operation, addr + "presskey_jarvis -> press_key -> ")
        return True
    else:
        return False


def Control_AppOpening(operation, addr):
    Multi_operation = operation.split()
    if Multi_operation[0] in OpenApp_jarvis and not _openByWindowsSearch:
        try:
            AppName, AppNameAddres = SearchByWindowsFiles(Multi_operation,
                                                          addr + " OpenApp_jarvis -> Search_by_windows -> OpenByWindowsSearch ->")
            if AppName != None:
                val = open_application(AppName[:-4], AppNameAddres, addr + "OpenApp_jarvis -> open_application -> ")
            else:
                val = "Search by windows"
            print("SubAction : ", val)
            if val == "Search by windows":
                print("Serch by windows Heyy", )
                # SearchByWindowsFiles(Multi_operation,
                #                      addr + " OpenApp_jarvis -> Search_by_windows -> OpenByWindowsSearch ->")
                OpenByWindows_search(Multi_operation,
                                     addr + " OpenApp_jarvis -> Search_by_windows -> OpenByWindowsSearch ->")
                OpeningSpeaker(Multi_operation, addr + "OpenApp_jarvis -> Search_by_windows -> OpeningSpeaker -> ")
                return True
            OpeningSpeaker(Multi_operation, addr + "OpenApp_jarvis -> OpeningSpeaker -> ")
            return True
        except Exception:
            print("Erron = ", addr)
            return True
    elif Multi_operation[0] in OpenApp_jarvis and _openByWindowsSearch:
        OpenByWindows_search(Multi_operation, addr + "_openByWindows -> OpenByWindowsSearch -> ")
        OpeningSpeaker(Multi_operation, addr + "_openByWindows -> OpeningSpeaker -> ")
        return True
    return False


def Control_AppClosing(operation, addr):
    Multi_operation = operation.split()
    if Multi_operation[0] in CloseApp_jarvis:
        try:
            # close_application(" ".join(Multi_operation[1:]))
            close_application_by_name(" ".join(Multi_operation[1:]),
                                      addr + "CloseApp_jarvis -> close_application_by_name -> ")
            ClosingSpeaker(Multi_operation, addr + "CloseApp_jarvis -> close_application_by_name -> ")
            return True
        except Exception:
            print("Erron = ", addr)
            return True
    return False


def Control_Window(operation, addr):
    Control_Windows(operation, addr + "WINDOWS.Control_Windows -> ")
