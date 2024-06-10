import Jarvies.ActivationFunction as ActivationFunction
import Jarvies.Speech_Recognition as Speech_Recognition

_IsJarvisCalled = False
_IsTypingActivated = True
_openByWindows = True
_delay = 3


def Manual_Control_main():
    while True:
        text = Speech_Recognition.listen_speech()
        # text = correct_spelling(text)
        print("SSSPPPP")
        Manual_Control(text, 0, "|| -->>>")


def Manual_Control(operation, dela, addr):
    addr = addr + "Main -> "
    ActivationFunction.MainActivation(operation, addr + "MainActivation -> ")
    _delay = dela


if __name__ == "__main__":
    Manual_Control_main()
