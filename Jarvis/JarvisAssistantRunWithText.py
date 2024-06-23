import threading
import CommandProcessor
from Jarvis import RecentAppPerformanceMonitor
from CameraFeatures import handSectionMovement
from WindowsDefaultApps import settingControlApp
from WindowsFeature import WINDOWS_SystemController
from Data import JSON_Information_Center, XLSX_Information_Center


def monitor_recent_apps():
    while True:
        try:
            RecentAppPerformanceMonitor.RecentAppPerformanceMonitorFun()
        except Exception as e:
            pass


def monitor_camera():
    try:
        handSectionMovement.cameraControl()
    except Exception as e:
        pass


def speech_input():
    # passing_user_input("close present windows", "|| -->>>")
    while True:
        text = input("Enter =>")
        if text in ['exit', '0']:
            exit()
        passing_user_input(text, "| -->>>")


def passing_user_input(operation, address):
    address = address + "Main -> "
    success = CommandProcessor.UserCommandProcessor.main_activation(operation, address + "Activation -> ")
    if success:
        print("Success")
    else:
        print("Fail")


if __name__ == "__main__":
    # thread1 = threading.Thread(target=monitor_recent_apps)
    # thread1.start()
    # thread2 = threading.Thread(target=monitor_camera)
    # thread2.start()
    speech_input()
