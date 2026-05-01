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
from typing import Optional, Callable

from jarvis_v2.perception.perception_packet import Utterance

logger = logging.getLogger(__name__)


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
