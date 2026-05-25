# JARVIS Automation Architecture Context

This document summarizes the JARVIS v2.1 "Iron Man" architecture pipeline for external system integration.

## 1. Core Loop & Input Ingestion
The system entry point is `jarvis/main.py`. It initializes the `Orchestrator` and enters a streaming loop via **Input Adapters**.

- **Entry Point**: `jarvis/main.py:main()`
- **Input Adapters**: Located in `jarvis/input/adapters.py`.
    - `TextAdapter`: Captures CLI input.
    - `VoiceAdapter`: Uses `faster-whisper` for STT.
    - `TelegramAdapter`: Captures messages from a Telegram bot.
- **The Loop**: Each adapter implements a `.stream()` method yielding `Utterance` objects. These are passed to `orchestrator.process(text)`.

## 2. Intent Routing
Routing follows a prioritized decision tree in `jarvis/brain/planner.py`:

1.  **Memory Recall**: Checks if the exact command or path is stored in the Graph DB (`memory/jarvis.db`).
2.  **Rule-Based Fast-Map**: Uses `jarvis/perception/nlu.py` with `_INTENT_PATTERNS` (Regex) and `_DIRECT_MAP` in `planner.py` for common actions (volume, apps, power).
3.  **LLM Router**: If no rule matches, the `LLMRouter` (`jarvis/llm/llm_router.py`) sends the prompt to the active LLM backend.

## 3. String Processing & Sanitization
Text is processed primarily in `jarvis/perception/nlu.py:parse()`:
- **Normalization**: `.strip().lower()` is applied to all incoming text.
- **Compound Detection**: Regex `_COMPOUND_SEPARATORS` splits commands like "open notepad and type hello".
- **Sanitization**: Entity extraction uses regex capture groups. For `pyautogui` operations, the `type_text` skill takes the raw extracted string but the orchestrator handles flow control.

## 4. Action Execution Modules
Skills are registered in the `SkillBus` and executed via decorators.

### OS Process Management (`jarvis/skills/builtins/app_skill.py`)
- **Launching**: Uses `os.startfile(exe)` for known aliases and `pywinauto` for window focusing.
- **Closing**: Uses `pyautogui.hotkey("alt", "F4")` for active windows or `taskkill /IM {exe} /F` for specific processes.

### System Metrics Polling (`jarvis/skills/builtins/session_skill.py`)
- **Method**: `system_status` skill.
- **Implementation**:
    ```python
    import psutil, platform
    cpu = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory()
    ```

### PyAutoGUI Interaction (`jarvis/skills/builtins/keyboard_skill.py`)
- **Typing**: Uses `pyautogui.typewrite(text, interval=interval)`.
- **Hotkeys**: Uses `pyautogui.hotkey(*parts)` (e.g., `ctrl+c`).
- **Safety**: A `time.sleep(0.5)` is often used before typing to ensure the target window has settled focus.

## 5. External APIs/Models
The `LLMRouter` manages a fallback chain:
1.  **Primary**: Typically `LocalLLM` (Ollama/Qwen2.5) or `OpenAILLM` (GPT-4o-mini).
2.  **Fallback**: Usually a smaller local model or a tunneled API.
3.  **Emergency**: `MockLLM` (hardcoded response generator to prevent system crashes).

Backends are defined in `jarvis/config/config.yaml` and monitored by a background health check thread in `LLMRouter`.
