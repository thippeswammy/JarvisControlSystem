import time
import pyautogui
from typing import List, Optional

keyName = {
    "escape": "esc",
    "tab": "tab",

    "space": "space",
    "space bar": "space",
    "spacebar": "space",

    "up Arrow": "up",
    "up key": "up",
    "up ": "up",

    "down Arrow": "down",
    "down key": "down",
    "down": "down",

    "left Arrow": "left",
    "left key": "left",
    "left": "left",

    "right Arrow": "right",
    "right key": "right",
    "right": "right",

    "control key": "ctrl",
    "control": "ctrl",

    "alternate key": "alt",
    "alternate": "alt",
    "alt key": "alt",
    "alt": "alt",

    "shift key": "shift",
    "shift": "shift",

    "page up key": "pageup",
    "pageup": "pageup",

    "page down key": "pagedown",
    "page down": "pagedown",

    "backspace key": "backspace",
    "backspace": "backspace",
    "back space key": "backspace",
    "back space": "backspace",

    "delete key": "delete",
    "delete": "delete",

    "caps lock key": "capslock",
    "caps lock": "capslock",
    "capslock key": "capslock",
    "capslock": "capslock",

    "num lock key": "numlock",
    "num lock": "numlock",
    "numlock key": "numlock",
    "numlock": "numlock",

    "print screen key": "printscreen",
    "print screen": "printscreen",
    "printscreen key": "printscreen",
    "printscreen": "printscreen",

    "windows": "win",
    "cmd": "win",
    "window": "win",
    "windows key": "win",
    "cmd key": "win",
    "window key": "win"
}

valid_keys = [
    'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
    'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
    '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
    'enter', 'esc', 'shift', 'ctrl', 'alt', 'tab', 'space', 'backspace',
    'delete', 'up', 'down', 'left', 'right', 'home', 'end', 'pageup', 'pagedown',
    'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12',
    'capslock', 'numlock', 'scrolllock', 'pause', 'printscreen', 'insert', 'win',
    'cmd', 'option', 'command', 'menu', 'volumeup', 'volumedown', 'volumemute',
    'mediaplaypause', 'mediastop', 'mediaprevtrack', 'medianexttrack'
]


def ConvertingKeyValues_Key(Multi_operation: List[str], addr: str) -> List[str]:
    for i in range(len(Multi_operation)):
        value = keyName.get(Multi_operation[i])
        if value is not None:
            Multi_operation[i] = value
    return Multi_operation


def type_text(operation: str, addr: str) -> None:
    if operation:
        pyautogui.typewrite(operation)
        # print("pressed key = ", operation, addr + "COMPLETED")
    return True


def press_key(Multi_operation: List[str], addr: str) -> None:
    # print("press key = ", Multi_operation)
    pyautogui.hotkey(ConvertingKeyValues_Key(Multi_operation,
                                             addr + "ConvertingKeyValues_Key -> "))
    # print("pressed key = ", Multi_operation, addr + "COMPLETED")
    return True


def hold_key(Multi_operation: List[str], addr: str) -> None:
    pyautogui.hold(
        ConvertingKeyValues_Key(Multi_operation, addr + "ConvertingKeyValues_Key -> "))
    # print("holding key = ", Multi_operation, addr + "COMPLETED")
    return True


def down_key(Multi_operation: List[str], addr: str) -> None:
    for i in ConvertingKeyValues_Key(Multi_operation,
                                     addr + "ConvertingKeyValues_Key -> ")[:]:
        pyautogui.keyDown(i)
    # print("down key = ", Multi_operation, addr + "COMPLETED")
    return True


def up_key(Multi_operation: List[str], addr: str) -> None:
    for i in ConvertingKeyValues_Key(Multi_operation,
                                     addr + "ConvertingKeyValues_Key -> ")[-1::-1]:
        pyautogui.keyUp(i)
    # print("up key = ", Multi_operation, addr + "COMPLETED")
    return True


def release_key(Multi_operation: List[str], addr: str) -> None:
    for i in ConvertingKeyValues_Key(Multi_operation,
                                     addr + "ConvertingKeyValues_Key -> ")[-1::-1]:
        pyautogui.keyUp(i)
    # print("releasing key = ", Multi_operation, addr + "COMPLETED")
    return True


def press_multi_key(Multi_operation: List[str], addr: str) -> None:
    val = ConvertingKeyValues_Key(Multi_operation,
                                  addr + "ConvertingKeyValues_Key -> ")
    pyautogui.hotkey(val)
    # print("press_multi_key = ", Multi_operation, addr + "COMPLETED")
    return True

