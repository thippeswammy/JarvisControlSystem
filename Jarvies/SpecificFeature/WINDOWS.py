import re
import time
from ctypes import cast, POINTER
import os
import pyautogui
import wmi
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

from Jarvies.KeyBoard_Controls import press_key
from Jarvies.SpecificFeature import WindowsFrame

import pandas as pd
from difflib import get_close_matches

windows_Set = {
    "set brightness": ['set brightness level', 'set brightness to ', 'set brightness',
                       'change brightness in windows', 'brightness level', 'brightness to level',
                       'set brightness to level'],

    "incr_decre brightness": ['increase brightness', 'increase brightness level',
                              'increase brightness in windows', 'increase brightness in windows',
                              'decrease brightness', 'decrease brightness level',
                              'decrease brightness in windows', 'decrease brightness in windows', ],

    "set volume": ['set volume level', 'set volume to ', 'set volume', 'set volume',
                   'change volume in windows', 'adjust volume', 'reduce volume'],

    "incr_decre volume": ['increase volume', 'increase volume level', 'increase volume in windows',
                          'increase volume in windows', 'decrease volume', 'decrease volume level',
                          'decrease volume in windows', 'decrease volume in windows', ],

    "shift windows right": ['shift windows right', 'shift tab right', 'shift frame right', 'shift right tab',
                            'move to right windows', 'move to right windows', 'move to right frame', 'move to next tab',
                            'move next tab', 'move to next windows', 'move next windows'],

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


# Function to read the Excel file and extract app names and addresses
def read_excel(file_path):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    df = pd.read_excel(file_path)
    app_names = df.iloc[:, 0].tolist()  # Assuming the first column contains app names
    addresses = df.iloc[:, 1].tolist()  # Assuming the second column contains addresses
    return app_names, addresses


# Path to the .xlsx file
file_path = 'F:\RunningProjects\JarvisControlSystem\Jarvies\AppNameList.xlsx'  # Update this with your actual file path

app_names, addresses = read_excel(file_path)


def find_best_matches(term, app_names, addresses, n=1):
    matches = get_close_matches(term, app_names, n=n, cutoff=0.5)
    match_addresses = [addresses[app_names.index(match)] for match in matches]
    return matches, match_addresses


def replace_words(sentence, replacements):
    words = sentence.split()
    new_sentence = ' '.join(replacements.get(word, word) for word in words)
    return new_sentence


def extract_numbers(text):
    numbers = re.findall(r'\d+', text)
    return [int(number) for number in numbers]


def windows_search(search, addr):
    pyautogui.press("win")
    time.sleep(0.5)
    pyautogui.typewrite(" ".join(search[1:]))
    # print(search)
    # return addr
    # print(" ".join(search[1:]),addr+"SearchByWindows -> ")


# windows_search(["search","name"],"")
def OpenByWindows_search(search, addr):
    windows_search(search, addr + "SearchByWindows -> ")
    time.sleep(0.1)
    press_key("enter", addr + "press_key -> ")
    # PressingSpeaker(search, addr + "PressingSpeaker -> ")
    print(" ".join(search[1:]), addr + "COMPLETED")


def SearchByWindowsFiles(search, addr):
    # search_term = "Google"
    print(search, "=" * 50)
    search_term = " ".join(search[1:])
    best_matches, match_addresses = find_best_matches(search_term, app_names, addresses)
    print(f"Best matches for '{search_term}':")
    for match, address in zip(best_matches, match_addresses):
        print(f"App Name: {match}, Address: {address}")
        return match, address
    return None, None


def set_volume(new_volume):
    new_volume = min(100, max(0, new_volume))
    new_volume = new_volume / 100
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = cast(interface, POINTER(IAudioEndpointVolume))
    volume.SetMasterVolumeLevelScalar(new_volume, None)


def get_volume():
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = cast(interface, POINTER(IAudioEndpointVolume))
    return int(volume.GetMasterVolumeLevelScalar() * 100)


def set_brightness(brightness_level):
    brightness_level = min(100, max(0, brightness_level))  # Ensure brightness is between 0 and 100

    c = wmi.WMI(namespace='wmi')
    methods = c.WmiMonitorBrightnessMethods()[0]

    # Set the brightness level (between 0 and 100)
    methods.WmiSetBrightness(brightness_level, 0)


def get_brightness_level():
    brightness = 0
    try:
        w = wmi.WMI(namespace='wmi')
        brightness = w.WmiMonitorBrightness()[0].CurrentBrightness
    except Exception as e:
        print(f"Error: {e}")
    return brightness


# Example: Set volume to 50% (0 - 100)%
# set_volume(88)

# Example: Set brightness to 50 (adjust as needed) (1-100)%
# set_brightness(88)

# Example: get the volume level to (1 -100)%
# print(f"Current Volume: {get_volume()}")

# Example: get the Brightness level to (1 -100)%
# print(f"Current Brightness Level: {get_brightness_level()}")


def Control_Windows(operation, addr):
    operation_save = operation
    operation = replace_words(operation, Dict_word_replacements)

    for i in windows_Set["set brightness"]:
        if i in operation:
            val = extract_numbers(operation)
            if len(val) == 0:
                set_brightness(get_brightness_level() + 10)
            else:
                set_brightness(val[0])
            break
    for i in windows_Set["incr_decre brightness"]:
        if i in operation:
            val = extract_numbers(operation)
            if len(val) > 0:
                if "increase" in operation:
                    set_brightness(get_brightness_level() + val[0])
                elif "decrease" in operation:
                    set_brightness(get_brightness_level() - val[0])
            else:
                val = 10
                if "increase" in operation:
                    set_brightness(get_brightness_level() + val)
                elif "decrease" in operation:
                    set_brightness(get_brightness_level() - val)
            break
    for i in windows_Set["set volume"]:
        if i in operation:
            val = extract_numbers(operation)
            if len(val) == 0:
                set_volume(get_volume() + 10)
            else:
                set_volume(val[0])
            break
    for i in windows_Set["incr_decre volume"]:
        if i in operation:
            val = extract_numbers(operation)
            if len(val) > 0:
                if "increase" in operation:
                    set_volume(get_volume() + val[0])
                elif "decrease" in operation:
                    set_volume(get_volume() - val[0])
            else:
                val = 10
                if "increase" in operation:
                    set_volume(get_volume() + val)
                elif "decrease" in operation:
                    set_volume(get_volume() - val)
            break

    if i in windows_Set["shift windows right"]:
        if i in operation:
            WindowsFrame.SwitchingFocusToNextActiveWindow("")
            breakpoint()

# for adding to number

# Control_Windows("increase volume to 2","")
# Control_Windows("set brightness to 100","")
