import os
import re
import wmi
import time
import logging
import pyautogui
import pygetwindow as gw
from comtypes import CLSCTX_ALL
from ctypes import cast, POINTER
from difflib import get_close_matches
from typing import List, Union, Optional, Dict, Tuple
from Jarvis.KeyboardAutomationController import press_key
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AppManager:
    """Manages application data loading and matching"""
    _app_data: Optional[Tuple[List[str], List[str]]] = None
    _last_loaded: float = 0
    DATA_REFRESH_INTERVAL = 300  # 5 minutes

    @classmethod
    def load_app_data(cls, file_path: str) -> None:
        """Load application data from Excel with caching and periodic refresh"""
        current_time = time.time()
        if (cls._app_data is None or
                current_time - cls._last_loaded > cls.DATA_REFRESH_INTERVAL):

            try:
                import openpyxl
                wb = openpyxl.load_workbook(file_path)
                sheet = wb.active

                app_names = []
                addresses = []

                for row in sheet.iter_rows(min_row=2, values_only=True):
                    # Only take first two non-empty values
                    if row and len(row) >= 2 and row[0] and row[1]:
                        app_names.append(str(row[0]).strip())
                        addresses.append(str(row[1]).strip())

                if not app_names:
                    raise ValueError("No valid data found in Excel file.")

                cls._app_data = (app_names, addresses)
                cls._last_loaded = current_time
                logger.info("Application data loaded successfully")
            except Exception as e:
                logger.error(f"Error loading app data: {e}")
                if cls._app_data is None:
                    raise

    @classmethod
    def get_app_data(cls) -> Tuple[List[str], List[str]]:
        """Get application data, loading if necessary"""
        if cls._app_data is None:
            raise RuntimeError("App data not loaded. Call load_app_data first.")
        return cls._app_data

    @classmethod
    def find_best_app_matches(cls, term: str, n: int = 1) -> Tuple[List[str], List[str]]:
        """Find closest matches for application names"""
        if cls._app_data is None:
            cls.load_app_data()

        app_names, addresses = cls.get_app_data()
        matches = get_close_matches(term, app_names, n=n, cutoff=0.6)
        match_addresses = [
            addresses[app_names.index(match)]
            for match in matches
            if match in app_names
        ]
        return matches, match_addresses


class SystemCommandHandler:
    """Base class for command handling with common utilities"""
    WORD_REPLACEMENTS = {
        "light": "brightness",
        "window": "windows",
        "sound": "volume",
        "reduce": "decrease",
        "shifting": "shift",
        "adjust": "change"
    }

    @staticmethod
    def replace_words(sentence: str) -> str:
        """Normalize words in command strings"""
        words = sentence.split()
        return ' '.join(
            SystemCommandHandler.WORD_REPLACEMENTS.get(word, word)
            for word in words
        )

    @staticmethod
    def extract_numbers(text: str) -> List[int]:
        """Extract all integers from text"""
        numbers = re.findall(r'\d+', text)
        return [int(num) for num in numbers] if numbers else [10]


class DesktopSystemController(SystemCommandHandler):
    """Handles system-level operations like brightness and volume control"""
    COMMAND_MAP = {
        "set brightness": {
            'phrases': [
                'set brightness level', 'set brightness to', 'set brightness',
                'change brightness in windows', 'brightness level',
                'brightness to level', 'set brightness to level'
            ],
            'handler': 'handle_brightness_set'
        },
        "adjust brightness": {
            'phrases': [
                'increase brightness', 'increase brightness level',
                'decrease brightness', 'decrease brightness level'
            ],
            'handler': 'handle_brightness_adjust'
        },
        "set volume": {
            'phrases': [
                'set volume level', 'set volume to', 'set volume',
                'change volume in windows', 'adjust volume', 'reduce volume'
            ],
            'handler': 'handle_volume_set'
        },
        "adjust volume": {
            'phrases': [
                'increase volume', 'increase volume level',
                'decrease volume', 'decrease volume level'
            ],
            'handler': 'handle_volume_adjust'
        }
    }

    @staticmethod
    def set_brightness(level: int) -> bool:
        """Set screen brightness (0-100)"""
        try:
            level = max(0, min(100, level))
            c = wmi.WMI(namespace='wmi')
            methods = c.WmiMonitorBrightnessMethods()[0]
            methods.WmiSetBrightness(level, 0)
            logger.info(f"Brightness set to {level}%")
            return True
        except Exception as e:
            logger.error(f"Brightness set failed: {e}")
            return False

    @staticmethod
    def get_brightness() -> int:
        """Get current brightness level (0-100)"""
        try:
            w = wmi.WMI(namespace='wmi')
            return w.WmiMonitorBrightness()[0].CurrentBrightness
        except Exception as e:
            logger.error(f"Brightness get failed: {e}")
            return 50  # Default value

    @staticmethod
    def set_volume(level: int) -> bool:
        """Set system volume (0-100)"""
        try:
            level = max(0, min(100, level)) / 100.0
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(
                IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMasterVolumeLevelScalar(level, None)
            logger.info(f"Volume set to {int(level * 100)}%")
            return True
        except Exception as e:
            logger.error(f"Volume set failed: {e}")
            return False

    @staticmethod
    def get_volume() -> int:
        """Get current volume level (0-100)"""
        try:
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(
                IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            return int(volume.GetMasterVolumeLevelScalar() * 100)
        except Exception as e:
            logger.error(f"Volume get failed: {e}")
            return 50  # Default value

    @classmethod
    def handle_brightness_set(cls, operation: str) -> bool:
        """Handle brightness set commands"""
        numbers = cls.extract_numbers(operation)
        level = numbers[0] if numbers else cls.get_brightness()
        return cls.set_brightness(level)

    @classmethod
    def handle_brightness_adjust(cls, operation: str) -> bool:
        """Handle brightness increase/decrease commands"""
        current = cls.get_brightness()
        numbers = cls.extract_numbers(operation)
        delta = numbers[0] if numbers else 10

        if "increase" in operation:
            new_level = min(100, current + delta)
        else:  # decrease
            new_level = max(0, current - delta)

        return cls.set_brightness(new_level)

    @classmethod
    def handle_volume_set(cls, operation: str) -> bool:
        """Handle volume set commands"""
        numbers = cls.extract_numbers(operation)
        level = numbers[0] if numbers else cls.get_volume()
        return cls.set_volume(level)

    @classmethod
    def handle_volume_adjust(cls, operation: str) -> bool:
        """Handle volume increase/decrease commands"""
        current = cls.get_volume()
        numbers = cls.extract_numbers(operation)
        delta = numbers[0] if numbers else 10

        if "increase" in operation:
            new_level = min(100, current + delta)
        else:  # decrease
            new_level = max(0, current - delta)

        return cls.set_volume(new_level)

    @classmethod
    def execute_command(cls, operation: str) -> bool:
        """Execute system command based on normalized operation string"""
        normalized = cls.replace_words(operation.lower())

        for _, command_info in cls.COMMAND_MAP.items():
            for phrase in command_info['phrases']:
                if phrase in normalized:
                    handler = getattr(cls, command_info['handler'])
                    return handler(normalized)
        return False


class WindowsAppController(SystemCommandHandler):
    """Manages window operations like minimize/maximize/close"""
    COMMAND_MAP = {
        'minimize': {
            'phrases': [
                'minimize window', 'minimize windows', 'minimize active window',
                'minimize active windows', 'minimize opened window', 'minimize opened windows',
                'minimise window', 'minimise windows', 'minimise active window',
                'minimise active windows', 'minimise opened window', 'minimise opened windows'
            ],
            'handler': 'minimize_window'
        },
        'minimize_all': {
            'phrases': [
                'minimize all windows', 'minimize all window',
                'minimise all windows', 'minimise all window'
            ],
            'handler': 'minimize_all_windows'
        },
        'maximize': {
            'phrases': [
                'maximize window', 'maximize windows', 'maximize active window',
                'maximize active windows', 'maximize opened window', 'maximize opened windows',
                'maximise window', 'maximise windows', 'maximise active window',
                'maximise active windows', 'maximise opened window', 'maximise opened windows',
                'full window', 'full windows', 'full screen', 'full screen window', 'full screen windows'
            ],
            'handler': 'maximize_window'
        },
        'maximize_all': {
            'phrases': [
                'maximize all windows', 'maximize all window',
                'maximise all windows', 'maximise all window',
                'all full screen windows', 'all full screen window'
            ],
            'handler': 'maximize_all_windows'
        },
        'close': {
            'phrases': [
                'close window', 'close windows', 'close present window', 'close present windows',
                'close active window', 'close active windows', 'close opened window', 'close opened windows'
            ],
            'handler': 'close_window'
        },
        'close_all': {
            'phrases': ['close all windows', 'close all window'],
            'handler': 'close_all_windows'
        },
        'shift': {
            'phrases': [
                'shift window', 'shift windows', 'next window', 'next windows', 'goto next window',
                'goto next windows', 'to next window', 'to next windows', 'switch window',
                'switch windows', 'switch to next window', 'switch to next windows'
            ],
            'handler': 'switch_windows'
        },
        'move_left': {
            'phrases': [
                'move window left', 'move windows left', 'move window to left', 'move windows to left',
                'move to left', 'snap left', 'window left', 'move left', 'left window'
            ],
            'handler': 'move_window_to_left'
        },
        'move_right': {
            'phrases': [
                'move window right', 'move windows right', 'move window to right', 'move windows to right',
                'move to right', 'snap right', 'window right', 'move right', 'right window'
            ],
            'handler': 'move_window_to_right'
        }
    }

    @staticmethod
    def get_active_window() -> Optional[gw.Window]:
        """Get currently active window"""
        try:
            return gw.getActiveWindow()
        except Exception:
            logger.warning("No active window found")
            return None

    @staticmethod
    def get_visible_windows() -> List[gw.Window]:
        """Get all visible non-empty windows"""
        try:
            return [
                win for win in gw.getAllWindows()
                if win.visible and win.title
            ]
        except Exception as e:
            logger.error(f"Error getting windows: {e}")
            return []

    @staticmethod
    def minimize_window(window: Optional[gw.Window] = None) -> bool:
        """Minimize specified or active window"""
        win = window or WindowsAppController.get_active_window()
        if not win:
            return False
        try:
            win.minimize()
            return True
        except Exception as e:
            logger.error(f"Minimize failed: {e}")
            return False

    @staticmethod
    def maximize_window(window: Optional[gw.Window] = None) -> bool:
        """Maximize specified or active window"""
        win = window or WindowsAppController.get_active_window()
        if not win:
            return False
        try:
            if win.isMinimized:
                win.restore()
            if not win.isMaximized:
                win.maximize()
            return True
        except Exception as e:
            logger.error(f"Maximize failed: {e}")
            return False

    @staticmethod
    def close_window(window: Optional[gw.Window] = None) -> bool:
        """Close specified or active window"""
        win = window or WindowsAppController.get_active_window()
        if not win:
            return False
        try:
            win.close()
            return True
        except Exception as e:
            logger.error(f"Close failed: {e}")
            return False

    @staticmethod
    def activate_window(window: gw.Window) -> bool:
        """Activate and bring window to foreground"""
        try:
            # First try standard activation
            window.activate()

            # Verify activation
            time.sleep(0.5)
            active = gw.getActiveWindow()
            if active and active.title == window.title:
                return True

            # If verification failed, try alternative method
            logger.warning("Standard activation failed, trying alt method")
            if window.isMinimized:
                window.restore()
            window.maximize()
            time.sleep(0.1)
            window.minimize()
            time.sleep(0.1)
            window.restore()
            window.activate()

            # Final verification
            time.sleep(0.5)
            active = gw.getActiveWindow()
            return active and active.title == window.title
        except Exception as e:
            # Check if the error message indicates success
            if "0" in str(e) and "success" in str(e).lower():
                logger.info(f"Ignoring benign activation error: {e}")
                return True
            logger.error(f"Activation failed: {e}")
            return False

    @classmethod
    def minimize_all_windows(cls) -> bool:
        """Minimize all visible windows"""
        success = True
        for win in cls.get_visible_windows():
            if not cls.minimize_window(win):
                success = False
        return success

    @classmethod
    def maximize_all_windows(cls) -> bool:
        """Maximize all visible windows"""
        success = True
        for win in cls.get_visible_windows():
            if not cls.maximize_window(win):
                success = False
        return success

    @classmethod
    def close_all_windows(cls) -> bool:
        """Close all visible windows"""
        success = True
        for win in cls.get_visible_windows():
            if not cls.close_window(win):
                success = False
        return success

    @staticmethod
    def move_window_to_left() -> bool:
        """Move active window to left half of screen"""
        try:
            pyautogui.hotkey("win", "left")
            time.sleep(0.5)  # Allow time for animation
            return True
        except Exception as e:
            logger.error(f"Move left failed: {e}")
            return False

    @staticmethod
    def move_window_to_right() -> bool:
        """Move active window to right half of screen"""
        try:
            pyautogui.hotkey("win", "right")
            time.sleep(0.5)  # Allow time for animation
            return True
        except Exception as e:
            logger.error(f"Move right failed: {e}")
            return False

    @classmethod
    def switch_windows(cls) -> bool:
        """Switch focus to next window in rotation"""
        windows = cls.get_visible_windows()
        if not windows:
            return False

        active = cls.get_active_window()
        if not active:
            return cls.activate_window(windows[0])

        if active in windows:
            current_idx = windows.index(active)
            next_idx = (current_idx + 1) % len(windows)
        else:
            next_idx = 0

        logger.info(f"Switching from window {current_idx} to {next_idx}")
        return cls.activate_window(windows[next_idx])

    @classmethod
    def execute_command(cls, operation: str) -> bool:
        """Execute window command based on normalized operation string"""
        normalized = cls.replace_words(operation.lower().strip())
        logger.debug(f"Processing command: {normalized}")

        # Check both original and normalized phrases
        for _, command_info in cls.COMMAND_MAP.items():
            for phrase in command_info['phrases']:
                # Check if phrase matches normalized command
                if phrase in normalized:
                    logger.info(f"Matched command: {phrase}")
                    handler = getattr(cls, command_info['handler'])
                    return handler()

                # Also check without word replacement for close commands
                if "close" in phrase and phrase in operation.lower():
                    logger.info(f"Matched original command: {phrase}")
                    handler = getattr(cls, command_info['handler'])
                    return handler()

        logger.warning(f"No handler found for: {operation}")
        return False


def MainActivationWindows(operation: Union[str, List[str]], addr: str = "") -> bool:
    """Main entry point for desktop/window operations"""
    # Normalize input
    if isinstance(operation, list):
        operation = " ".join(operation)
    original_operation = operation
    operation = operation.lower().strip()

    logger.info(f"Processing operation: {original_operation}")

    # Execute system commands
    if DesktopSystemController.execute_command(operation):
        return True

    # Execute window commands with original operation for close commands
    result = WindowsAppController.execute_command(operation)
    if not result and "close" in operation:
        # Retry with original operation if close command failed
        result = WindowsAppController.execute_command(original_operation)

    if result:
        return True

    logger.warning(f"No handler found for: {original_operation}")
    return False


# Initialization
if __name__ == "__main__":
    try:
        # Enable debug logging for troubleshooting
        logger.setLevel(logging.DEBUG)

        AppManager.load_app_data(
            "F:/RunningProjects/JarvisControlSystem/Jarvis/Data/Data_Information_Value/AppNameList.xlsx"
        )
        logger.info("System initialized successfully")

        # Test commands
        test_commands = [
            "set brightness 50",
            "increase volume",
            "next window",
            "move window left",
            "close window",
            "close windows"
        ]
        time.sleep(10)
        for cmd in test_commands:
            logger.info(f"Testing command: {cmd}")
            result = MainActivationWindows(cmd)
            logger.info(f"Result: {'Success' if result else 'Failed'}")
            time.sleep(1)

    except Exception as e:
        logger.error(f"Initialization failed: {e}")