from Jarvis.Data.JSON_Information_Center import loadDate
from Jarvis.KeyboardAutomationController import hold_key, press_key, release_key, type_text
from Jarvis.ApplicationManager import close_application_by_name, open_application
from Jarvis.WindowsFeature import WINDOWS_SystemController
from Jarvis.WindowsDefaultApps.settingControlApp import SettingControlAccess as SettingWindows
from Jarvis.SpeechRecognition import (
    ClosingSpeaker, OpeningSpeaker, PressingSpeaker, Speaker,
    TypingSpeaker, holdingSpeaker, releasingSpeaker
)


class UserCommandProcessor:
    _is_desktop_mode: bool = False
    _is_jarvis_active: bool = False
    _is_typing_active: bool = False
    _lock_opened_windows: bool = False
    _open_by_windows_search: bool = False
    _delay: int = 3

    File_Name1: str = r"Data\Data_Information_Value\Data1.json"
    DATA = loadDate(File_Name1)

    activating_jarvis_cmds: list = ['hi', 'hi jarvis', 'jarvis', 'start jarvis', 'jarvis start']
    deactivating_jarvis_cmds: list = ['jarvis close', 'close jarvis', 'jarvis stop', 'stop jarvis']

    typing_start_cmds: list = ['start typing', 'typing start', 'activate typing', 'typing activate']
    typing_stop_cmds: list = ['stop typing', 'typing stop', 'deactivate typing', 'typing deactivate']

    press_key_cmds: list = ['press', 'press key', 'key press']
    hold_key_cmds: list = ['hold', 'holdkey', 'hold key', 'keydown']
    release_key_cmds: list = ['release', 'releasekey', 'release key']

    open_app_cmds: list = ['open', 'start', 'run']
    close_app_cmds: list = ['close', 'exit', 'terminate']

    desktop_mode_cmds: list = ['set desktop mode', 'go to desktop mode', 'desktop mode', 'goto desktop mode',
                               'start desktop mode']
    normal_mode_cmds: list = ['set normal mode', 'go to normal mode', 'normal mode', 'goto normal mode',
                              'stop desktop mode']

    search_cmds: list = [
        'search', 'find', 'windows search', 'window search', 'search windows',
        'search window', 'search by windows', 'search by window'
    ]

    windows_search_enable_cmds: list = ['open by search', 'open by windows', 'open by windows search']
    windows_search_disable_cmds: list = ['stop by search', 'stop by windows', 'stop by windows search']

    @classmethod
    def main_activation(cls, operation: str, addr: str) -> bool:
        if operation in cls.activating_jarvis_cmds:
            cls._is_jarvis_active = True
            Speaker("activating jarvis", addr + "activating_jarvis -> ")
            return True
        elif operation in cls.deactivating_jarvis_cmds:
            cls._is_jarvis_active = False
            Speaker("destroying jarvis", addr + "deactivating_jarvis -> ")
            return True
        elif operation in cls.typing_start_cmds:
            cls._is_typing_active = True
            Speaker("activating typing", addr + "typing_start_cmds -> ")
            return True
        elif operation in cls.typing_stop_cmds:
            cls._is_typing_active = False
            Speaker("deactivate typing", addr + "typing_stop_cmds -> ")
            return True
        elif operation in cls.windows_search_enable_cmds:
            cls._open_by_windows_search = True
            Speaker("Activating opening by windows search bar", addr + "windows_search_enable_cmds -> ")
            return True
        elif operation in cls.windows_search_disable_cmds:
            cls._open_by_windows_search = False
            Speaker("Deactivating opening by windows search bar", addr + "windows_search_disable_cmds -> ")
            return True
        elif operation in ['open settings', 'open setting']:
            cls._lock_opened_windows = True
            return cls.sub_activation(operation, addr + "sub_activation -> ")
        elif operation in ['close settings', 'close setting'] or (cls._lock_opened_windows and operation in ['close']):
            val = cls.sub_activation(operation, addr + "sub_activation -> ")
            cls._lock_opened_windows = False
            return val
        # elif operation in ['open settings', 'open setting']:
        #     cls._lock_opened_windows = True
        #     return cls.sub_activation(operation, addr + "sub_activation -> ")
        else:
            return cls.sub_activation(operation, addr + "sub_activation -> ")

    @classmethod
    def sub_activation(cls, operation: str, addr: str) -> bool:
        if cls.control_keyboard(operation, addr + "control_keyboard -> "):
            return True
        elif cls.control_opened_windows(operation, addr + "control_opened_windows -> "):
            return True
        elif cls.control_search(operation, addr + "control_search -> "):
            return True
        elif cls.control_app_opening(operation, addr + "control_app_opening -> "):
            return True
        elif cls.control_app_closing(operation, addr + "control_app_closing -> "):
            return True
        elif cls.controlling_active_window(operation, addr + "controlling_active_window -> "):
            return True
        return False

    @classmethod
    def control_search(cls, operation: str, addr: str) -> bool:
        multi_operation = operation.split()
        if (multi_operation[0] in cls.search_cmds or
                (len(multi_operation) > 2 and (multi_operation[0] + " " + multi_operation[1]) in cls.search_cmds) or
                (len(multi_operation) > 3 and multi_operation[0] + " " + multi_operation[1] + " " + multi_operation[
                    2]) in cls.search_cmds):
            return WINDOWS.DesktopSystemController.search_windows_for_term(multi_operation, addr + "windows_search -> ")
        return False

    @classmethod
    def control_keyboard(cls, operation: str, addr: str) -> bool:
        multi_operation = operation.split()

        if cls._is_typing_active:
            TypingSpeaker(operation, addr + "_is_typing_active -> TypingSpeaker -> ")
            type_text(operation, addr + "_is_typing_active -> type_operation -> ")
            return True

        if multi_operation[0] in cls.hold_key_cmds:
            multi_operation = multi_operation[1:]
            if "key" in multi_operation:
                multi_operation.remove("key")
            if "keys" in multi_operation:
                multi_operation.remove("keys")
            holdingSpeaker(multi_operation, addr + "hold_key_cmds -> holdingSpeaker -> ")
            hold_key(multi_operation, addr + "hold_key_cmds -> hold_key -> ")
            return True

        elif multi_operation[0] in cls.release_key_cmds:
            multi_operation = multi_operation[1:]
            if "key" in multi_operation:
                multi_operation.remove("key")
            if "keys" in multi_operation:
                multi_operation.remove("keys")
            releasingSpeaker(multi_operation, addr + "release_key_cmds -> releasingSpeaker -> ")
            release_key(multi_operation, addr + "release_key_cmds -> release_key -> ")
            return True

        elif multi_operation[0] in cls.press_key_cmds:
            multi_operation = multi_operation[1:]
            if "key" in multi_operation:
                multi_operation.remove("key")
            if "keys" in multi_operation:
                multi_operation.remove("keys")
            PressingSpeaker(multi_operation, addr + "press_key_cmds -> PressingSpeaker ->")
            press_key(multi_operation, addr + "press_key_cmds -> press_key -> ")
            return True
        return False

    @classmethod
    def control_app_opening(cls, operation: str, addr: str) -> bool:
        multi_operation = operation.split()
        # print("multi_operation", multi_operation)
        if multi_operation[0] in cls.open_app_cmds and not cls._open_by_windows_search:
            try:
                app_name, app_address = WINDOWS_SystemController.DesktopSystemController.open_app_by_file_search(
                    multi_operation, addr + " open_app_cmds -> Search_by_windows -> OpenByWindowsSearch ->"
                )
                if app_name is not None:
                    val = open_application(app_name[:-4], app_address, addr + "open_app_cmds -> open_application -> ")
                    if val:
                        return True
                else:
                    val = "Search by windows"
                if val == "Search by windows":
                    WINDOWS_SystemController.DesktopSystemController.open_apps_by_windows_search(
                        multi_operation, addr + " open_app_cmds -> Search_by_windows -> OpenByWindowsSearch ->"
                    )
                    OpeningSpeaker(multi_operation, addr + "open_app_cmds -> Search_by_windows -> OpeningSpeaker -> ")
                    return True
                OpeningSpeaker(multi_operation, addr + "open_app_cmds -> OpeningSpeaker -> ")
                return True
            except Exception as e:
                print("Error = ", e, addr)
                return False
        elif multi_operation[0] in cls.open_app_cmds and cls._open_by_windows_search:
            cls.open_apps_by_windows_search(multi_operation,
                                            addr + "_open_by_windows_search -> OpenByWindowsSearch -> ")
            OpeningSpeaker(multi_operation, addr + "_open_by_windows_search -> OpeningSpeaker -> ")
            return True
        return False

    @classmethod
    def control_app_closing(cls, operation: str, addr: str) -> bool:
        multi_operation = operation.split()
        if multi_operation[0] in cls.close_app_cmds:
            try:
                val = close_application_by_name(" ".join(multi_operation[1:]),
                                                addr + "close_app_cmds -> close_application_by_name -> ")
                if val:
                    ClosingSpeaker(multi_operation, addr + "close_app_cmds -> close_application_by_name -> ")
                return val
            except Exception as e:
                print("Error = ", e, addr)
                return False
        return False

    @classmethod
    def control_opened_windows(cls, operation: str, addr: str) -> bool:
        # print('cls._lock_opened_windows', cls._lock_opened_windows)
        if cls._lock_opened_windows:
            SettingWindows(operation, addr + 'control_opened_windows -> ')
            if operation == 'close':
                cls._lock_opened_windows = False
                # print("cls._lock_opened_windows", cls._lock_opened_windows)
            Speaker(operation, addr + "control_opened_windows -> ")
            return True
        return False

    @staticmethod
    def open_apps_by_windows_search(operation: str, addr: str) -> bool:
        return WINDOWS.DesktopSystemController.open_apps_by_windows_search(
            operation, addr + "open_apps_by_windows_search -> "
        )

    @staticmethod
    def controlling_active_window(operation: str, addr: str) -> bool:
        return WINDOWS_SystemController.MainActivationWindows(operation, addr)

# represent the parameter type required has input
