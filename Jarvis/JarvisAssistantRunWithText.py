import socket
import threading
import CommandProcessor
from Jarvis import RecentAppPerformanceMonitor
from WindowsDefaultApps import settingControlApp
from WindowsFeature import WINDOWS_SystemController
from Data import JSON_Information_Center, XLSX_Information_Center
from CameraFeatures import handSectionMovement


def inputFromOtherDevices():
    HOST = '0.0.0.0'
    PORT = 12345  # Choose any free port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((HOST, PORT))
        server_socket.listen()
        print(f'Server listening on {HOST} : {PORT}...')
        conn, addr = server_socket.accept()
        with conn:
            print(f'Connected by {addr}')
            while True:
                data = conn.recv(1024)
                if data == 'exit()':
                    break
                print("input =", data.decode())
                thread = threading.Thread(target=passing_user_input(data.decode(), "socket -> "))
                thread.start()


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


def Text_input():
    # passing_user_input("close present windows", "|| -->>>")
    while True:
        text = input("Enter =>")
        passing_user_input(text, "| -->>>")


def passing_user_input(operation, address):
    if operation in ['exit', '0']:
        exit()
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
    # Text_input()
    inputFromOtherDevices()
