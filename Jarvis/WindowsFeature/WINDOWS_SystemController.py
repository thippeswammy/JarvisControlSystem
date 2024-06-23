import os
import re
import wmi
import time
import pyautogui
import pandas as pd
import pygetwindow as gw
from comtypes import CLSCTX_ALL
from ctypes import cast, POINTER
from difflib import get_close_matches
from typing import List, Union, Optional
from Jarvis.KeyboardAutomationController import press_key
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume


def read_app_list_from_excel(file_path: str) -> tuple:
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    df = pd.read_excel(file_path)
    app_names = df.iloc[:, 0].tolist()  # Assuming the first column contains app names
    addresses = df.iloc[:, 1].tolist()  # Assuming the second column contains addresses
    return app_names, addresses


file_path = "F:/RunningProjects/JarvisControlSystem/Jarvis/Data/Data_Information_Value/AppNameList.xlsx"
app_names, app_addresses = read_app_list_from_excel(file_path)


class DesktopSystemController:
    DesktopSystemController_set_data = {
        "set brightness": ['set brightness level', 'set brightness to ', 'set brightness',
                           'change brightness in windows', 'brightness level', 'brightness to level',
                           'set brightness to level'],

        "incr_decre brightness": ['increase brightness', 'increase brightness level',
                                  'increase brightness in windows', 'increase brightness in windows',
                                  'decrease brightness', 'decrease brightness level',
                                  'decrease brightness in windows', 'decrease brightness in windows'],

        "set volume": ['set volume level', 'set volume to ', 'set volume', 'set volume',
                       'change volume in windows', 'adjust volume', 'reduce volume'],

        "incr_decre volume": ['increase volume', 'increase volume level', 'increase volume in windows',
                              'increase volume in windows', 'decrease volume', 'decrease volume level',
                              'decrease volume in windows', 'decrease volume in windows'],

        "shift windows right": ['shift windows right', 'shift tab right', 'shift frame right', 'shift right tab',
                                'move to right windows', 'move to right windows', 'move to right frame',
                                'move to next tab', 'next windows', 'move next tab', 'move to next windows',
                                'move next windows'],

        "shift windows left": ['shift windows left', 'shift tab left', 'shift frame left', 'shift left tab',
                               'move to left windows', 'move to left windows', 'move to left frame', 'move to past tab',
                               'move past tab', 'move to past windows', 'move past windows'],
    }

    Dict_word_replacements = {"light": "brightness",
                              "window": "windows",
                              "sound": "volume",
                              "reduce": "decrease",
                              "shifting": "shift",
                              "adjust": "change"}

    @staticmethod
    def find_best_app_matches(term: str, app_names: List[str], addresses: List[str], n: int = 1) -> tuple:
        matches = get_close_matches(term, app_names, n=n, cutoff=0.6)
        match_addresses = [addresses[app_names.index(match)] for match in matches]
        return matches, match_addresses

    @staticmethod
    def replace_words_in_sentence(sentence: str) -> str:
        words = sentence.split()
        new_sentence = ' '.join(DesktopSystemController.Dict_word_replacements.get(word, word) for word in words)
        return new_sentence

    @staticmethod
    def extract_numbers_from_text(text: str) -> List[int]:
        numbers = re.findall(r'\d+', text)
        return [int(number) for number in numbers]

    @staticmethod
    def search_windows_for_term(search: List[str], addr: str) -> bool:
        pyautogui.press("win")
        time.sleep(0.5)
        pyautogui.typewrite(" ".join(search[1:]))
        return True

    @staticmethod
    def open_apps_by_windows_search(search: List[str], addr: str) -> bool:
        DesktopSystemController.search_windows_for_term(search, addr + "SearchByWindows -> ")
        time.sleep(0.1)
        press_key("enter", addr + "press_key -> ")
        return True

    @staticmethod
    def open_app_by_file_search(search: List[str], addr: str) -> Union[None, tuple]:
        print("=" * 50, "open_app_by_file_search => ", search, "=" * 50)
        search_term = " ".join(search[1:])
        best_matches, match_addresses = (
            DesktopSystemController.find_best_app_matches(search_term, app_names, app_addresses))
        print(f"Best matches for '{search_term}':")
        for match, address in zip(best_matches, match_addresses):
            print(f"App Name: {match}, Address: {address}")
            return match, address
        return None, None

    @staticmethod
    def set_system_volume_level(new_volume: int) -> bool:
        new_volume = min(100, max(0, new_volume))
        new_volume = new_volume / 100
        devices = AudioUtilities.GetSpeakers()
        # noinspection PyProtectedMember
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        volume.SetMasterVolumeLevelScalar(new_volume, None)
        return True

    @staticmethod
    def get_system_volume_level() -> int:
        devices = AudioUtilities.GetSpeakers()
        # noinspection PyProtectedMember
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        return int(volume.GetMasterVolumeLevelScalar() * 100)

    @staticmethod
    def set_screen_brightness_level(brightness_level: int) -> bool:
        brightness_level = min(100, max(0, brightness_level))  # Ensure brightness is between 0 and 100
        c = wmi.WMI(namespace='wmi')
        methods = c.WmiMonitorBrightnessMethods()[0]
        methods.WmiSetBrightness(brightness_level, 0)
        return True

    @staticmethod
    def get_screen_brightness_level() -> int:
        try:
            w = wmi.WMI(namespace='wmi')
            brightness = w.WmiMonitorBrightness()[0].CurrentBrightness
        except Exception as e:
            print(f"Error: {e}")
            return False
        return brightness

    @staticmethod
    def perform_background_activation(operation: str = '', addr: str = '') -> bool:
        operation = DesktopSystemController.replace_words_in_sentence(operation)
        for i in DesktopSystemController.DesktopSystemController_set_data["set brightness"]:
            if i in operation:
                val = DesktopSystemController.extract_numbers_from_text(operation)
                if len(val) == 0:
                    return DesktopSystemController.set_screen_brightness_level(
                        DesktopSystemController.get_screen_brightness_level() + 10)
                else:
                    return DesktopSystemController.set_screen_brightness_level(val[0])
        for i in DesktopSystemController.DesktopSystemController_set_data["incr_decre brightness"]:
            if i in operation:
                val = DesktopSystemController.extract_numbers_from_text(operation)
                if len(val) > 0:
                    if "increase" in operation:
                        return DesktopSystemController.set_screen_brightness_level(
                            DesktopSystemController.get_screen_brightness_level() + val[0])

                    elif "decrease" in operation:
                        return DesktopSystemController.set_screen_brightness_level(
                            DesktopSystemController.get_screen_brightness_level() - val[0])

                else:
                    val = 10
                    if "increase" in operation:
                        return DesktopSystemController.set_screen_brightness_level(
                            DesktopSystemController.get_screen_brightness_level() + val)

                    elif "decrease" in operation:
                        return DesktopSystemController.set_screen_brightness_level(
                            DesktopSystemController.get_screen_brightness_level() - val)

        for i in DesktopSystemController.DesktopSystemController_set_data["set volume"]:
            if i in operation:
                val = DesktopSystemController.extract_numbers_from_text(operation)
                if len(val) == 0:
                    return DesktopSystemController.set_system_volume_level(
                        DesktopSystemController.get_system_volume_level() + 10)
                else:
                    return DesktopSystemController.set_system_volume_level(val[0])
        for i in DesktopSystemController.DesktopSystemController_set_data["incr_decre volume"]:
            if i in operation:
                val = DesktopSystemController.extract_numbers_from_text(operation)
                if len(val) > 0:
                    if "increase" in operation:
                        return DesktopSystemController.set_system_volume_level(
                            DesktopSystemController.get_system_volume_level() + val[0])

                    elif "decrease" in operation:
                        return DesktopSystemController.set_system_volume_level(
                            DesktopSystemController.get_system_volume_level() - val[0])

                else:
                    val = 10
                    if "increase" in operation:
                        return DesktopSystemController.set_system_volume_level(
                            DesktopSystemController.get_system_volume_level() + val)

                    elif "decrease" in operation:
                        return DesktopSystemController.set_system_volume_level(
                            DesktopSystemController.get_system_volume_level() - val)

                break

        # for ope in DesktopSystemController.DesktopSystemController_set_data["shift windows right"]:
        #     if ope in operation:
        #         return WindowsFrame.SwitchingFocusToNextActiveWindow("")

        return False


class WindowsAppController:
    WindowsAppController_set_data = {
        'minimize_wind': ['minimize windows', 'minimize window', 'minimize active windows', 'minimize active window',
                          'minimize opened windows', 'minimize opened window', 'minimise windows', 'minimise window',
                          'minimise active windows', 'minimise active window',
                          'minimise opened windows', 'minimise opened window', ],
        'minimize_all_wind': ['minimize all windows', 'minimize all window', 'minimise all windows',
                              'minimise all window'],
        'maximize_wind': ['maximize windows', 'maximize window', 'maximize active windows', 'maximize active window',
                          'maximize opened windows', 'maximize opened window', 'maximise windows', 'maximise window',
                          'maximise active windows', 'maximise active window',
                          'maximise opened windows', 'maximise opened window', 'full windows', 'full window',
                          'full screen', 'full screen windows', 'full screen window'],
        'maximize_all_wind': ['maximize all windows', 'maximize all window', 'maximise all windows',
                              'maximise all window',
                              'all full screen windows', 'all full screen window'],
        'close_wind': ['close present windows', 'close present window', 'close active windows', 'close active window',
                       'close opened windows', 'close opened window'],
        'close_all_wind': ['close all windows', 'close all window'],
        'shift_windows': ['shift windows', 'shift window', 'next window', 'next windows', 'goto next window',
                          'goto next windows', 'to next window', 'to next windows'],
        'move_wind_left': ['move windows left', 'move window left', 'move windows to left', 'move window to left'],
        'move_wind_right': ['move windows right', 'move window right', 'move windows to right', 'move window to right']
    }

    @staticmethod
    def get_active_window() -> Optional[gw.Window]:
        active_window = gw.getActiveWindow()
        if active_window:
            return active_window
        else:
            # print("No active window found.")
            return None

    @staticmethod
    def get_all_visible_windows() -> List[gw.Window]:
        windows = gw.getAllWindows()
        visible_windows = [win for win in windows if
                           (win.isActive or win.isMaximized or win.isMinimized) and win.title != '']
        return visible_windows[:-1]

    @staticmethod
    def minimize_window(window: Optional[gw.Window] = None) -> bool:
        if window is None:
            window = WindowsAppController.get_active_window()
        if window:
            try:
                window.minimize()
                return True
            except gw.PyGetWindowException as e:
                print(f"Could not minimize window {window}: {e}")
                return False
        return False

    @staticmethod
    def maximize_window(window: Optional[gw.Window] = None) -> bool:
        if window is None:
            window = WindowsAppController.get_active_window()
        if window:
            try:
                if window.left == -32000 and window.top == -32000:
                    window.restore()
                window.activate()
                if not window.isMaximized:
                    window.maximize()
                window.show()
                return True
            except gw.PyGetWindowException as e:
                print(f"Could not maximize window {window}: {e}")
                return False
        return False

    @staticmethod
    def close_window(window: Optional[gw.Window] = None) -> bool:
        time.sleep(5)
        if window is None:
            window = WindowsAppController.get_active_window()
        if window:
            try:
                window.close()
                return True
            except gw.PyGetWindowException as e:
                print(f"Could not close window {window}: {e}")
                return False
        return False

    @staticmethod
    def activate_window(window: Optional[gw.Window] = None) -> bool:
        if window is None:
            window = WindowsAppController.get_active_window()
        if window:
            try:
                window.show()
                window.activate()
                return True
            except gw.PyGetWindowException as e:
                print(f"Could not activate window {window}: {e}")
                return False
        return False

    @staticmethod
    def minimize_all_windows() -> bool:
        success = True
        visible_windows = WindowsAppController.get_all_visible_windows()
        for win in visible_windows:
            if not WindowsAppController.minimize_window(win):
                success = False
        return success

    @staticmethod
    def maximize_all_windows() -> bool:
        success = True
        visible_windows = WindowsAppController.get_all_visible_windows()
        for win in visible_windows:
            if not WindowsAppController.maximize_window(win):
                success = False
            if not WindowsAppController.activate_window(win):
                success = False
            # time.sleep(2)
        return success

    @staticmethod
    def close_all_windows() -> bool:
        success = True
        visible_windows = WindowsAppController.get_all_visible_windows()
        for win in visible_windows:
            if win.isMinimized or win.isMaximized or win.isActive:
                if not WindowsAppController.close_window(win):
                    success = False
        return success

    @staticmethod
    def move_window_to_left(window: Optional[gw.Window] = None) -> bool:
        if window is None:
            window = WindowsAppController.get_active_window()
        if window and window.isActive:
            pyautogui.hotkey("win", "left")
            return True
        return False

    @staticmethod
    def move_window_to_right(window: Optional[gw.Window] = None) -> bool:
        if window is None:
            window = WindowsAppController.get_active_window()
        if window and window.isActive:
            pyautogui.hotkey("win", "right")
            return True
        return False

    @staticmethod
    def switch_windows(frame_number: int = 1) -> bool:
        visible_windows = WindowsAppController.get_all_visible_windows()
        ActiveWindow = gw.getActiveWindow()
        visible_windows.remove(ActiveWindow)
        visible_windows.insert(0, ActiveWindow)
        if len(visible_windows) > 0:
            if frame_number >= 0:
                if frame_number < len(visible_windows):
                    target_window = visible_windows[frame_number]
                else:
                    # print(f"Frame number {frame_number} exceeds the number of visible windows.")
                    return False
            else:
                if -frame_number <= len(visible_windows):
                    frame_number = len(visible_windows) + frame_number
                    target_window = visible_windows[frame_number]
                else:
                    # print(f"Frame number {frame_number} exceeds the number of visible windows.")
                    return False

            try:
                # time.sleep(1)
                WindowsAppController.maximize_window(target_window)
                for i, win in enumerate(visible_windows):
                    if i != frame_number:
                        WindowsAppController.minimize_window(win)
                return True
            except gw.PyGetWindowException as e:
                print(f"An error occurred while handling window {target_window}: {e}")
                return False
        else:
            # print("No visible windows to switch to.")
            pass
        return False

    @staticmethod
    def move_window_to_left_and_click(window: Optional[gw.Window] = None) -> bool:
        if window is None:
            window = WindowsAppController.get_active_window()
        if window and window.isActive:
            pyautogui.hotkey("win", "left")
            time.sleep(0.5)
            window_x, window_y, window_width, window_height = window.left, window.top, window.width, window.height
            mox, moy = pyautogui.position()
            click_x = window_x + window_width - 200  # Click towards the left side
            click_y = window_y + 20  # Click on an empty space near the top
            pyautogui.click(click_x, click_y, duration=0)  # Adjust click duration as needed
            time.sleep(0.1)
            pyautogui.click(mox, moy, duration=0)  # Adjust click duration as needed
            return True
        return False

    @staticmethod
    def move_window_to_right_and_click(window: Optional[gw.Window] = None) -> bool:
        if window is None:
            window = WindowsAppController.get_active_window()
        if window and window.isActive:
            pyautogui.hotkey("win", "right")
            time.sleep(0.5)
            window_x, window_y, window_width, window_height = window.left, window.top, window.width, window.height
            mox, moy = pyautogui.position()
            click_x = window_x + window_width - 200  # Click towards the left side
            click_y = window_y + 20  # Click on an empty space near the top
            pyautogui.click(click_x, click_y, duration=0)  # Adjust click duration as needed
            time.sleep(0.1)
            pyautogui.click(mox, moy, duration=0)  # Adjust click duration as needed
            return True
        return False

    @staticmethod
    def switch_focus_to_next_active_window() -> bool:
        return WindowsAppController.switch_windows(1)

    @staticmethod
    def display_visible_windows() -> List[gw.Window]:
        ActiveWindow = gw.getActiveWindow()
        visible_windows = WindowsAppController.get_all_visible_windows()
        visible_windows.remove(ActiveWindow)
        visible_windows.insert(0, ActiveWindow)
        for win in visible_windows:
            try:
                # Restore window if it is minimized
                if win.isMinimized:
                    win.restore()
                    # time.sleep(1)
                # Maximize window if it's not maximized
                if not win.isMaximized:
                    win.maximize()
                    # time.sleep(1)
                # Activate window if it's not active
                if not win.isActive:
                    win.activate()
                    # time.sleep(1)
            except gw.PyGetWindowException as e:
                if "Access is denied" in str(e):
                    print(f"Skipping window {win} due to access denial.")
                else:
                    print(f"An error occurred while handling window {win}: {e}")
                return False
        return visible_windows

    @staticmethod
    def perform_background_activation(operation: str = '', addr: str = '') -> bool:
        for minimize_wind in WindowsAppController.WindowsAppController_set_data['minimize_wind']:
            if operation in minimize_wind:
                return WindowsAppController.minimize_window()
        for maximize_wind in WindowsAppController.WindowsAppController_set_data['maximize_wind']:
            if operation in maximize_wind:
                return WindowsAppController.maximize_window()
        for minimize_all_wind in WindowsAppController.WindowsAppController_set_data['minimize_all_wind']:
            if operation in minimize_all_wind:
                return WindowsAppController.minimize_all_windows()
        for maximize_all_wind in WindowsAppController.WindowsAppController_set_data['maximize_all_wind']:
            if operation in maximize_all_wind:
                return WindowsAppController.maximize_all_windows()
        for close_wind in WindowsAppController.WindowsAppController_set_data['close_wind']:
            if operation in close_wind:
                return WindowsAppController.close_window()
        for close_all_wind in WindowsAppController.WindowsAppController_set_data['close_all_wind']:
            if operation in close_all_wind:
                return WindowsAppController.close_all_windows()
        for shift_windows in WindowsAppController.WindowsAppController_set_data['shift_windows']:
            if operation in shift_windows:
                return WindowsAppController.switch_windows()
        for move_wind_left in WindowsAppController.WindowsAppController_set_data['move_wind_left']:
            if operation in move_wind_left:
                return WindowsAppController.move_window_to_left()
        for move_wind_right in WindowsAppController.WindowsAppController_set_data['move_wind_right']:
            if operation in move_wind_right:
                return WindowsAppController.move_window_to_right()
        return False


def process_operation(operation):
    if not isinstance(operation, str):
        if len(operation) > 1:
            operation = " ".join(operation)
        else:
            operation = operation[0]
    return operation


def MainActivationWindows(operation: str = "", addr: str = "") -> bool:
    operation = process_operation(operation)
    if DesktopSystemController.perform_background_activation(operation.lower(), ""):
        return True
    elif WindowsAppController.perform_background_activation(operation.lower(), ""):
        return True
    return False


if __name__ == "__main__":
    # print(MainActivationWindows("set brightness 500", ''))
    # print(WindowsAppController.switch_windows(2))
    pass
