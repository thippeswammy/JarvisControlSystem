"""
Jarvis Assistant — Text Input Entry Point
=========================================
Entry point for the Jarvis AI Control System.

Usage:
  python JarvisAssistantRunWithText.py

Say 'hi jarvis' to activate, then issue commands:
  "open chrome"
  "set volume to 80"
  "go to documents"
  "click save"
  "start typing"  (then everything you type is keyboard-typed)
  "stop typing"
  "close jarvis"

Network mode:
  Uncomment inputFromOtherDevices() to receive commands over TCP socket.
"""

import socket
import threading
import logging

# ─────────────────────────────────────────────
#  Logging Setup
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("jarvis.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger("jarvis.main")

# ─────────────────────────────────────────────
#  Import the new engine
# ─────────────────────────────────────────────
from Jarvis.core.jarvis_engine import JarvisEngine

# Single shared engine instance
_engine: JarvisEngine = None


def get_engine() -> JarvisEngine:
    global _engine
    if _engine is None:
        _engine = JarvisEngine(
            feedback_fn=_speak,
            enable_window_tracking=True,
        )
    return _engine


# ─────────────────────────────────────────────
#  Feedback (TTS + print)
# ─────────────────────────────────────────────
def _speak(message: str) -> None:
    """Output feedback to console. Extend with TTS if desired."""
    print(f"  [Jarvis] {message}")
    # Uncomment to enable TTS:
    # try:
    #     from Jarvis.SpeechRecognition import SpeechController
    #     SpeechController(...).speak(message, "main")
    # except Exception:
    #     pass


# ─────────────────────────────────────────────
#  Input Modes
# ─────────────────────────────────────────────
def text_input_loop():
    """Interactive text input loop."""
    engine = get_engine()

    # Auto-greet on start
    engine.process("hi jarvis")

    print("\n" + "="*60)
    print("  JARVIS AI CONTROL SYSTEM")
    print("  Say 'hi jarvis' to activate | 'exit' or '0' to quit")
    print("  Commands work in plain English:")
    print("    open chrome | set volume 80 | go to documents")
    print("    click save  | start typing  | minimize window")
    print("="*60 + "\n")

    while True:
        try:
            text = input("You => ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            break

        if not text:
            continue

        if text.lower() in ("exit", "0", "quit", "q"):
            engine.process("close jarvis")
            break

        engine.process(text)


def socket_input_loop():
    """Receive commands over TCP socket (for remote devices / mobile)."""
    HOST = "0.0.0.0"
    PORT = 12345
    engine = get_engine()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen()
        logger.info(f"Listening for remote commands on {HOST}:{PORT}")
        print(f"  [Network] Listening on {HOST}:{PORT}...")

        conn, addr = server_socket.accept()
        with conn:
            logger.info(f"Connected from {addr}")
            print(f"  [Network] Connected from {addr}")
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                text = data.decode("utf-8").strip()
                if text.lower() in ("exit()", "exit", "0"):
                    break
                logger.info(f"Socket command: {text!r}")
                thread = threading.Thread(
                    target=engine.process,
                    args=(text,),
                    daemon=True,
                )
                thread.start()


# ─────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import os
    # Ensure imports resolve from project root
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Run text input (primary mode)
    text_input_loop()

    # To use network mode instead:
    # socket_input_loop()

    # To run both in parallel:
    # socket_thread = threading.Thread(target=socket_input_loop, daemon=True)
    # socket_thread.start()
    # text_input_loop()

    # Cleanup
    if _engine:
        _engine.shutdown()
    print("Goodbye.")
