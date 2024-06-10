import threading

from Jarvies import RecentAppPerformanceMonitor, Main


# Define your functions
def RecentAppPerformanceMonitorFun():
    while True:
        RecentAppPerformanceMonitor.RecentAppPerformanceMonitorFun()
        # print("Running RecentAppPerformanceMonitorFun")
        # Place the logic of RecentAppPerformanceMonitorFun here
        # time.sleep(1)  # Adjust the delay as needed


def RUN_METHOD():
    while True:
        Main.Manual_Control_main()
        # Main.Manual_Control("open notepad", 3, "|| -->>> mainTest -> ")
        # print("Running RUN_METHOD")
        # Place the logic of RUN_METHOD here
        # time.sleep(1)  # Adjust the delay as needed


if __name__ == "__main__":
    # Create threads for each function
    thread1 = threading.Thread(target=RecentAppPerformanceMonitorFun())
    # thread2 = threading.Thread(target=RUN_METHOD)
    # Start both threads
    thread1.start()
    # thread2.start()
    # Wait for both threads to complete (this won't happen in this example as the threads run indefinitely)
    # thread2.join()
    RUN_METHOD()
