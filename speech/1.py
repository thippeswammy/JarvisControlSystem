import torch
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
import soundfile as sf
import librosa
import speech_recognition as sr
import pyttsx3
import threading


def Notifications(notification_type, message):
    print(f"{notification_type.upper()}: {message}")


def listen_and_save_audio(file_path):
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        Notifications('speech', "Listening... Say something.")
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)

    with open(file_path, "wb") as f:
        f.write(audio.get_wav_data())

    return file_path


def resample_audio(file_path, target_sample_rate=16000):
    # Load the audio file
    speech, sample_rate = sf.read(file_path)

    # Resample the audio if the sample rate is different
    if sample_rate != target_sample_rate:
        speech = librosa.resample(speech, orig_sr=sample_rate, target_sr=target_sample_rate)

    return speech, target_sample_rate


def transcribe_speech(file_path):
    # Resample the audio to 16 kHz
    speech, sample_rate = resample_audio(file_path)

    # Tokenize input
    input_values = processor(speech, sampling_rate=sample_rate, return_tensors="pt").input_values

    # Perform inference
    with torch.no_grad():
        logits = model(input_values).logits

    # Decode predicted ids
    predicted_ids = torch.argmax(logits, dim=-1)
    transcription = processor.decode(predicted_ids[0])

    return transcription.lower()


# Load pre-trained model and tokenizer
processor = Wav2Vec2Processor.from_pretrained("facebook/wav2vec2-base-960h")
model = Wav2Vec2ForCTC.from_pretrained("facebook/wav2vec2-base-960h")

engine = pyttsx3.init()


def MainSpeaker(command, addr):
    engine.say(command)
    engine.runAndWait()


def Speaker(command, addr):
    try:
        thread = threading.Thread(target=MainSpeaker, args=(command, addr + "MainSpeaker -> "))
        thread.start()
    except Exception as e:
        print(f"ERROR In Speaker: {e}")


if __name__ == "__main__":
    audio_file = listen_and_save_audio("audio.wav")
    command = transcribe_speech(audio_file)
    if command:
        Speaker(command, "Address")
