# JarvisControlSystem
JarvisControlSystem is a Python-based virtual assistant system inspired by J.A.R.V.I.S from Marvel's Iron Man. It integrates various functionalities aimed at automating and enhancing computer interaction through voice commands and image processing.

## Features
Speech Recognition and Response: Converts speech into text using the Speech Recognizer module, allowing users to command the system verbally.

RecentAppPerformanceMonitor: Tracks and logs information about opened applications and their file paths.

SystemFilePathScanner: Scans specified locations for executable (.exe) and shortcut (.lnk) files, storing results in an Excel (.xlsx) file.

KeyboardAutomationController: Simulates keyboard inputs based on user commands, enabling automation without physical interaction.

WindowsSettingsAutomation - DesktopSystemController: Controls system settings such as brightness and volume, and manages window positions.

WindowsSettingsAutomation - WindowsAppController: Manipulates application windows (minimize, maximize, close) and manages active windows.

ApplicationManager: Opens and closes applications based on user commands, using application names to locate executable files.

CommandProcessor: Interprets user commands to perform various actions, remembers states, and manages application lifecycles.

SettingControlApp: Navigates through system settings using window titles and interacts with UI elements like buttons, text fields, and links.

HandSectionMovement: Processes camera input to detect hands and uses gestures to control window operations like minimize and maximize.

JarvisAssistantRunWithSpeech: Orchestrates speech input processing, app performance monitoring, and camera handling with multi-threading for efficient parallel execution.

## Usage
JarvisControlSystem eliminates the need for direct computer interaction, providing a hands-free experience through voice commands and gesture control. It enhances productivity by automating repetitive tasks and simplifying system management.


Clone the repository.
Install Python dependencies (requirements.txt).
Ensure appropriate hardware for camera input if using gesture control features.
Future Development
Extend gesture recognition capabilities for more complex interactions.
Enhance speech recognition accuracy and expand command vocabulary.
Integrate with additional applications and system controls for broader functionality.
