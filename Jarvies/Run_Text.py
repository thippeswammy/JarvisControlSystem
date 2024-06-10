import threading

import Jarvies.RecentAppPerformanceMonitor as RecentAppPerformanceMonitor
import Jarvies.mainTest as mainTest


# cd Jarvis
# pyinstaller Run_Text.py --onefile
# Define your functions
def RecentAppPerformanceMonitorFun():
    while True:
        RecentAppPerformanceMonitor.RecentAppPerformanceMonitorFun()


def RUN_METHOD():
    while True:
        mainTest.RUN_METHOD()


if __name__ == "__main__":
    thread1 = threading.Thread(target=RecentAppPerformanceMonitorFun)
    thread1.start()
    RUN_METHOD()
