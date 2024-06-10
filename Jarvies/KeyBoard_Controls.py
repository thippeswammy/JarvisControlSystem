import time

import pyautogui

_delay = 0
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


def ConvertingKeyValues_Key(Multi_operation, addr):
    time.sleep(_delay)
    for i in range(0, len(Multi_operation)):
        value = keyName.get(Multi_operation[i])
        if value is not None:
            Multi_operation[i] = value
    return Multi_operation


def type_text(operation, addr):
    time.sleep(_delay)
    if operation:
        pyautogui.typewrite(operation)
        print("pressed key = ", operation, addr + "COMPLETED")


def press_key(Multi_operation, addr):
    print("press key = ", Multi_operation)
    pyautogui.hotkey(ConvertingKeyValues_Key(Multi_operation, addr + "ConvertingKeyValues_Key -> "))
    print("pressed key = ", Multi_operation, addr + "COMPLETED")


def hold_key(Multi_operation, addr):
    pyautogui.hold(ConvertingKeyValues_Key(Multi_operation, addr + "ConvertingKeyValues_Key -> "))
    print("holding key = ", Multi_operation, addr + "COMPLETED")


def down_key(Multi_operation, addr):
    for i in ConvertingKeyValues_Key(Multi_operation, addr + "ConvertingKeyValues_Key -> ")[:]:
        pyautogui.keyDown(i)
    print("down key = ", Multi_operation, addr + "COMPLETED")


def up_key(Multi_operation, addr):
    for i in ConvertingKeyValues_Key(Multi_operation, addr + "ConvertingKeyValues_Key -> ")[-1::-1]:
        pyautogui.keyUp(i)
    print("up key = ", Multi_operation, addr + "COMPLETED")


def release_key(Multi_operation, addr):
    for i in ConvertingKeyValues_Key(Multi_operation, addr + "ConvertingKeyValues_Key -> ")[-1::-1]:
        pyautogui.keyUp(i)
    print("releasing key = ", Multi_operation, addr + "COMPLETED")


def press_multi_key(Multi_operation, addr):
    val = ConvertingKeyValues_Key(Multi_operation, addr + "ConvertingKeyValues_Key -> ")
    pyautogui.hotkey(val)
    print("press_multi_key = ", Multi_operation, addr + "COMPLETED")


# pyautogui.hotkey(["win", "i"])


# press_multi_key(["windows", "left"], "")
# pyautogui.hotkey('win', 'up')

'''  

def Action_for_presskey(jarvisTextRes):
    Startingposition: int = 0
    Endinggposition: int = len(jarvisTextRes)
    if jarvisTextRes[0] + " " + jarvisTextRes[1] == "press key":
        IsPresskey = True
        Startingposition = 2
        Endinggposition = len(jarvisTextRes)
    elif jarvisTextRes[0] + " " + jarvisTextRes[1] == "press keys":
        IsPresskey = True
        Startingposition = 2
        Endinggposition = len(jarvisTextRes)
    elif jarvisTextRes[0] == "press":
        IsPresskey = True
        Startingposition = 1
        Endinggposition = len(jarvisTextRes)
    elif jarvisTextRes[0] + " " + jarvisTextRes[len(jarvisTextRes) - 1] == "press key":
        IsPresskey = True
        Startingposition = 1
        Endinggposition = len(jarvisTextRes) - 1
    elif jarvisTextRes[0] + " " + jarvisTextRes[len(jarvisTextRes) - 1] == "press keys":
        IsPresskey = True
        Startingposition = 1
        Endinggposition = len(jarvisTextRes) - 1
    if IsPresskey:
        for i in range(Startingposition, Endinggposition):
            if jarvisTextRes[i] == "control":
                keyboard.press(Key.ctrl)
            elif jarvisTextRes[i] == "window":
                keyboard.press(Key.cmd)
            elif jarvisTextRes[i] == "windows":
                keyboard.press(Key.cmd)
            elif jarvisTextRes[i] == "cmd":
                keyboard.press(Key.cmd)
            elif jarvisTextRes[i] == "alt":
                keyboard.press(Key.alt)
            elif jarvisTextRes[i] == "space":
                keyboard.press(Key.space)
            elif jarvisTextRes[i] == "shift":
                keyboard.press(Key.shfit)
            elif jarvisTextRes[i] == "enter":
                keyboard.press(Key.enter)
            elif jarvisTextRes[i] == "backspace":
                keyboard.press(Key.backspace)
            elif jarvisTextRes[i] == "tab":
                keyboard.press(Key.tab)
            elif jarvisTextRes[i] == "caps lock":
                keyboard.press(Key.caps_lock)
            elif jarvisTextRes[i] == "up":
                keyboard.press(Key.up)
            elif jarvisTextRes[i] == "right":
                keyboard.press(Key.right)
            elif jarvisTextRes[i] == "down":
                keyboard.press(Key.down)
            elif jarvisTextRes[i] == "left":
                keyboard.press(Key.left)
            elif jarvisTextRes[i] == "else":
                keyboard.press(Key.esc)
            elif jarvisTextRes[i] == "insert":
                keyboard.press(Key.insert)
            elif jarvisTextRes[i] == "play next":
                keyboard.press(Key.media_next)
            elif jarvisTextRes[i] == "pause ":
                keyboard.press(Key.media_play_pause)
            elif jarvisTextRes[i] == "play stop":
                keyboard.press(Key.media_play_pause)
            elif jarvisTextRes[i] == "previous":
                keyboard.press(Key.media_previous)
            elif jarvisTextRes[i] == "play back":
                keyboard.press(Key.media_previous)
            elif jarvisTextRes[i] == "volume down":
                keyboard.press(Key.media_volume_down)
            elif jarvisTextRes[i] == "volume mute":
                keyboard.press(Key.media_volume_mute)
            elif jarvisTextRes[i] == "volume up":
                keyboard.press(Key.media_volume_up)
            elif jarvisTextRes[i] == "num lock":
                keyboard.press(Key.num_lock)
            elif jarvisTextRes[i] == "page down":
                keyboard.press(Key.page_down)
            elif jarvisTextRes[i] == "page up":
                keyboard.press(Key.page_up)
            elif jarvisTextRes[i] == "pause":
                keyboard.press(Key.pause)
            elif jarvisTextRes[i] == "print screen":
                keyboard.press(Key.print_screen)
            elif jarvisTextRes[i] == "scroll lock":
                keyboard.press(Key.scroll_lock)
            elif len(jarvisTextRes[i]) == 1:
                keyboard.press(jarvisTextRes[i])
        for i in range((Endinggposition - 1), Startingposition - 1, -1):
            if jarvisTextRes[i] == "control":
                keyboard.release(Key.ctrl)
            elif jarvisTextRes[i] == "window":
                keyboard.release(Key.cmd)
            elif jarvisTextRes[i] == "windows":
                keyboard.release(Key.cmd)
            elif jarvisTextRes[i] == "cmd":
                keyboard.release(Key.cmd)
            elif jarvisTextRes[i] == "alt":
                keyboard.release(Key.alt)
            elif jarvisTextRes[i] == "space":
                keyboard.release(Key.space)
            elif jarvisTextRes[i] == "shift":
                keyboard.release(Key.shfit)
            elif jarvisTextRes[i] == "enter":
                keyboard.release(Key.enter)
            elif jarvisTextRes[i] == "backspace":
                keyboard.release(Key.backspace)
            elif jarvisTextRes[i] == "tab":
                keyboard.release(Key.tab)
            elif jarvisTextRes[i] == "caps lock":
                keyboard.release(Key.caps_lock)
            elif jarvisTextRes[i] == "up":
                keyboard.release(Key.up)
            elif jarvisTextRes[i] == "right":
                keyboard.release(Key.right)
            elif jarvisTextRes[i] == "down":
                keyboard.release(Key.down)
            elif jarvisTextRes[i] == "left":
                keyboard.release(Key.left)
            elif jarvisTextRes[i] == "else":
                keyboard.release(Key.esc)
            elif jarvisTextRes[i] == "insert":
                keyboard.release(Key.insert)
            elif jarvisTextRes[i] == "play next":
                keyboard.release(Key.media_next)
            elif jarvisTextRes[i] == "pause":
                keyboard.release(Key.media_play_pause)
            elif jarvisTextRes[i] == "play":
                keyboard.release(Key.media_play_pause)
            elif jarvisTextRes[i] == "play stop":
                keyboard.release(Key.media_play_pause)
            elif jarvisTextRes[i] == "previous":
                keyboard.release(Key.media_previous)
            elif jarvisTextRes[i] == "play back":
                keyboard.release(Key.media_previous)
            elif jarvisTextRes[i] == "volume down":
                keyboard.release(Key.media_volume_down)
            elif jarvisTextRes[i] == "volume mute":
                keyboard.release(Key.media_volume_mute)
            elif jarvisTextRes[i] == "volume up":
                keyboard.release(Key.media_volume_up)
            elif jarvisTextRes[i] == "num lock":
                keyboard.release(Key.num_lock)
            elif jarvisTextRes[i] == "page down":
                keyboard.release(Key.page_down)
            elif jarvisTextRes[i] == "page up":
                keyboard.release(Key.page_up)
            elif jarvisTextRes[i] == "pause":
                keyboard.release(Key.pause)
            elif jarvisTextRes[i] == "print screen":
                keyboard.release(Key.print_screen)
            elif jarvisTextRes[i] == "scroll lock":
                keyboard.release(Key.scroll_lock)
            elif len(jarvisTextRes[i]) == 1:
                keyboard.release(jarvisTextRes[i])
 
'''
