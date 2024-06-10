import threading
import CommandProcessor
from win10toast import ToastNotifier
from Jarvis import RecentAppPerformanceMonitor
import Jarvis.SpeechRecognition as Speech_Recognition

is_jarvis_called = False
is_typing_activated = True
open_by_windows = True
delay_time = 3


def Notifications(title="", mes=""):
    try:
        toast = ToastNotifier()
        toast.show_toast(
            title,
            mes,
            duration=2,
            # icon_path = "icon.ico",
            threaded=True,
        )
    except:
        pass


def monitor_recent_apps():
    while True:
        RecentAppPerformanceMonitor.RecentAppPerformanceMonitorFun()


def speech_input():
    while True:
        text = Speech_Recognition.listen_speech()
        print("speech input=", text)
        # Notifications("speech input:", text)
        # thread1 = threading.Thread(target=monitor_recent_apps)
        # thread1.start()
        if text != "":
            passing_user_input(text, 0, "|| -->>>")


def passing_user_input(operation, delay, address):
    global delay_time
    address = address + "Main -> "
    success = CommandProcessor.UserCommandProcessor.main_activation(operation, address + "Activation -> ")
    if success:
        print("success")
    else:
        print("fail")
    delay_time = delay


if __name__ == "__main__":
    # thread1 = threading.Thread(target=monitor_recent_apps)
    # thread1.start()
    speech_input()
    # Notifications()
