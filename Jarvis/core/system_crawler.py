"""
Jarvis System Crawler
=====================
Recursively scans the local system (Start Menu, Settings, Project Dirs)
to find paths and creates direct-execution memory recipes.
"""
import logging
import os
import subprocess
import threading
from typing import Dict

from Jarvis.core.jarvis_memory import MemoryManager

logger = logging.getLogger(__name__)

class SystemCrawler:
    def __init__(self, memory_manager: MemoryManager):
        self._memory = memory_manager

    def scan_all_async(self):
        """Run all scans in the background."""
        thread = threading.Thread(target=self._run_all, daemon=True, name="SystemCrawler")
        thread.start()

    def _run_all(self):
        logger.info("[Crawler] Starting system scan...")
        apps_found = {}
        
        apps_found.update(self.find_start_menu_apps())
        apps_found.update(self.find_settings_uris())
        apps_found.update(self.scan_project_directory(r"F:\RunningProjects\JarvisControlSystem"))
        
        if apps_found:
            self._memory.batch_save_apps(apps_dict=apps_found)
            logger.info(f"[Crawler] Scan complete. Found {len(apps_found)} direct execution targets.")

    def find_start_menu_apps(self) -> Dict[str, str]:
        """Scans the Start Menu for .lnk files and resolves their targets using PowerShell."""
        results = {}
        ps_script = r'''
        $paths = @(
            "$env:ProgramData\Microsoft\Windows\Start Menu\Programs",
            "$env:APPDATA\Microsoft\Windows\Start Menu\Programs"
        )
        $sh = New-Object -ComObject WScript.Shell
        Get-ChildItem -Path $paths -Recurse -Filter "*.lnk" -ErrorAction SilentlyContinue | ForEach-Object {
            $link = $sh.CreateShortcut($_.FullName)
            if ($link.TargetPath -match "\.(exe|bat|cmd)$") {
                Write-Output ($_.BaseName + "|" + $link.TargetPath)
            }
        }
        '''
        try:
            output = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", ps_script],
                text=True, 
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            for line in output.splitlines():
                if "|" in line:
                    name, target = line.split("|", 1)
                    results[name.strip()] = target.strip()
        except Exception as e:
            logger.error(f"[Crawler] Start menu scan failed: {e}")
        return results

    def find_settings_uris(self) -> Dict[str, str]:
        """Returns known Windows 11 ms-settings URIs."""
        # A static map is fastest and most reliable for ms-settings
        return {
            "Settings System": "ms-settings:system",
            "Settings Display": "ms-settings:display",
            "Settings Sound": "ms-settings:sound",
            "Settings Notifications": "ms-settings:notifications",
            "Settings Power": "ms-settings:powersleep",
            "Settings Bluetooth": "ms-settings:bluetooth",
            "Settings Network": "ms-settings:network",
            "Settings Wifi": "ms-settings:network-wifi",
            "Settings Personalization": "ms-settings:personalization",
            "Settings Apps": "ms-settings:appsfeatures",
            "Settings Accounts": "ms-settings:accounts",
            "Settings Time": "ms-settings:dateandtime",
            "Settings Gaming": "ms-settings:gaming",
            "Settings Accessibility": "ms-settings:easeofaccess",
            "Settings Privacy": "ms-settings:privacy",
            "Settings Update": "ms-settings:windowsupdate",
            "Settings Advanced Display": "ms-settings:display-advanced",
            "Settings": "ms-settings:",
        }

    def scan_project_directory(self, root_dir: str) -> Dict[str, str]:
        """Scans a specific directory for Python scripts / project files."""
        results = {}
        if not os.path.exists(root_dir):
            return results
            
        for root, dirs, files in os.walk(root_dir):
            if "__pycache__" in root or ".git" in root:
                continue
            for file in files:
                if file.endswith(('.py', '.md', '.txt')):
                    full_path = os.path.join(root, file)
                    # Use the file name as the "app" name
                    # e.g., open test_live_sequence.py
                    name = file.lower()
                    results[name] = full_path
                    
        return results
