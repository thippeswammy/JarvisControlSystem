import threading

import pyttsx3


def MainSpeaker(engine, command, addr):
    engine.say(command)
    engine.runAndWait()
    # Other functionality related to speaker function


def thread_function():
    engine = pyttsx3.init()
    # Other initialization steps

    # Your main loop
    while True:
        # Your logic
        MainSpeaker(engine, "Your command here", "Address here")
        # Other functionality


# Start your thread
thread = threading.Thread(target=thread_function)
thread.start()
