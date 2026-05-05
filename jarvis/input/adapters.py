"""
Input Adapters (Phase 7)
========================
Text and Voice input adapters that feed utterances into the Orchestrator.

TextAdapter   — reads from stdin or a string queue (CLI / API mode)
VoiceAdapter  — wraps faster-whisper for real-time mic transcription (Phase 7)

Both return an Utterance to pass to Orchestrator.process().
"""

import logging
import queue
import threading
from pathlib import Path
from typing import Optional, Callable

from jarvis.perception.perception_packet import Utterance

logger = logging.getLogger(__name__)


# ── Telegram Logger ───────────────────────────────────────────

class TelegramLogger:
    """
    Handles logging of Telegram interactions to a dedicated file.
    """
    def __init__(self, log_path: str = "logs/telegram_chat.log"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(exist_ok=True)

    def log_input(self, chat_id: int, username: str, text: str):
        import datetime
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(f"[{now}] [Chat:{chat_id}] [@{username}] >> {text}\n")

    def log_output(self, chat_id: int, text: str):
        import datetime
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(f"[{now}] [Chat:{chat_id}] Jarvis << {text}\n")


# ── Text Adapter ──────────────────────────────────────────────

class TextAdapter:
    """
    Reads commands from stdin or a push queue.
    Used for testing, CLI mode, and API integration.

    Usage:
        adapter = TextAdapter()
        for utterance in adapter.stream():
            result = orchestrator.process(utterance.text)
    """

    def __init__(self, prompt: str = "Jarvis> "):
        self._prompt = prompt
        self._queue: queue.Queue[Optional[str]] = queue.Queue()
        self._running = False

    def push(self, text: str) -> None:
        """Push a command programmatically (API / test mode)."""
        self._queue.put(text)

    def stop(self) -> None:
        """Signal the stream loop to exit."""
        self._queue.put(None)
        self._running = False

    def stream(self):
        """Yield Utterance objects indefinitely from stdin."""
        self._running = True
        while self._running:
            try:
                text = input(self._prompt).strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not text:
                continue
            if text.lower() in ("exit", "quit"):
                break
            yield Utterance(text=text, source="text", confidence=1.0)

    def stream_queue(self):
        """Yield Utterance objects from the push queue (non-blocking mode)."""
        self._running = True
        while self._running:
            text = self._queue.get()
            if text is None:
                break
            yield Utterance(text=text, source="text", confidence=1.0)


# ── Voice Adapter ─────────────────────────────────────────────

class VoiceAdapter:
    """
    Real-time voice transcription using faster-whisper.
    Feeds into Orchestrator on keyword detection ("jarvis").

    Hardware requirements:
        - Microphone input
        - faster-whisper + ctranslate2 (CPU or CUDA)
        - Model: tiny.en or base.en (auto-downloaded)

    Usage:
        adapter = VoiceAdapter(on_wake="jarvis")
        for utterance in adapter.stream():
            result = orchestrator.process(utterance.text, source="voice",
                                          confidence=utterance.confidence)
    """

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
        """Lazy-load the Whisper model (first call only)."""
        if not self._available:
            logger.warning("[VoiceAdapter] faster-whisper not available")
            return False
        if self._model is not None:
            return True
        try:
            from faster_whisper import WhisperModel
            device = self._resolve_device()
            compute = "float16" if device == "cuda" else "int8"
            logger.info(f"[VoiceAdapter] Loading {self._model_size} on {device} ({compute})")
            self._model = WhisperModel(self._model_size, device=device, compute_type=compute)
            logger.info("[VoiceAdapter] Model loaded ✅")
            return True
        except Exception as e:
            logger.error(f"[VoiceAdapter] Model load failed: {e}")
            return False

    def transcribe(self, audio_path: str) -> tuple[str, float]:
        """
        Transcribe an audio file. Returns (text, confidence).
        confidence = mean segment probability.
        """
        if not self._model:
            return "", 0.0
        try:
            segments, info = self._model.transcribe(
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

    def stream(self, chunk_seconds: float = 3.0):
        """
        Real-time streaming from microphone.
        Yields Utterance objects after wake-word detection.

        Requires: sounddevice, numpy
        """
        if not self.load_model():
            return

        try:
            import sounddevice as sd
            import numpy as np
            import tempfile, wave
        except ImportError:
            logger.error("[VoiceAdapter] sounddevice/numpy not installed")
            return

        sample_rate = 16000
        logger.info(f"[VoiceAdapter] Listening... (wake word: '{self._wake_word}')")

        while True:
            try:
                audio = sd.rec(
                    int(chunk_seconds * sample_rate),
                    samplerate=sample_rate,
                    channels=1,
                    dtype="int16",
                )
                sd.wait()

                # Save to temp file
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    tmp_path = f.name

                with wave.open(tmp_path, "w") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(sample_rate)
                    wf.writeframes(audio.tobytes())

                text, conf = self.transcribe(tmp_path)

                if not text or conf < self._min_conf:
                    continue

                text_lower = text.lower()
                if self._wake_word in text_lower:
                    # Strip wake word from command
                    command = text_lower.replace(self._wake_word, "").strip()
                    if command:
                        logger.info(f"[VoiceAdapter] Heard: '{command}' (conf={conf:.2f})")
                        yield Utterance(text=command, source="voice", confidence=conf)

            except KeyboardInterrupt:
                logger.info("[VoiceAdapter] Stopped")
                break
            except Exception as e:
                logger.error(f"[VoiceAdapter] Stream error: {e}")

    # ── Private ──────────────────────────────────────

    def _resolve_device(self) -> str:
        if self._device != "auto":
            return self._device
        try:
            import torch
            return "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            return "cpu"

    @staticmethod
    def _check_deps() -> bool:
        try:
            import faster_whisper  # noqa
            return True
        except ImportError:
            logger.info("[VoiceAdapter] faster-whisper not installed (voice disabled)")
            return False


# ── Telegram Adapter ──────────────────────────────────────────

import requests

class TelegramAdapter:
    """
    Reads commands from a Telegram Bot using long polling.
    Useful for remote testing without speech hardware.

    Requires: requests

    Usage:
        adapter = TelegramAdapter(token="...")
        for utterance in adapter.stream():
            orch.process(utterance.text, source="telegram")
    """

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
        return bool(self._token and self._token != "${TELEGRAM_TOKEN}" and "AA" in self._token)

    def stream(self):
        """Yield Utterance objects from Telegram updates."""
        import time

        if not self.is_available():
            logger.error("[TelegramAdapter] No token provided")
            return

        self._running = True
        logger.info(f"[TelegramAdapter] Listening for messages...")

        while self._running:
            try:
                # getUpdates with long polling (timeout=30s)
                resp = self._session.get(
                    f"{self._api_url}/getUpdates",
                    params={
                        "offset": self._last_update_id + 1,
                        "timeout": 30
                    },
                    timeout=35
                )

                if resp.status_code != 200:
                    logger.debug(f"[TelegramAdapter] Status {resp.status_code}: {resp.text}")
                    time.sleep(5)
                    continue

                data = resp.json()
                updates = data.get("result", [])

                for update in updates:
                    self._last_update_id = update["update_id"]
                    
                    message = update.get("message", {})
                    text = message.get("text", "").strip()
                    chat = message.get("chat", {})
                    chat_id = chat.get("id")
                    username = chat.get("username", "unknown")

                    if not text:
                        continue

                    # Filter by chat ID if specified
                    if self._allowed_chat_ids and chat_id not in self._allowed_chat_ids:
                        logger.warning(f"[TelegramAdapter] Ignored message from unauthorized chat: {chat_id} (@{username})")
                        continue

                    logger.info(f"[TelegramAdapter] Received: '{text}' from @{username}")
                    
                    # Internal logging
                    self._logger.log_input(chat_id, username, text)

                    yield Utterance(
                        text=text,
                        source="telegram",
                        confidence=1.0,
                        metadata={"chat_id": chat_id, "username": username}
                    )

            except KeyboardInterrupt:
                break
            except requests.exceptions.RequestException as re:
                logger.debug(f"[TelegramAdapter] Network error: {re}")
                time.sleep(5)
            except Exception as e:
                logger.error(f"[TelegramAdapter] Error: {e}")
                time.sleep(5)

    def send_message(self, chat_id: int, text: str) -> bool:
        """Send a message back to a specific Telegram chat."""
        self.stop_typing(chat_id)  # Stop typing when sending message
        try:
            resp = self._session.post(
                f"{self._api_url}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "Markdown" # Enable rich formatting
                },
                timeout=10
            )
            if resp.status_code != 200:
                logger.error(f"[TelegramAdapter] Send failed ({resp.status_code}): {resp.text}")
            else:
                self._logger.log_output(chat_id, text)
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"[TelegramAdapter] Failed to send message: {e}")
            return False

    def start_typing(self, chat_id: int):
        """Starts a background thread to keep sending 'typing' action until stopped."""
        if chat_id in self._typing_events:
            return

        stop_event = threading.Event()
        self._typing_events[chat_id] = stop_event

        def _typing_loop():
            while not stop_event.is_set():
                try:
                    self._session.post(
                        f"{self._api_url}/sendChatAction",
                        json={"chat_id": chat_id, "action": "typing"},
                        timeout=5
                    )
                except Exception:
                    pass
                stop_event.wait(4.0)  # Telegram clears typing status after ~5s

        t = threading.Thread(target=_typing_loop, daemon=True)
        t.start()

    def stop_typing(self, chat_id: int):
        """Stops the background typing thread."""
        if chat_id in self._typing_events:
            self._typing_events[chat_id].set()
            del self._typing_events[chat_id]


class MockTelegramAdapter(TelegramAdapter):
    """
    Mock version of TelegramAdapter for testing.
    Instead of polling an API, it reads from a queue of simulated messages.
    """
    def __init__(self, log_path: str = "logs/telegram_test.log"):
        super().__init__(token="MOCK_TOKEN", log_path=log_path)
        self._input_queue = queue.Queue()
        self._replies = []

    def is_available(self) -> bool:
        return True

    def simulate_message(self, text: str, chat_id: int = 12345, username: str = "testuser"):
        """Programmatically inject a message into the stream."""
        self._input_queue.put({
            "text": text,
            "chat": {"id": chat_id, "username": username},
            "update_id": 0
        })

    def stream(self):
        self._running = True
        logger.info("[MockTelegramAdapter] Listening for mock messages...")
        while self._running:
            try:
                msg_data = self._input_queue.get(timeout=1.0)
                if msg_data is None: break
                
                text = msg_data["text"]
                chat_id = msg_data["chat"]["id"]
                username = msg_data["chat"]["username"]

                self._logger.log_input(chat_id, username, text)
                yield Utterance(
                    text=text,
                    source="telegram",
                    confidence=1.0,
                    metadata={"chat_id": chat_id, "username": username}
                )
            except queue.Empty:
                continue

    def send_message(self, chat_id: int, text: str) -> bool:
        self.stop_typing(chat_id)
        logger.info(f"[MockTelegramAdapter] REPLY to {chat_id}: {text}")
        self._logger.log_output(chat_id, text)
        self._replies.append({"chat_id": chat_id, "text": text})
        return True

    def start_typing(self, chat_id: int):
        pass

    def stop_typing(self, chat_id: int):
        pass

    def stop(self):
        """Stop the mock stream."""
        self._running = False
        self._input_queue.put(None)

    def get_replies(self):
        return self._replies

    def stop(self):
        self._running = False
