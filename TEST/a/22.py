import threading
import time


# Define a function that will run in a thread
def print_numbers():
    for i in range(5):
        print(f"Number: {i}")
        time.sleep(1)  # Simulating some delay


def print_letters():
    for letter in 'ABCDE':
        print(f"Letter: {letter}")
        time.sleep(1.5)  # Simulating some delay


# Create threads for each function
thread1 = threading.Thread(target=print_numbers)
thread2 = threading.Thread(target=print_letters)

# Start the threads
thread1.start()
thread2.start()

# Wait for the threads to complete (optional)
thread1.join()
thread2.join()

# The main thread continues while the other threads run concurrently
print("Main thread continues...")
