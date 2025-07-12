import logging
import os
from typing import List, Dict, Union, Optional

from Jarvis.ApplicationManager import open_application, close_application
from Jarvis.Data.JSON_Information_Center import loadDate
from Jarvis.KeyboardAutomationController import hold_key, press_key, release_key, type_text
from Jarvis.SpeechRecognition import SpeechController, NotificationController, VoiceCommandProcessor
from Jarvis.SystemFilePathScanner import GetAllFilePath
from Jarvis.WindowsDefaultApps.settingControlApp import SettingControlAccess as SettingWindows
from Jarvis.WindowsFeature.WINDOWS_SystemController import MainActivationWindows, DesktopSystemController

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    filename='command_processor.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s'
)


# Custom exception
class CommandProcessorError(Exception):
    pass


# Embedded configuration
CONFIG = {
    "speech_patterns": {
        "opening": "Opening {command}",
        "closing": "Closing {command}",
        "pressing": "Pressing {command} key",
        "typing": "Typing {command}",
        "holding": "Pressed {command} key",
        "releasing": "Releasing {command} key",
        "jarvis_activated": "Jarvis activated",
        "jarvis_deactivated": "Jarvis deactivated",
        "typing_on": "Typing mode activated",
        "typing_off": "Typing mode deactivated",
        "win_search_on": "Opening apps via Windows Search is now preferred",
        "win_search_off": "Opening apps directly is now preferred",
        "open_settings": "Opening settings",
        "close_settings": "Closing settings",
        "rescan_triggered": "Starting application scan, please wait",
        "rescan_complete": "Application scan complete, list updated",
        "rescan_error": "Error during application scan",
        "ask_app": "Which application would you like to {action}?",
        "search_ask_query": "What would you like to search for?",
        "trying_to_open": "Attempting to open {command}",
        "trying_to_close": "Attempting to close {command}",
        "open_fail_trying_search": "Could not open {command} directly, trying Windows Search",
        "open_search_fallback_fail": "Sorry, could not open {command} even with Windows Search",
        "close_fail": "Could not close {command}, or it was not running",
        "locked_window_action": "Performed {command} in the current window context"
    },
    "notification_settings": {
        "default_duration": 5,
        "icon_path": "icon.ico"
    },
    "speech_settings": {
        "voice_id": 0,
        "rate": 150,
        "volume": 0.9
    },
    "command_settings": {
        "delay": 3,
        "file_data_path": os.path.join(os.path.dirname(__file__), 'Data', 'Data_Information_Value', 'Data1.json')
    }
}


class UserCommandProcessor:
    _is_desktop_mode: bool = False
    _is_jarvis_active: bool = False
    _is_typing_active: bool = False
    _lock_opened_windows: bool = False
    _open_by_windows_search: bool = False
    _delay: int = CONFIG["command_settings"]["delay"]
    _speech_controller: Optional[SpeechController] = None
    _notification_controller: Optional[NotificationController] = None
    _voice_processor: Optional[VoiceCommandProcessor] = None

    # Command lists from JSON or defaults
    _data: Dict = {}
    activating_jarvis_cmds: List[str] = []
    deactivating_jarvis_cmds: List[str] = []
    typing_start_cmds: List[str] = []
    typing_stop_cmds: List[str] = []
    press_key_cmds: List[str] = []
    hold_key_cmds: List[str] = []
    release_key_cmds: List[str] = []
    open_app_cmds: List[str] = []
    close_app_cmds: List[str] = []
    search_cmds: List[str] = []
    windows_search_enable_cmds: List[str] = []
    windows_search_disable_cmds: List[str] = []
    rescan_apps_cmds: List[str] = []
    open_settings_cmds: List[str] = ['open settings', 'open setting']
    close_settings_cmds: List[str] = ['close settings', 'close setting']

    @classmethod
    def initialize(cls) -> None:
        """Initialize controllers and load command data."""
        cls._speech_controller = SpeechController(CONFIG)
        cls._notification_controller = NotificationController(CONFIG)
        cls._voice_processor = VoiceCommandProcessor(cls._speech_controller, cls._notification_controller)
        cls._load_command_data()

    @classmethod
    def _load_command_data(cls) -> None:
        """Load command data from JSON or use defaults."""
        file_path = CONFIG["command_settings"]["file_data_path"]
        try:
            cls._data = loadDate(file_path)
            if cls._data is None or not isinstance(cls._data, dict):
                logging.warning(f"Data from {file_path} is None or not a dict. Using defaults.")
                cls._data = {}
        except Exception as e:
            logging.error(f"Failed to load data from {file_path}: {e}. Using defaults.")
            cls._data = {}

        # Set command lists with defaults
        cls.activating_jarvis_cmds = cls._data.get('activating_jarvis',
                                                   ['hi', 'hi jarvis', 'jarvis', 'start jarvis', 'jarvis start'])
        cls.deactivating_jarvis_cmds = cls._data.get('deactivating_jarvis',
                                                     ['jarvis close', 'close jarvis', 'jarvis stop', 'stop jarvis'])
        cls.typing_start_cmds = cls._data.get('typing_jarvies',
                                              ['start typing', 'typing start', 'activate typing', 'typing activate'])
        cls.typing_stop_cmds = cls._data.get('stop_typing_jarvies',
                                             ['stop typing', 'typing stop', 'deactivate typing', 'typing deactivate'])
        cls.press_key_cmds = cls._data.get('presskey_jarvis1', ['press', 'press key', 'key press'])
        cls.hold_key_cmds = cls._data.get('holdkey_jarvis', ['hold', 'holdkey', 'hold key', 'keydown'])
        cls.release_key_cmds = cls._data.get('relasekey_jarvis', ['release', 'releasekey', 'release key'])
        cls.open_app_cmds = cls._data.get('OpenApp_jarvis', ['open', 'start', 'run', 'launch'])
        cls.close_app_cmds = cls._data.get('CloseApp_jarvis', ['close', 'exit', 'terminate', 'quit'])
        cls.search_cmds = cls._data.get('SearchApp_jarvis', ['search', 'find', 'windows search', 'window search'])
        cls.windows_search_enable_cmds = cls._data.get('WindowsSearchBarAccess_jarvis',
                                                       ['open by search', 'open by windows search'])
        cls.windows_search_disable_cmds = cls._data.get('closeByWindows_jarvis',
                                                        ['stop by search', 'stop by windows search'])
        cls.rescan_apps_cmds = cls._data.get('rescan_apps_cmds',
                                             ['rescan apps', 'refresh apps', 'scan for programs', 'find new apps',
                                              'update app list', 'refresh application list'])
        logging.info("Command data loaded successfully")

    @classmethod
    def main_activation(cls, operation: Union[str, List[str]], addr: str = "") -> bool:
        """Process primary commands and delegate to sub_activation if needed."""
        if not cls._speech_controller:
            cls.initialize()

        if isinstance(operation, list):
            operation = " ".join(operation).strip()
        op_lower_stripped = operation.lower().strip()
        logging.debug(f"Processing command: {op_lower_stripped} [Addr: {addr}]")

        if not cls._is_jarvis_active and op_lower_stripped not in cls.activating_jarvis_cmds:
            cls._speech_controller.speak("Jarvis is not active. Say 'Hi Jarvis' to activate.", addr + "inactive_prompt")
            logging.info(f"Jarvis inactive, command ignored: {op_lower_stripped} [Addr: {addr}]")
            return False

        if op_lower_stripped in cls.activating_jarvis_cmds:
            if not cls._is_jarvis_active:
                cls._is_jarvis_active = True
                cls._speech_controller.format_speech("jarvis_activated", "", addr + "jarvis_activated")
                cls._notification_controller.show_notification("Jarvis", "Activated", addr + "jarvis_activated")
            else:
                cls._speech_controller.speak("Jarvis is already active.", addr + "jarvis_already_active")
            return True
        elif op_lower_stripped in cls.deactivating_jarvis_cmds:
            cls._is_jarvis_active = False
            cls._speech_controller.format_speech("jarvis_deactivated", "", addr + "jarvis_deactivated")
            cls._notification_controller.show_notification("Jarvis", "Deactivated", addr + "jarvis_deactivated")
            return True
        elif op_lower_stripped in cls.typing_start_cmds:
            cls._is_typing_active = True
            cls._speech_controller.format_speech("typing_on", "", addr + "typing_on")
            cls._notification_controller.show_notification("Typing", "Mode activated", addr + "typing_on")
            return True
        elif op_lower_stripped in cls.typing_stop_cmds:
            cls._is_typing_active = False
            cls._speech_controller.format_speech("typing_off", "", addr + "typing_off")
            cls._notification_controller.show_notification("Typing", "Mode deactivated", addr + "typing_off")
            return True
        elif op_lower_stripped in cls.windows_search_enable_cmds:
            cls._open_by_windows_search = True
            cls._speech_controller.format_speech("win_search_on", "", addr + "win_search_on")
            cls._notification_controller.show_notification("Search", "Windows Search enabled", addr + "win_search_on")
            return True
        elif op_lower_stripped in cls.windows_search_disable_cmds:
            cls._open_by_windows_search = False
            cls._speech_controller.format_speech("win_search_off", "", addr + "win_search_off")
            cls._notification_controller.show_notification("Search", "Windows Search disabled", addr + "win_search_off")
            return True
        elif op_lower_stripped in cls.open_settings_cmds:
            cls._lock_opened_windows = True
            cls._speech_controller.format_speech("open_settings", "", addr + "open_settings")
            return cls.sub_activation(op_lower_stripped, addr + "sub_act_open_settings")
        elif op_lower_stripped in cls.close_settings_cmds or \
                (cls._lock_opened_windows and op_lower_stripped in cls.close_app_cmds):
            cls._speech_controller.format_speech("close_settings", "", addr + "close_settings")
            closed = cls.sub_activation(op_lower_stripped, addr + "sub_act_close_settings")
            cls._lock_opened_windows = False
            return closed
        elif op_lower_stripped in cls.rescan_apps_cmds:
            cls._speech_controller.format_speech("rescan_triggered", "", addr + "rescan_triggered")
            try:
                GetAllFilePath(addr + "rescan_apps_cmd")
                cls._load_command_data()  # Reload JSON data after rescan
                cls._speech_controller.format_speech("rescan_complete", "", addr + "rescan_complete")
                cls._notification_controller.show_notification("Apps", "Application scan complete",
                                                               addr + "rescan_complete")
                return True
            except Exception as e:
                cls._speech_controller.format_speech("rescan_error", "", addr + "rescan_error")
                cls._notification_controller.show_notification("Error", f"Application scan failed: {e}",
                                                               addr + "rescan_error")
                logging.error(f"Rescan apps failed: {e} [Addr: {addr}]")
                return False
        else:
            return cls.sub_activation(op_lower_stripped, addr + "sub_act_general")

    @classmethod
    def sub_activation(cls, operation: str, addr: str = "") -> bool:
        """Delegate to specific command handlers."""
        if cls._lock_opened_windows and cls.control_opened_windows(operation, addr + "control_locked_window"):
            return True
        if cls.control_keyboard(operation, addr + "control_keyboard"):
            return True
        if cls.control_app_opening(operation, addr + "control_app_opening"):
            return True
        if cls.control_app_closing(operation, addr + "control_app_closing"):
            return True
        if cls.control_search(operation, addr + "control_search"):
            return True
        if cls.controlling_active_window(operation, addr + "control_active_window"):
            return True
        logging.warning(f"Operation not handled: {operation} [Addr: {addr}]")
        cls._speech_controller.speak(f"Command {operation} not recognized.", addr + "unhandled_command")
        return False

    @classmethod
    def control_search(cls, operation: str, addr: str = "") -> bool:
        """Handle Windows Search commands."""
        op_parts = operation.split()
        command_verb = op_parts[0]
        if command_verb in cls.search_cmds:
            search_query_parts = op_parts[1:]
            if not search_query_parts:
                cls._speech_controller.format_speech("search_ask_query", "", addr + "search_ask_query")
                cls._notification_controller.show_notification("Search", "Please specify a search query",
                                                               addr + "search_ask_query")
                return True
            search_query = " ".join(search_query_parts)
            cls._speech_controller.speak(f"Searching Windows for: {search_query}", addr + "searching_for")
            DesktopSystemController.search_windows_for_term(search_query_parts, addr + "DesktopSearch.search_term")
            cls._notification_controller.show_notification("Search", f"Searching for: {search_query}",
                                                           addr + "searching_for")
            return True
        return False

    @classmethod
    def control_keyboard(cls, operation: str, addr: str = "") -> bool:
        """Handle keyboard-related commands."""
        if cls._is_typing_active:
            cls._speech_controller.format_speech("typing", operation, addr + "typing_text")
            type_text(operation, addr + "type_text_action")
            return True

        op_parts = operation.split()
        command_verb = op_parts[0]
        keys_to_action = [k for k in op_parts[1:] if k not in ["key", "keys"]]

        if not keys_to_action and command_verb in (cls.press_key_cmds + cls.hold_key_cmds + cls.release_key_cmds):
            cls._speech_controller.speak(f"Please specify which key to {command_verb}.", addr + "keyboard_ask_keys")
            cls._notification_controller.show_notification("Keyboard", f"Specify key for {command_verb}",
                                                           addr + "keyboard_ask_keys")
            return True

        if command_verb in cls.hold_key_cmds and keys_to_action:
            cls._speech_controller.format_speech("holding", " ".join(keys_to_action), addr + "holding_keys")
            hold_key(keys_to_action, addr + "hold_key_action")
            return True
        elif command_verb in cls.release_key_cmds and keys_to_action:
            cls._speech_controller.format_speech("releasing", " ".join(keys_to_action), addr + "releasing_keys")
            release_key(keys_to_action, addr + "release_key_action")
            return True
        elif command_verb in cls.press_key_cmds and keys_to_action:
            cls._speech_controller.format_speech("pressing", " ".join(keys_to_action), addr + "pressing_keys")
            press_key(keys_to_action, addr + "press_key_action")
            return True
        return False

    @classmethod
    def control_app_opening(cls, operation: str, addr: str = "") -> bool:
        """Handle application opening commands."""
        op_parts = operation.split()
        command_verb = op_parts[0]
        if command_verb in cls.open_app_cmds:
            app_name_query = " ".join(op_parts[1:])
            if not app_name_query:
                cls._speech_controller.format_speech("ask_app", "open", addr + "open_ask_app")
                cls._notification_controller.show_notification("Open App", "Which application to open?",
                                                               addr + "open_ask_app")
                return True

            cls._speech_controller.format_speech("trying_to_open", app_name_query, addr + "trying_to_open")
            success = open_application(app_name_query=app_name_query, addr=addr + "AM.open_app")
            if success:
                cls._speech_controller.format_speech("opening", app_name_query, addr + "open_success_speak")
                cls._notification_controller.show_notification("Open App", f"Opened {app_name_query}",
                                                               addr + "open_success")
            else:
                cls._speech_controller.format_speech("open_fail_trying_search", app_name_query,
                                                     addr + "open_fail_trying_search")
                if DesktopSystemController.open_apps_by_windows_search(operation, addr + "DSC.open_by_search"):
                    cls._speech_controller.format_speech("opening", app_name_query,
                                                         addr + "open_search_fallback_success")
                    cls._notification_controller.show_notification("Open App",
                                                                   f"Opened {app_name_query} via Windows Search",
                                                                   addr + "open_search_success")
                else:
                    cls._speech_controller.format_speech("open_search_fallback_fail", app_name_query,
                                                         addr + "open_search_fallback_fail")
                    cls._notification_controller.show_notification("Error", f"Failed to open {app_name_query}",
                                                                   addr + "open_search_fail")
            return True
        return False

    @classmethod
    def control_app_closing(cls, operation: str, addr: str = "") -> bool:
        """Handle application closing commands."""
        op_parts = operation.split()
        command_verb = op_parts[0]
        if command_verb in cls.close_app_cmds:
            app_name_query = " ".join(op_parts[1:])
            if not app_name_query:
                cls._speech_controller.format_speech("ask_app", command_verb, addr + "close_ask_app")
                cls._notification_controller.show_notification("Close App", f"Which application to {command_verb}?",
                                                               addr + "close_ask_app")
                return True

            cls._speech_controller.format_speech("trying_to_close", app_name_query, addr + "trying_to_close")
            success = close_application(app_name_query=app_name_query, addr=addr + "AM.close_app")
            if success:
                cls._speech_controller.format_speech("closing", app_name_query, addr + "close_success_speak")
                cls._notification_controller.show_notification("Close App", f"Closed {app_name_query}",
                                                               addr + "close_success")
            else:
                cls._speech_controller.format_speech("close_fail", app_name_query, addr + "close_fail_speak")
                cls._notification_controller.show_notification("Error", f"Failed to close {app_name_query}",
                                                               addr + "close_fail")
            return True
        return False

    @classmethod
    def control_opened_windows(cls, operation: str, addr: str = "") -> bool:
        """Handle commands for locked windows (e.g., settings)."""
        if cls._lock_opened_windows:
            cls._speech_controller.format_speech("locked_window_action", operation, addr + "locked_window_action")
            SettingWindows(operation, addr + "SettingWindows_action")
            cls._notification_controller.show_notification("Settings", f"Performed: {operation}",
                                                           addr + "locked_window_action")
            return True
        return False

    @classmethod
    def controlling_active_window(cls, operation: str, addr: str = "") -> bool:
        """Handle window control commands."""
        result = MainActivationWindows(operation, addr + "WinSysCtrl.MainActivation")
        if result:
            cls._speech_controller.speak(f"Executed window command: {operation}", addr + "window_success")
            cls._notification_controller.show_notification("Window", f"Executed: {operation}", addr + "window_success")
        else:
            cls._speech_controller.speak(f"Failed to execute window command: {operation}", addr + "window_fail")
            cls._notification_controller.show_notification("Error", f"Failed: {operation}", addr + "window_fail")
        return result

    @classmethod
    def listen_and_process(cls, addr: str = "") -> bool:
        """Listen for a voice command and process it."""
        if not cls._voice_processor:
            cls.initialize()
        return cls._voice_processor.listen_and_process(addr + "voice_processor")

    @classmethod
    def shutdown(cls) -> None:
        """Shutdown controllers."""
        if cls._speech_controller:
            cls._speech_controller.shutdown()
        logging.info("UserCommandProcessor shutdown")


def main():
    """Main function to test command processing."""
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    UserCommandProcessor.initialize()

    try:
        # Test predefined commands
        commands = [
            "hi jarvis",
            "set brightness to 100",
            "increase volume by 40",
            "switch windows",
            "minimize all windows",
            "open notepad",
            "press enter",
            "rescan apps",
            "open settings",
            "close settings"
        ]
        for cmd in commands:
            result = UserCommandProcessor.main_activation(cmd, "main")
            print(f"Command '{cmd}' result: {result}")

        # Test voice input
        print("Starting voice command listener...")
        result = UserCommandProcessor.listen_and_process("voice")
        print(f"Voice command result: {result}")

    finally:
        UserCommandProcessor.shutdown()


if __name__ == "__main__":
    main()
