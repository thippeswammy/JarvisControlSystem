import os
from Jarvis.Data.JSON_Information_Center import loadDate
from Jarvis.KeyboardAutomationController import hold_key, press_key, release_key, type_text
from Jarvis.ApplicationManager import open_application, close_application # Using updated functions
from Jarvis.WindowsFeature import WINDOWS_SystemController
from Jarvis.WindowsDefaultApps.settingControlApp import SettingControlAccess as SettingWindows
from Jarvis.SpeechRecognition import (
    ClosingSpeaker, OpeningSpeaker, PressingSpeaker, Speaker,
    TypingSpeaker, holdingSpeaker, releasingSpeaker
)
from Jarvis.SystemFilePathScanner import GetAllFilePath # For re-scanning applications

class UserCommandProcessor:
    _is_desktop_mode: bool = False
    _is_jarvis_active: bool = False
    _is_typing_active: bool = False
    _lock_opened_windows: bool = False # Used for specific control over settings window
    _open_by_windows_search: bool = False # This flag's relevance might change with improved app opening
    _delay: int = 3

    # Path to the JSON data file. Consider making this path more robust.
    # (e.g., relative to this file's location or an absolute path from config)
    FILE_DATA_PATH = os.path.join(os.path.dirname(__file__), 'Data', 'Data_Information_Value', 'Data1.json')

    # Load command data from JSON. This is done once at class definition.
    # If Data1.json can change during runtime and needs to be reloaded, this strategy would need adjustment.
    try:
        DATA = loadDate(FILE_DATA_PATH)
        if DATA is None or not isinstance(DATA, dict):
            # print(f"Warning: Data from {FILE_DATA_PATH} is None or not a dict. Using empty data.")
            DATA = {}
    except Exception as e:
        # print(f"Critical Error: Could not load data from {FILE_DATA_PATH}: {e}. Using empty data.")
        DATA = {}

    # Define command lists, fetching from DATA or using defaults
    activating_jarvis_cmds: list = DATA.get('activating_jarvis', ['hi', 'hi jarvis', 'jarvis', 'start jarvis', 'jarvis start'])
    deactivating_jarvis_cmds: list = DATA.get('deactivating_jarvis', ['jarvis close', 'close jarvis', 'jarvis stop', 'stop jarvis'])
    typing_start_cmds: list = DATA.get('typing_jarvies', ['start typing', 'typing start', 'activate typing', 'typing activate'])
    typing_stop_cmds: list = DATA.get('stop_typing_jarvies', ['stop typing', 'typing stop', 'deactivate typing', 'typing deactivate'])
    press_key_cmds: list = DATA.get('presskey_jarvis1', ['press', 'press key', 'key press'])
    hold_key_cmds: list = DATA.get('holdkey_jarvis', ['hold', 'holdkey', 'hold key', 'keydown'])
    release_key_cmds: list = DATA.get('relasekey_jarvis', ['release', 'releasekey', 'release key']) # Note: 'relasekey_jarvis' might be a typo in JSON
    open_app_cmds: list = DATA.get('OpenApp_jarvis', ['open', 'start', 'run', 'launch']) # Added 'launch'
    close_app_cmds: list = DATA.get('CloseApp_jarvis', ['close', 'exit', 'terminate', 'quit']) # Added 'quit'
    search_cmds: list = DATA.get('SearchApp_jarvis', ['search', 'find', 'windows search', 'window search']) # Simplified some defaults
    windows_search_enable_cmds: list = DATA.get('WindowsSearchBarAccess_jarvis', ['open by search', 'open by windows search'])
    windows_search_disable_cmds: list = DATA.get('closeByWindows_jarvis', ['stop by search', 'stop by windows search'])

    # New command list for re-scanning applications
    rescan_apps_cmds: list = DATA.get('rescan_apps_cmds', ['rescan apps', 'refresh apps', 'scan for programs', 'find new apps', 'update app list', 'refresh application list'])

    # Settings-related commands (hardcoded for now, could be moved to JSON)
    open_settings_cmds: list = ['open settings', 'open setting']
    close_settings_cmds: list = ['close settings', 'close setting']


    @classmethod
    def main_activation(cls, operation: str, addr: str = "") -> bool:
        if not cls._is_jarvis_active and operation.lower().strip() not in cls.activating_jarvis_cmds:
            # Speaker("Jarvis is not active. Say 'Hi Jarvis' to activate.", addr + "inactive_prompt") # Optional feedback
            return False # Jarvis must be active for most commands

        op_lower_stripped = operation.lower().strip()

        if op_lower_stripped in cls.activating_jarvis_cmds:
            if not cls._is_jarvis_active: # Only activate if not already active
                cls._is_jarvis_active = True
                Speaker("Jarvis activated.", addr + "jarvis_activated")
            else:
                Speaker("Jarvis is already active.", addr + "jarvis_already_active")
            return True
        elif op_lower_stripped in cls.deactivating_jarvis_cmds:
            cls._is_jarvis_active = False
            Speaker("Jarvis deactivated.", addr + "jarvis_deactivated")
            return True # Deactivation is a primary command

        # Other primary commands (can be run even if sub_activation might handle parts of them)
        elif op_lower_stripped in cls.typing_start_cmds:
            cls._is_typing_active = True
            Speaker("Typing mode activated.", addr + "typing_on")
            return True
        elif op_lower_stripped in cls.typing_stop_cmds:
            cls._is_typing_active = False
            Speaker("Typing mode deactivated.", addr + "typing_off")
            return True
        elif op_lower_stripped in cls.windows_search_enable_cmds: # This flag's utility should be reviewed
            cls._open_by_windows_search = True
            Speaker("Opening apps via Windows Search is now preferred.", addr + "win_search_on")
            return True
        elif op_lower_stripped in cls.windows_search_disable_cmds:
            cls._open_by_windows_search = False
            Speaker("Opening apps directly is now preferred.", addr + "win_search_off")
            return True
        elif op_lower_stripped in cls.open_settings_cmds:
            cls._lock_opened_windows = True # Signal that a settings-like window is being controlled
            # Actual opening of settings might be handled by sub_activation or a dedicated method
            Speaker("Opening settings.", addr + "open_settings_cmd")
            # This typically calls something like `open_application("settings", ...)`
            # Let sub_activation handle it via control_app_opening if "settings" is an app.
            # Or, it could be a special system call. For now, assume sub_activation.
            return cls.sub_activation(op_lower_stripped, addr + "sub_act_open_settings")
        elif op_lower_stripped in cls.close_settings_cmds or \
             (cls._lock_opened_windows and op_lower_stripped in cls.close_app_cmds): # "close" while settings focused
            # If settings are "locked" (focused), "close" should target settings.
            Speaker("Closing settings.", addr + "close_settings_cmd")
            # Similar to opening, actual closing might be special.
            # For now, assume sub_activation handles it via control_app_closing.
            closed = cls.sub_activation(op_lower_stripped, addr + "sub_act_close_settings")
            cls._lock_opened_windows = False # Unlock after attempting to close settings
            return closed
        elif op_lower_stripped in cls.rescan_apps_cmds:
            Speaker("Starting application scan. This may take a moment.", addr + "rescan_triggered")
            try:
                GetAllFilePath(addr + "rescan_apps_cmd -> GetAllFilePath")
                Speaker("Application scan complete. List updated.", addr + "rescan_complete")
            except Exception as e:
                Speaker("Error during application scan.", addr + "rescan_error")
                # print(f"{addr} GetAllFilePath error: {e}")
            return True
        else: # If not a primary command handled above, pass to sub_activation
            return cls.sub_activation(op_lower_stripped, addr + "sub_act_general")

    @classmethod
    def sub_activation(cls, operation: str, addr: str = "") -> bool: # operation is lowercased & stripped
        # Order of these checks can be important.
        # For example, "open settings" might be caught by control_app_opening if "settings" is treated as a regular app.
        # If settings interaction is special (_lock_opened_windows), control_opened_windows should handle it.

        if cls._lock_opened_windows and cls.control_opened_windows(operation, addr + "control_locked_window"):
            # If in locked mode (e.g. settings), control_opened_windows gets priority for actions.
            return True

        if cls.control_keyboard(operation, addr + "control_keyboard"):
            return True
        # App opening/closing should be fairly high priority after keyboard/locked window
        if cls.control_app_opening(operation, addr + "control_app_opening"):
            return True
        if cls.control_app_closing(operation, addr + "control_app_closing"):
            return True
        # General system interactions
        if cls.control_search(operation, addr + "control_search"): # Windows Search query
            return True
        if cls.controlling_active_window(operation, addr + "control_active_window"): # Minimize, maximize, etc.
            return True

        # If _lock_opened_windows was true but control_opened_windows didn't handle it,
        # it means the command wasn't for the locked window.
        # Fall through to other handlers.
        # print(f"{addr}sub_activation: Operation '{operation}' not handled.")
        return False

    @classmethod
    def control_search(cls, operation: str, addr: str = "") -> bool: # operation is lowercased & stripped
        # This is for initiating a generic Windows Search.
        op_parts = operation.split()
        command_verb = op_parts[0]

        # Check if the command starts with a search verb.
        # Assumes search_cmds are single words like "search", "find".
        if command_verb in cls.search_cmds:
            search_query_parts = op_parts[1:]
            if not search_query_parts:
                Speaker("What would you like to search for?", addr + "search_ask_query")
                return True # Handled by asking

            search_query = " ".join(search_query_parts)
            Speaker(f"Searching Windows for: {search_query}", addr + "searching_for")
            # DesktopSystemController.search_windows_for_term expects the terms to search as a list
            WINDOWS_SystemController.DesktopSystemController.search_windows_for_term(
                search_query_parts, # Pass only the query parts
                addr + "DesktopSearch.search_term"
            )
            return True
        return False

    @classmethod
    def control_keyboard(cls, operation: str, addr: str = "") -> bool: # operation is lowercased & stripped
        if cls._is_typing_active: # If typing mode, all input is typed.
            TypingSpeaker(operation, addr + "typing_text") # Speak what's being typed
            type_text(operation, addr + "type_text_action")
            return True

        op_parts = operation.split()
        command_verb = op_parts[0]
        keys_to_action = op_parts[1:]

        # Clean "key" or "keys" from the list of keys
        keys_to_action = [k for k in keys_to_action if k not in ["key", "keys"]]

        if not keys_to_action and command_verb in (cls.press_key_cmds + cls.hold_key_cmds + cls.release_key_cmds):
            # Speaker(f"Please specify which key(s) to {command_verb}.", addr + "keyboard_ask_keys")
            return True # Handled by asking (or could be False if we expect full commands)

        if command_verb in cls.hold_key_cmds and keys_to_action:
            holdingSpeaker(keys_to_action, addr + "holding_keys")
            hold_key(keys_to_action, addr + "hold_key_action")
            return True
        elif command_verb in cls.release_key_cmds and keys_to_action:
            releasingSpeaker(keys_to_action, addr + "releasing_keys")
            release_key(keys_to_action, addr + "release_key_action")
            return True
        elif command_verb in cls.press_key_cmds and keys_to_action:
            PressingSpeaker(keys_to_action, addr + "pressing_keys")
            press_key(keys_to_action, addr + "press_key_action")
            return True
        return False

    @classmethod
    def control_app_opening(cls, operation: str, addr: str = "") -> bool: # operation is lowercased & stripped
        op_parts = operation.split()
        command_verb = op_parts[0]

        if command_verb in cls.open_app_cmds:
            app_name_query = " ".join(op_parts[1:])
            if not app_name_query:
                Speaker("Which application to open?", addr + "open_ask_app")
                return True

            # Special handling for "settings" if it's meant to use _lock_opened_windows
            if app_name_query == "settings" and operation in cls.open_settings_cmds:
                 # This is already handled by main_activation's _lock_opened_windows logic.
                 # If main_activation sets _lock_opened_windows=True, then control_opened_windows
                 # will take precedence if it can handle "settings" specific actions.
                 # If "settings" is just a regular app to open, it proceeds here.
                 # For now, assume "open settings" could be a generic app open.
                 pass


            Speaker(f"Attempting to open {app_name_query}.", addr + "trying_to_open")

            # Use the updated open_application from ApplicationManager
            # The app_path_override is not used here as we rely on GetFilePath within open_application.
            success = open_application(app_name_query=app_name_query, addr=addr + "AM.open_app")

            if success:
                OpeningSpeaker(app_name_query, addr + "open_success_speak")
            else:
                # Fallback: Try with DesktopSystemController.open_apps_by_windows_search
                # This was part of the original logic if the primary open failed or was via search bar.
                # This provides a fallback if GetFilePath is not exhaustive for some cases.
                # print(f"{addr} open_application failed for '{app_name_query}'. Trying Windows Search fallback...")
                Speaker(f"Could not open {app_name_query} directly. Trying Windows Search.", addr + "open_fail_trying_search")
                if WINDOWS_SystemController.DesktopSystemController.open_apps_by_windows_search(
                    operation, # Pass original operation, as DSC expects it
                    addr + "DSC.open_by_search"
                ):
                    OpeningSpeaker(app_name_query, addr + "open_search_fallback_success") # Generic success speaker
                else:
                    Speaker(f"Sorry, I couldn't open {app_name_query} even with Windows Search.", addr + "open_search_fallback_fail")
            return True # Command was handled (attempted to open)
        return False

    @classmethod
    def control_app_closing(cls, operation: str, addr: str = "") -> bool: # operation is lowercased & stripped
        op_parts = operation.split()
        command_verb = op_parts[0]

        if command_verb in cls.close_app_cmds:
            app_name_query = " ".join(op_parts[1:])
            if not app_name_query:
                # If settings are focused and user just says "close", main_activation handles it.
                # This check is for "close" without app name when settings are NOT focused.
                if operation == "close" and not cls._lock_opened_windows:
                     Speaker("Which application would you like to close?", addr + "close_ask_app")
                     return True
                elif operation != "close": # e.g. "exit" without app name
                     Speaker(f"Which application to {command_verb}?", addr + "close_ask_app_specific_verb")
                     return True
                # If it's just "close" and settings are locked, main_activation should have caught it.
                # If it reaches here, it means "close" was said but not for settings.
                return False


            Speaker(f"Attempting to close {app_name_query}.", addr + "trying_to_close")

            # Use the updated close_application from ApplicationManager (which is a dispatcher)
            success = close_application(app_name_query=app_name_query, addr=addr + "AM.close_app")

            if success:
                ClosingSpeaker(app_name_query, addr + "close_success_speak")
            else:
                Speaker(f"Could not close {app_name_query}, or it was not running.", addr + "close_fail_speak")
            return True # Command was handled (attempted to close)
        return False

    @classmethod
    def control_opened_windows(cls, operation: str, addr: str = "") -> bool: # operation is lowercased & stripped
        # This method is for specific interactions when _lock_opened_windows is True (e.g., settings).
        if cls._lock_opened_windows:
            # Pass the operation to SettingControlAccess, which knows how to interact with settings.
            # print(f"{addr} Locked window mode: Passing '{operation}' to SettingWindows.")
            SettingWindows(operation, addr + 'SettingWindows_action') # SettingControlAccess instance call
            Speaker(f"Performed '{operation}' in the current window context.", addr + "locked_window_action_speak")
            # Note: main_activation handles unsetting _lock_opened_windows if 'close settings' or 'close' is issued.
            return True
        return False

    @staticmethod
    def controlling_active_window(operation: str, addr: str = "") -> bool: # operation is lowercased & stripped
        # For general window manipulations: minimize, maximize, switch, etc.
        # print(f"{addr} Passing '{operation}' to MainActivationWindows for active window control.")
        return WINDOWS_SystemController.MainActivationWindows(operation, addr + "WinSysCtrl.MainActivation")
