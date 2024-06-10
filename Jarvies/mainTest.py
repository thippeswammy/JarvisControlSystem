import threading

import Jarvies.Main as Main


def RUN_METHOD():
    inp = input("\nYOU : ")
    if inp == "99":
        exit()
    else:
        # inp = correct_spelling(inp)
        # Main.Manual_Control(inp, 3, "|| -->>> mainTest-> ")
        thread = threading.Thread(target=Main.Manual_Control(inp, 3, "|| -->>> mainTest -> "))
        thread.start()
        # Main.Manual_Control(inp, 3, "|| -->>> mainTest-> ")


# if __name__ == "__main__":
#     # thread2 = threading.Thread(target=RecentAppPerformanceMonitorFun())
#     process1 = Process(target=RecentAppPerformanceMonitorFun())
#     process2 = Process(target=RUN_METHODE())
#
#     process1.start()
#     process2.start()
#
#     process1.join()
#     process2.join()
#     # RUN_METHODE()
#     # thread2.start()
#     # thread2.join()
#
# if __name__ == "__main__":
#     thread1 = threading.Thread(target=RecentAppPerformanceMonitorFun())
#     thread2 = threading.Thread(target=RUN_METHOD())
#
#     # Start both threads
#     thread1.start()
#     thread2.start()
#
#     # Wait for both threads to complete (this won't happen in this example as the threads run indefinitely)
#     thread1.join()
#     thread2.join()
