import logging
import queue
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Callable, Iterator, Any

from jarvis.perception.perception_packet import Utterance

logger = logging.getLogger(__name__)


class ChannelAdapter(ABC):
    """
    Abstract Base Class for all input/output channels.
    Provides a unified interface for the Gateway to manage parallel channels.
    """
    name: str = "base"

    @abstractmethod
    def stream(self) -> Iterator[Utterance]:
        """Yield Utterances from the input source."""
        pass

    @abstractmethod
    def send(self, session_id: str, text: str) -> bool:
        """Send a reply back to the user."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the channel dependencies/config are present."""
        pass

    def start_typing(self, session_id: str) -> None:
        """Optional: Show 'typing' indicator."""
        pass

    def stop_typing(self, session_id: str) -> None:
        """Optional: Stop 'typing' indicator."""
        pass

    def on_ready(self) -> None:
        """Called when the gateway has successfully started this channel."""
        pass

    def on_stop(self) -> None:
        """Called when the gateway is shutting down."""
        pass


# ── Telegram Logger ───────────────────────────────────────────

class TelegramLogger:
    """
    Handles logging of Telegram interactions to a dedicated file.
    """
    def __init__(self, log_path: str = "logs/telegram_chat.log"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(exist_ok=True)

    def log_input(self, chat_id: Any, username: str, text: str):
        import datetime
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(f"[{now}] [Chat:{chat_id}] [@{username}] >> {text}\n")

    def log_output(self, chat_id: Any, text: str):
        import datetime
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(f"[{now}] [Chat:{chat_id}] Jarvis << {text}\n")


# ── CLI Adapter ──────────────────────────────────────────────

class CLIAdapter(ChannelAdapter):
    """
    Reads commands from stdin.
    """
    name = "cli"

    def __init__(self, prompt: str = "Jarvis> "):
        self._prompt = prompt
        self._running = False

    def is_available(self) -> bool:
        return True

    def stream(self) -> Iterator[Utterance]:
        self._running = True
        while self._running:
            try:
                # Use input() for basic CLI
                text = input(self._prompt).strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not text:
                continue
            if text.lower() in ("exit", "quit"):
                break
            yield Utterance(text=text, source="cli", confidence=1.0, metadata={"user_id": "default"})

    def send(self, session_id: str, text: str) -> bool:
        print(f"\n  Jarvis: {text}")
        return True

    def stop(self) -> None:
        self._running = False


class TUIAdapter(ChannelAdapter):
    """
    Adapter for the Rich/PromptToolkit TUI.
    Uses queues to communicate with the TUI event loop.
    """
    name = "tui"

    def __init__(self):
        self._input_queue = queue.Queue()
        self._output_queue = queue.Queue()
        self._running = False

    def is_available(self) -> bool:
        return True

    def simulate_input(self, text: str):
        """Called by TUIApp to inject text into the gateway."""
        self._input_queue.put(text)

    def get_output_queue(self) -> queue.Queue:
        """Called by TUIApp to receive messages from the gateway."""
        return self._output_queue

    def stream(self) -> Iterator[Utterance]:
        self._running = True
        while self._running:
            try:
                text = self._input_queue.get(timeout=1.0)
                if text is None: break
                yield Utterance(text=text, source="tui", confidence=1.0, metadata={"user_id": "tui_user"})
            except queue.Empty:
                continue

    def send(self, session_id: str, text: str) -> bool:
        self._output_queue.put(text)
        return True

    def stop(self) -> None:
        self._running = False
        self._input_queue.put(None)


# ── Voice Adapter ─────────────────────────────────────────────

class VoiceAdapter(ChannelAdapter):
    """
    Real-time voice transcription using faster-whisper.
    """
    name = "voice"
    SUPPORTED_MODELS = ["tiny.en", "base.en", "small.en"]

    def __init__(
        self,
        model_size: str = "tiny.en",
        wake_word: str = "jarvis",
        device: str = "auto",
        min_confidence: float = 0.65,
        vad_threshold: float = 0.50,
    ):
        self._model_size = model_size
        self._wake_word = wake_word.lower()
        self._device = device
        self._min_conf = min_confidence
        self._vad_threshold = vad_threshold
        self._model = None
        self._available = self._check_deps()

    def is_available(self) -> bool:
        return self._available

    def load_model(self) -> bool:
        if not self._available:
            return False
        if self._model is not None:
            return True
        try:
            from faster_whisper import WhisperModel
            device = self._resolve_device()
            compute = "float16" if device == "cuda" else "int8"
            self._model = WhisperModel(self._model_size, device=device, compute_type=compute)
            return True
        except Exception as e:
            logger.error(f"[VoiceAdapter] Model load failed: {e}")
            return False

    def transcribe(self, audio_path: str) -> tuple[str, float]:
        if not self._model:
            return "", 0.0
        try:
            segments, _ = self._model.transcribe(
                audio_path,
                beam_size=3,
                vad_filter=True,
                vad_parameters={"threshold": self._vad_threshold},
            )
            seg_list = list(segments)
            if not seg_list:
                return "", 0.0
            text = " ".join(s.text.strip() for s in seg_list)
            avg_prob = sum(
                sum(t.probability for t in s.tokens) / max(len(s.tokens), 1)
                for s in seg_list
            ) / len(seg_list)
            return text.strip(), round(avg_prob, 3)
        except Exception as e:
            logger.error(f"[VoiceAdapter] Transcription error: {e}")
            return "", 0.0

    def stream(self) -> Iterator[Utterance]:
        if not self.load_model():
            return

        import sounddevice as sd
        import numpy as np
        import tempfile, wave

        sample_rate = 16000
        chunk_seconds = 3.0
        logger.info(f"[VoiceAdapter] Listening...")

        while True:
            try:
                audio = sd.rec(int(chunk_seconds * sample_rate), samplerate=sample_rate, channels=1, dtype="int16")
                sd.wait()

                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    tmp_path = f.name
                with wave.open(tmp_path, "w") as wf:
                    wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sample_rate)
                    wf.writeframes(audio.tobytes())

                text, conf = self.transcribe(tmp_path)
                if not text or conf < self._min_conf:
                    continue

                if self._wake_word in text.lower():
                    command = text.lower().replace(self._wake_word, "").strip()
                    if command:
                        yield Utterance(text=command, source="voice", confidence=conf, metadata={"user_id": "default"})
            except Exception as e:
                logger.error(f"[VoiceAdapter] Stream error: {e}")
                break

    def send(self, session_id: str, text: str) -> bool:
        # Voice output is handled by a separate TTS skill usually,
        # but for now we print it.
        print(f"🎙 [Voice Reply]: {text}")
        return True

    def _resolve_device(self) -> str:
        if self._device != "auto": return self._device
        try:
            import torch
            return "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            return "cpu"

    @staticmethod
    def _check_deps() -> bool:
        try:
            import faster_whisper
            return True
        except ImportError:
            return False


# ── Telegram Adapter ──────────────────────────────────────────

import requests

class TelegramAdapter(ChannelAdapter):
    """
    Reads commands from a Telegram Bot using long polling.
    """
    name = "telegram"

    def __init__(self, token: str, allowed_chat_ids: list[int] = None, log_path: str = "logs/telegram_chat.log"):
        self._token = token
        self._allowed_chat_ids = allowed_chat_ids or []
        self._api_url = f"https://api.telegram.org/bot{token}"
        self._last_update_id = 0
        self._running = False
        self._logger = TelegramLogger(log_path)
        self._typing_events: dict[int, threading.Event] = {}
        self._session = requests.Session()

    def is_available(self) -> bool:
        return bool(self._token and "AA" in self._token)

    def stream(self) -> Iterator[Utterance]:
        import time
        if not self.is_available():
            return

        self._running = True
        logger.info(f"[TelegramAdapter] Listening...")

        while self._running:
            try:
                resp = self._session.get(
                    f"{self._api_url}/getUpdates",
                    params={"offset": self._last_update_id + 1, "timeout": 30},
                    timeout=35
                )
                if resp.status_code != 200:
                    time.sleep(5); continue

                updates = resp.json().get("result", [])
                for update in updates:
                    self._last_update_id = update["update_id"]
                    msg = update.get("message", {})
                    text = msg.get("text", "").strip()
                    chat_id = msg.get("chat", {}).get("id")
                    username = msg.get("chat", {}).get("username", "unknown")

                    if not text or (self._allowed_chat_ids and chat_id not in self._allowed_chat_ids):
                        continue

                    self._logger.log_input(chat_id, username, text)
                    yield Utterance(
                        text=text,
                        source="telegram",
                        confidence=1.0,
                        metadata={"chat_id": chat_id, "username": username, "user_id": str(chat_id)}
                    )
            except Exception as e:
                logger.debug(f"[TelegramAdapter] Error: {e}")
                time.sleep(5)

    def send(self, session_id: str, text: str) -> bool:
        # session_id for telegram is "telegram:{chat_id}"
        chat_id = session_id.split(":")[-1]
        self.stop_typing(session_id)
        try:
            resp = self._session.post(
                f"{self._api_url}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
                timeout=10
            )
            if resp.status_code == 200:
                self._logger.log_output(chat_id, text)
                return True
        except Exception as e:
            logger.error(f"[TelegramAdapter] Send failed: {e}")
        return False

    def start_typing(self, session_id: str):
        chat_id = session_id.split(":")[-1]
        if chat_id in self._typing_events: return

        stop_event = threading.Event()
        self._typing_events[chat_id] = stop_event

        def _loop():
            while not stop_event.is_set():
                try:
                    self._session.post(f"{self._api_url}/sendChatAction", 
                                     json={"chat_id": chat_id, "action": "typing"}, timeout=5)
                except: pass
                stop_event.wait(4.0)

        threading.Thread(target=_loop, daemon=True).start()

    def stop_typing(self, session_id: str):
        chat_id = session_id.split(":")[-1]
        if chat_id in self._typing_events:
            self._typing_events[chat_id].set()
            del self._typing_events[chat_id]


class MockTelegramAdapter(TelegramAdapter):
    """
    Mock version of TelegramAdapter for testing.
    """
    name = "telegram-test"

    def __init__(self, log_path: str = "logs/telegram_test.log"):
        super().__init__(token="MOCK_TOKEN", log_path=log_path)
        self._input_queue = queue.Queue()
        self._replies = []

    def is_available(self) -> bool:
        return True

    def simulate_message(self, text: str, chat_id: int = 12345, username: str = "testuser"):
        self._input_queue.put({"text": text, "chat": {"id": chat_id, "username": username}})

    def stream(self) -> Iterator[Utterance]:
        self._running = True
        while self._running:
            try:
                msg = self._input_queue.get(timeout=1.0)
                if msg is None: break
                chat_id = msg["chat"]["id"]
                self._logger.log_input(chat_id, msg["chat"]["username"], msg["text"])
                yield Utterance(
                    text=msg["text"], source="telegram", confidence=1.0,
                    metadata={"chat_id": chat_id, "username": msg["chat"]["username"], "user_id": str(chat_id)}
                )
            except queue.Empty: continue

    def send(self, session_id: str, text: str) -> bool:
        chat_id = session_id.split(":")[-1]
        logger.info(f"[MockTelegram] REPLY to {chat_id}: {text}")
        self._logger.log_output(chat_id, text)
        self._replies.append({"chat_id": chat_id, "text": text})
        return True

    def stop(self):
        self._running = False
        self._input_queue.put(None)

    def get_replies(self):
        return self._replies
