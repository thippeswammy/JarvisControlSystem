import threading

import pyttsx3
import speech_recognition as sr


def listen_speech():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening... Say something.")
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)
    try:
        print("Recognizing...")
        text = recognizer.recognize_google(audio)
        print("Speech recognized:", text)
        return text.lower()
    except sr.UnknownValueError:
        print("Could not understand audio.")
        return ""
    except sr.RequestError as e:
        print("Error fetching results; {0}".format(e))
        return ""


engine = pyttsx3.init()


def MainSpeaker(command, addr):
    engine.say(command)
    engine.runAndWait()
    # print(command,addr+"COMPLETED")


def Speaker(command, addr):
    pass
    try:
        thread = threading.Thread(target=MainSpeaker(command, addr + "MainSpeaker -> "))
        thread.start()
        # MainSpeaker(command, addr + "MainSpeaker -> ")
    except Exception:
        print("ERROR In Speaker")


def OpeningSpeaker(command, addr):
    # print("opening " + " ".join(command[1:]))
    Speaker("opening " + " ".join(command[1:]), addr + "Speaker -> ")


def ClosingSpeaker(command, addr):
    # print("closing " + " ".join(command[1:]))
    Speaker("closing " + " ".join(command[1:]), addr + "Speaker -> ")


def PressingSpeaker(command, addr):
    # print("pressing " + " ".join(command) + " key")
    Speaker("pressing " + " ".join(command) + " key", addr + "Speaker -> ")


def TypingSpeaker(command, addr):
    # print("Typing " + command)
    Speaker("Typing " + command, addr + "Speaker -> ")


def holdingSpeaker(command, addr):
    # print("pressed " + " ".join(command) + " key")
    Speaker("pressed " + " ".join(command) + " key", addr + "Speaker -> ")


def releasingSpeaker(command, addr):
    # print("releasing " + " ".join(command) + " key")
    Speaker("releasing " + " ".join(command) + " key", addr + "Speaker -> ")

# Speaker("open notepad","aa")
# listen_speech()
