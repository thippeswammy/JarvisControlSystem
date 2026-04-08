import logging
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Union

import pyttsx3
import speech_recognition as sr
from win10toast import ToastNotifier

# from WINDOWS_SystemController import MainActivationWindows  # Import from system controller

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    filename='speech_controller.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s'
)


# Custom exception
class SpeechControlError(Exception):
    pass


# Embedded configuration
CONFIG = {
    "speech_patterns": {
        "opening": "Opening {command}",
        "closing": "Closing {command}",
        "pressing": "Pressing {command} key",
        "typing": "Typing {command}",
        "holding": "Pressed {command} key",
        "releasing": "Releasing {command} key"
    },
    "notification_settings": {
        "default_duration": 5,
        "icon_path": "icon.ico"
    },
    "speech_settings": {
        "voice_id": 0,
        "rate": 150,
        "volume": 0.9
    }
}


# Speech controller class
class SpeechController:
    def __init__(self, config: Dict):
        """Initialize speech controller with recognizer and TTS engine."""
        self.config = config
        self.recognizer = sr.Recognizer()
        self.engine = pyttsx3.init()
        self.executor = ThreadPoolExecutor(max_workers=2)  # Limit threads for speech
        self._configure_engine()

    def _configure_engine(self) -> None:
        """Configure TTS engine settings."""
        settings = self.config.get("speech_settings", {})
        try:
            voices = self.engine.getProperty('voices')
            self.engine.setProperty('voice', voices[settings.get("voice_id", 0)].id)
            self.engine.setProperty('rate', settings.get("rate", 150))
            self.engine.setProperty('volume', settings.get("volume", 0.9))
            logging.info("TTS engine configured successfully")
        except Exception as e:
            logging.error(f"Failed to configure TTS engine: {e}")

    def speak(self, text: str, addr: str = "") -> None:
        """Speak the given text asynchronously."""

        def _speak():
            try:
                self.engine.say(text)
                self.engine.runAndWait()
                logging.info(f"Spoke: {text} [Addr: {addr}]")
            except Exception as e:
                logging.error(f"Failed to speak: {e} [Addr: {addr}]")

        try:
            self.executor.submit(_speak)
        except Exception as e:
            logging.error(f"Failed to queue speech task: {e} [Addr: {addr}]")

    def format_speech(self, command_type: str, command: str, addr: str = "") -> None:
        """Format and speak a command based on its type."""
        patterns = self.config.get("speech_patterns", {})
        template = patterns.get(command_type, "{command}")
        text = template.format(command=command)
        self.speak(text, addr)

    def listen(self, timeout: int = 5, retries: int = 3) -> str:
        """Listen for speech input with retries and timeout."""
        for attempt in range(retries):
            with sr.Microphone() as source:
                self.speak("Listening, say something", "listen")
                logging.debug(f"Listening attempt {attempt + 1}/{retries}")
                try:
                    self.recognizer.adjust_for_ambient_noise(source, duration=1)
                    audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=5)
                    self.speak("Processing speech", "listen")
                    text = self.recognizer.recognize_google(audio)
                    logging.info(f"Speech recognized: {text}")
                    return text.lower()
                except sr.WaitTimeoutError:
                    logging.warning(f"Speech recognition timed out (attempt {attempt + 1})")
                except sr.UnknownValueError:
                    logging.warning(f"Could not understand audio (attempt {attempt + 1})")
                except sr.RequestError as e:
                    logging.error(f"Speech recognition error: {e} (attempt {attempt + 1})")
        self.speak("Failed to recognize speech", "listen")
        return ""

    def shutdown(self) -> None:
        """Shutdown the thread pool and TTS engine."""
        self.executor.shutdown(wait=True)
        self.engine.stop()
        logging.info("SpeechController shutdown")


# Notification controller
class NotificationController:
    def __init__(self, config: Dict):
        """Initialize notification controller."""
        self.config = config
        self.toaster = ToastNotifier()

    def show_notification(self, title: str, message: str, addr: str = "") -> bool:
        """Show a Windows toast notification."""
        settings = self.config.get("notification_settings", {})
        duration = settings.get("default_duration", 5)
        icon_path = settings.get("icon_path", None)
        try:
            self.toaster.show_toast(
                title,
                message,
                duration=duration,
                icon_path=icon_path if os.path.exists(icon_path or "") else None,
                threaded=True
            )
            logging.info(f"Notification shown: {title} - {message} [Addr: {addr}]")
            return True
        except Exception as e:
            logging.error(f"Failed to show notification: {e} [Addr: {addr}]")
            return False


# Command processor
class VoiceCommandProcessor:
    def __init__(self, speech_controller: SpeechController, notification_controller: NotificationController):
        """Initialize voice command processor."""
        self.speech_controller = speech_controller
        self.notification_controller = notification_controller
        self.speech_patterns = {
            "open": self.speech_controller.format_speech,
            "close": self.speech_controller.format_speech,
            "press": self.speech_controller.format_speech,
            "type": self.speech_controller.format_speech,
            "hold": self.speech_controller.format_speech,
            "release": self.speech_controller.format_speech
        }

    def process_command(self, command: Union[str, list], addr: str = "") -> bool:
        """Process a command (string or list) and execute it."""
        if isinstance(command, list):
            command = " ".join(command).strip()
        if not command:
            self.notification_controller.show_notification("Error", "No command provided", addr)
            return False

        # Check for specific speech commands
        for cmd_type, handler in self.speech_patterns.items():
            if command.startswith(cmd_type):
                parts = command.split(maxsplit=1)
                if len(parts) > 1:
                    handler(cmd_type, parts[1], addr)
                    return True

        # Pass to WINDOWS_SystemController
        # result = MainActivationWindows(command, addr)
        # if result:
        #     self.notification_controller.show_notification("Success", f"Executed: {command}", addr)
        #     self.speech_controller.speak(f"Executed {command}", addr)
        # else:
        #     self.notification_controller.show_notification("Error", f"Failed to execute: {command}", addr)
        #     self.speech_controller.speak(f"Failed to execute {command}", addr)
        return True

    def listen_and_process(self, addr: str = "") -> bool:
        """Listen for a voice command and process it."""
        command = self.speech_controller.listen()
        return self.process_command(command, addr)


# Main execution
def main():
    """Main function to initialize and run voice command processing."""
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    config = CONFIG

    speech_controller = SpeechController(config)
    notification_controller = NotificationController(config)
    processor = VoiceCommandProcessor(speech_controller, notification_controller)

    try:
        # Example: Process predefined commands
        commands = [
            "set brightness to 50",
            "increase volume by 20",
            "minimize all windows",
            "switch windows",
            "press enter"
        ]
        for cmd in commands:
            result = processor.process_command(cmd, "main")
            print(f"Command '{cmd}' result: {result}")

        # Example: Listen for voice input
        print("Starting voice command listener...")
        result = processor.listen_and_process("voice")
        print(f"Voice command result: {result}")

    finally:
        speech_controller.shutdown()


if __name__ == "__main__":
    main()
