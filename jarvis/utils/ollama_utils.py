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
_OLLAMA_READY_EVENT = threading.Event()  # Set when Ollama becomes reachable

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
            # Give it a short moment to start/check
            time.sleep(0.5)
            if is_ollama_running(url):
                return
            logger.debug("[OllamaUtils] Native helper ran but Ollama not yet running. Trying Python fallback.")
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
            cmd = "ollama"
            if os.name == "nt":
                import shutil
                if not shutil.which("ollama"):
                    local_appdata = os.environ.get("LOCALAPPDATA")
                    if local_appdata:
                        std_path = Path(local_appdata) / "Programs" / "Ollama" / "ollama.exe"
                        if std_path.exists():
                            cmd = str(std_path)
            
            # Set OLLAMA_MAX_LOADED_MODELS=2 so Ollama keeps both the LLM model
            # and nomic-embed-text resident in VRAM simultaneously, preventing
            # the costly model-swap that causes 60s timeouts.
            env = os.environ.copy()
            env["OLLAMA_MAX_LOADED_MODELS"] = "2"
            env["OLLAMA_NUM_PARALLEL"] = "1"   # 1 request at a time, no queue buildup

            subprocess.Popen(
                [cmd, "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            # Wait up to 30s for Ollama to become reachable
            for i in range(15):
                time.sleep(2)
                if is_ollama_running(url):
                    logger.info("[OllamaUtils] Ollama successfully started and reachable.")
                    _OLLAMA_READY_EVENT.set()
                    return
                logger.debug(f"[OllamaUtils] Waiting for Ollama to wake up ({i+1}/15)...")
            
            logger.warning("[OllamaUtils] Started Ollama but it's still not reachable after 30s.")
        except FileNotFoundError:
            logger.error("[OllamaUtils] 'ollama' command not found. Please install Ollama: https://ollama.com")
        except Exception as e:
            logger.error(f"[OllamaUtils] Failed to start Ollama: {e}")
        finally:
            with _OLLAMA_STARTED_LOCK:
                global _OLLAMA_STARTED
                _OLLAMA_STARTED = False  # Allow retry on next call

    threading.Thread(target=_start_service, daemon=True, name="OllamaStarter").start()



def wait_for_ollama_ready(url: str = "http://localhost:11434", timeout: float = 35.0) -> bool:
    """
    Block until Ollama is reachable or timeout expires.
    Returns True if Ollama is ready, False if it timed out.
    Call this after ensure_ollama_running() to synchronise startup.
    """
    if is_ollama_running(url):
        return True
    # Wait for the background starter thread to signal readiness
    ready = _OLLAMA_READY_EVENT.wait(timeout=timeout)
    if ready:
        logger.info("[OllamaUtils] Ollama is ready (event received).")
    else:
        # Last-chance direct check in case the event was already set before we started waiting
        ready = is_ollama_running(url)
        if ready:
            logger.info("[OllamaUtils] Ollama is ready (direct check).")
        else:
            logger.warning(f"[OllamaUtils] Timed out waiting {timeout}s for Ollama to become ready.")
    return ready


def prewarm_models(models: list, ollama_base_url: str = "http://localhost:11434", timeout: float = 45.0) -> None:
    """
    Pre-load each model into Ollama's VRAM by sending a minimal generation request.
    This prevents the first real user request from waiting for model-load cold-start.

    Call this after wait_for_ollama_ready() returns True.
    Runs in a background thread so it never blocks the gateway startup.

    Args:
        models: list of model name strings, e.g. ["qwen3.5:2b", "nomic-embed-text"]
        ollama_base_url: base URL of the Ollama server
        timeout: per-model prewarm timeout in seconds
    """
    def _do_prewarm():
        for model in models:
            try:
                logger.info(f"[OllamaUtils] Pre-warming model into VRAM: {model}")
                # Use /api/generate with keep_alive to pin model in VRAM
                payload = {
                    "model": model,
                    "prompt": "",
                    "keep_alive": "10m",   # keep model hot for 10 minutes
                    "stream": False,
                }
                resp = requests.post(
                    f"{ollama_base_url}/api/generate",
                    json=payload,
                    timeout=timeout,
                )
                if resp.status_code == 200:
                    logger.info(f"[OllamaUtils] Model '{model}' is warm and resident in VRAM.")
                else:
                    logger.warning(f"[OllamaUtils] Prewarm for '{model}' returned HTTP {resp.status_code}.")
            except requests.exceptions.Timeout:
                logger.warning(f"[OllamaUtils] Prewarm for '{model}' timed out after {timeout}s — model may be loading slowly.")
            except Exception as e:
                logger.warning(f"[OllamaUtils] Prewarm for '{model}' failed: {e}")

    threading.Thread(target=_do_prewarm, daemon=True, name="OllamaPrewarm").start()

