# JarvisControlSystem

JarvisControlSystem is an advanced, autonomous virtual assistant system inspired by J.A.R.V.I.S from Marvel's Iron Man. Evolving from a basic voice-command and gesture script, JARVIS is now a self-aware, state-persistent, and fully autonomous desktop agent built on the robust v2.1 "Iron Man" Architecture.

## Vision & Architecture
JARVIS aims to provide seamless, hands-free automation of the digital workspace by decoupling cognitive intent from physical execution. 

The system relies on an **Orchestrator brain** and a continuous **Verification Loop** to interpret semantic intents and safely execute native Windows actions. Powered by local LLMs (like Ollama/gemma3) for privacy and offline inference, JARVIS maintains a rich context of the user's environment through a DAG-based persistent memory model.

## Core System Capabilities 

* **State-Aware Delta Navigation**: Employs "Look-Before-You-Leap" execution by dynamically evaluating the current UI state (`get_ui_tree`). This state-awareness prevents blind macro execution and ensures the agent knows exactly where it is before acting.
* **Self-Learning Semantic Macros**: An autonomous macro-learning engine that caches successful, LLM-generated physical skill sequences into a Graph DB. These learned "reflexes" are intrinsically tied to the specific UI state signatures in which they are valid.
* **Advanced Memory Architecture**: Utilizes a 5-layer persistent memory model (Episodic, Preference, Task, etc.) coupled with a RAG context pipeline. This allows JARVIS to remember complex workflows, inject persistent system context (Preference Routing), and elegantly handle semantic collisions.
* **Robust Execution & Safety**: Enforces "Success-Gate" validation and strict "Payload Safety Checks" to filter out dynamic cognitive tasks from static physical execution, guaranteeing that learned macros are executed safely.
* **Intelligent Pathfinding**: Implements an A* pathfinding engine to navigate complex desktop environments and reach intended UI states dynamically.
* **Remote Telemetry & Control**: Features a fully integrated Telegram bot acting as a remote interface for command execution and two-way communication, complete with extensive interaction logging (`telegram_chat.log`) for auditing and debugging.

## Legacy Automation Features

While the core architecture has been overhauled, JARVIS still supports its foundational automation capabilities:
* **Application Management**: Monitors, opens, and closes applications dynamically, tracking performance and file paths.
* **System & Window Control**: Navigates Windows settings, adjusts system controls (brightness, volume), and manages active windows.
* **Accessibility Inputs**: Integrates multi-threaded speech recognition and camera-based hand gesture detection for alternative control paradigms.

## Setup & Usage

1. Clone the repository.
2. Install Python dependencies using `pip install -r requirements.txt`.
3. Configure your local LLM provider (e.g., Ollama) and Telegram Bot tokens.
4. Run the main orchestration loop to initialize the Jarvis Control System.

---
*This system is currently undergoing active migration to finalize the v2.1 architecture, stabilizing the testing regression suite and refining its persistent DAG-based memory models.*
