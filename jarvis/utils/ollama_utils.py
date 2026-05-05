import logging
import os
import subprocess
import threading
import time
import requests
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_OLLAMA_STARTED_LOCK = threading.Lock()
_OLLAMA_STARTED = False
_AUTO_START_ENABLED = False

def enable_auto_start(enabled: bool = True):
    """Enable or disable the auto-start functionality globally."""
    global _AUTO_START_ENABLED
    _AUTO_START_ENABLED = enabled

def is_ollama_running(url: str = "http://localhost:11434") -> bool:
    """Check if Ollama server is reachable."""
    try:
        # Use a short timeout for the check
        resp = requests.get(url, timeout=2)
        return resp.status_code == 200 or "Ollama is running" in resp.text
    except:
        return False

def ensure_ollama_running(url: str = "http://localhost:11434"):
    """
    Ensure Ollama is running. 
    Uses a native C++ helper for maximum speed on Windows.
    """
    global _OLLAMA_STARTED
    
    if not _AUTO_START_ENABLED:
        return
        
    # ── Try Native Helper First ──────────────────────────────
    helper_path = Path(__file__).parent / "ollama_helper.exe"
    if helper_path.exists():
        try:
            # Native helper is extremely fast and handles check + start in one go
            subprocess.Popen(
                [str(helper_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            return
        except Exception as e:
            logger.debug(f"[OllamaUtils] Native helper failed: {e}. Falling back to Python.")

    # ── Python Fallback ──────────────────────────────────────
    if is_ollama_running(url):
        return

    with _OLLAMA_STARTED_LOCK:
        if _OLLAMA_STARTED:
            return
        _OLLAMA_STARTED = True

    def _start_service():
        logger.info("[OllamaUtils] Ollama not found. Attempting to start 'ollama serve' in background...")
        try:
            # Start ollama serve. Use Popen so it doesn't block.
            # On Windows, this will start the server. 
            # If the user has Ollama installed, this command should be in PATH.
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            # Wait a few seconds and check again
            for i in range(10):
                time.sleep(2)
                if is_ollama_running(url):
                    logger.info("[OllamaUtils] Ollama successfully started and reachable.")
                    return
                logger.debug(f"[OllamaUtils] Waiting for Ollama to wake up ({i+1}/10)...")
            
            logger.warning("[OllamaUtils] Started Ollama but it's still not reachable after 20s.")
        except FileNotFoundError:
            logger.error("[OllamaUtils] 'ollama' command not found. Please install Ollama: https://ollama.com")
        except Exception as e:
            logger.error(f"[OllamaUtils] Failed to start Ollama: {e}")
        finally:
            with _OLLAMA_STARTED_LOCK:
                global _OLLAMA_STARTED
                _OLLAMA_STARTED = False

    threading.Thread(target=_start_service, daemon=True, name="OllamaStarter").start()
