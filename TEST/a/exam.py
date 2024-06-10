import pyautogui


def open(text):
    pyautogui.press("win")
    pyautogui.typewrite(text)
    pyautogui.press("enter")


while True:
    inp = input("Enter = ")
    if inp == "00":
        break
    else:
        open(inp)
