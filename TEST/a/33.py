import threading

import speech_recognition as sr


# Define a function to perform speech recognition
def recognize_speech():
    while True:
        recognizer = sr.Recognizer()

        with sr.Microphone() as source:
            print("Listening for speech...")
            recognizer.adjust_for_ambient_noise(source)

            try:
                audio = recognizer.listen(source)
                print("Recognizing...")

                # Perform speech recognition
                recognized_text = recognizer.recognize_google(audio)
                print(f"Speech recognized: {recognized_text}")
            except sr.UnknownValueError:
                print("Speech could not be understood")
            except sr.RequestError as e:
                print(f"Error during recognition: {e}")


# Create and start the thread for speech recognition

speech_thread = threading.Thread(target=recognize_speech)
speech_thread.start()

# Perform other tasks in the main thread while speech recognition thread listens
# For example, simulate some other work here...
for i in range(5):
    print(f"Working... {i}")
