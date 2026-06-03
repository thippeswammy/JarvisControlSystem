"""
Dynamic Application Pathfinder
=============================
Autonomously discovers installed applications on the Windows operating system
without relying on hardcoded dictionaries.
Uses registry key analysis, Start Menu shortcut resolution (.lnk), and PATH scans.
"""

import json
import logging
import os
import re
import shutil
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_MAPPING_FILE = Path(__file__).resolve().parent.parent / "config" / "app_mappings.json"

class AppFinder:
    """Discovers application executable paths dynamically on Windows."""

    @staticmethod
    def register_mapping(app_name: str, path_or_uri: str) -> bool:
        """Register a new mapping dynamically and save it to config."""
        app_clean = app_name.strip().lower()
        if not app_clean or not path_or_uri:
            return False
            
        mappings = {}
        _MAPPING_FILE.parent.mkdir(parents=True, exist_ok=True)
        if _MAPPING_FILE.exists():
            try:
                with open(_MAPPING_FILE, "r", encoding="utf-8") as f:
                    mappings = json.load(f)
            except Exception:
                pass
                
        mappings[app_clean] = path_or_uri
        
        try:
            with open(_MAPPING_FILE, "w", encoding="utf-8") as f:
                json.dump(mappings, f, indent=4)
            logger.info(f"[AppFinder] Registered custom mapping: {app_clean} -> {path_or_uri}")
            return True
        except Exception as e:
            logger.error(f"[AppFinder] Failed to save app_mappings.json: {e}")
            return False

    @staticmethod
    def find_exe_path(app_name: str) -> Optional[str]:
        """
        Dynamically locate the target application's executable path.
        Checks Registry, Start Menu Shortcuts, and system PATH in order.
        """
        app_clean = app_name.strip().lower()
        if not app_clean:
            return None

        # 0. High-Priority Direct Path/Protocol Checks (trusting direct LLM input)
        expanded = os.path.expandvars(app_name).strip()
        if os.path.exists(expanded) and os.path.isfile(expanded):
            logger.info(f"[AppFinder] Direct file path exists, using immediately: {expanded}")
            return os.path.abspath(expanded)

        # Check for deep-links/protocols (e.g. ms-settings:wifi, custom URI schemes)
        # URI protocols usually contain ':' but do not have ':' at index 1 (which indicates a Windows drive letter like C:)
        if ":" in app_clean and not (len(app_clean) > 1 and app_clean[1] == ":"):
            logger.info(f"[AppFinder] Detected URI/protocol scheme: {app_name}")
            return app_name


        # Ensure we check variations (e.g. "word" -> "winword", "brave" -> "brave.exe")
        variations = [app_clean]
        if not app_clean.endswith(".exe"):
            variations.append(f"{app_clean}.exe")

        # Load dynamic mappings from config file
        mappings = {}
        if _MAPPING_FILE.exists():
            try:
                with open(_MAPPING_FILE, "r", encoding="utf-8") as f:
                    mappings = json.load(f)
            except Exception as e:
                logger.error(f"[AppFinder] Failed to load app_mappings.json: {e}")

        # Check mapping for app name
        if app_clean in mappings:
            mapped_val = mappings[app_clean]
            # If it's a deep link or URI, return it directly
            if ":" in mapped_val and not (len(mapped_val) > 1 and mapped_val[1] == ":"):
                return mapped_val
            # Otherwise, add it to variations to search for it
            if mapped_val not in variations:
                variations.append(mapped_val)

        # 1. Try Registry App Paths
        for var in variations:
            path = AppFinder._check_registry_app_path(var)
            if path and os.path.exists(path):
                logger.info(f"[AppFinder] Discovered {app_name} via Registry: {path}")
                return path

        # 2. Try Start Menu Shortcut (.lnk) scans
        for var in variations:
            clean_var = var.replace(".exe", "")
            path = AppFinder._scan_start_menu_shortcuts(clean_var)
            if path and os.path.exists(path):
                logger.info(f"[AppFinder] Discovered {app_name} via Start Menu: {path}")
                return path

        # 3. Try standard system PATH
        for var in variations:
            path = shutil.which(var)
            if path:
                logger.info(f"[AppFinder] Discovered {app_name} via PATH: {path}")
                return path

        # 4. Try standard directory fallbacks
        dirs = [
            os.path.expandvars(r"%PROGRAMFILES%"),
            os.path.expandvars(r"%PROGRAMFILES(X86)%"),
            os.path.expandvars(r"%LOCALAPPDATA%"),
        ]
        for d in dirs:
            if not os.path.exists(d):
                continue
            for var in variations:
                # Walk depth=3 to keep it fast and prevent massive timeouts
                for pattern in [f"{var}", f"*/{var}", f"*/*/{var}", f"*/*/*/{var}"]:
                    for path in Path(d).glob(pattern):
                        if path.is_file():
                            p_str = str(path.resolve())
                            logger.info(f"[AppFinder] Discovered {app_name} via dir scan: {p_str}")
                            return p_str

        logger.warning(f"[AppFinder] Could not discover path for application: {app_name}")
        return None

    @staticmethod
    def _check_registry_app_path(exe_name: str) -> Optional[str]:
        try:
            import winreg
        except ImportError:
            return None

        keys = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\App Paths"),
        ]

        for root, subkey in keys:
            try:
                # We need the key to end with .exe for Windows App Paths
                name = exe_name if exe_name.endswith(".exe") else f"{exe_name}.exe"
                full_key = f"{subkey}\\{name}"
                with winreg.OpenKey(root, full_key) as key:
                    path, _ = winreg.QueryValueEx(key, "")
                    if path:
                        # Clean quotes or outer spaces
                        path_clean = path.strip('"').strip()
                        if os.path.exists(path_clean):
                            return path_clean
            except OSError:
                continue
        return None

    @staticmethod
    def _scan_start_menu_shortcuts(app_label: str) -> Optional[str]:
        """Scans standard Start Menu folders and resolves matching .lnk targets."""
        folders = [
            os.path.expandvars(r"%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs"),
            os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
        ]
        
        for folder in folders:
            if not os.path.exists(folder):
                continue
            
            # Simple match pattern
            pattern = re.compile(rf".*{re.escape(app_label)}.*", re.IGNORECASE)
            for root, _, files in os.walk(folder):
                for file in files:
                    if file.lower().endswith(".lnk") and pattern.match(file):
                        full_path = os.path.join(root, file)
                        resolved = AppFinder._resolve_shortcut(full_path)
                        if resolved and os.path.exists(resolved) and resolved.lower().endswith(".exe"):
                            return resolved
        return None

    @staticmethod
    def _resolve_shortcut(shortcut_path: str) -> Optional[str]:
        try:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(shortcut_path)
            return shortcut.Targetpath
        except Exception:
            return None
