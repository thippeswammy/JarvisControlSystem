"""
Preference Router
=================
Loads user-defined workspace preferences from config/preferences.yaml.
Injects persistent 'System Context' into LLM prompts (default browser, email, etc).
"""

import logging
import os
from pathlib import Path
from typing import Dict, Optional

import yaml

logger = logging.getLogger(__name__)

_DEFAULT_PREFS = {
    "workspace": {
        "os": "windows_11",
        "browser": "chrome",
        "email": "gmail_web",
        "email_url": "https://mail.google.com",
        "terminal": "powershell",
        "text_editor": "notepad"
    }
}

class PreferenceRouter:
    """
    Manages user workspace preferences and generates LLM system context blocks.
    """

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = str(Path(__file__).parent.parent / "config" / "preferences.yaml")
        
        self._config_path = config_path
        self._prefs = self._load_prefs()

    def _load_prefs(self) -> Dict:
        if not os.path.exists(self._config_path):
            logger.info(f"[PreferenceRouter] No preferences.yaml found. Creating default.")
            dir_name = os.path.dirname(self._config_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            with open(self._config_path, "w", encoding="utf-8") as f:
                yaml.dump(_DEFAULT_PREFS, f, default_flow_style=False)
            return _DEFAULT_PREFS
        
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or _DEFAULT_PREFS
        except Exception as e:
            logger.error(f"[PreferenceRouter] Failed to load {self._config_path}: {e}")
            return _DEFAULT_PREFS

    def get_system_context(self) -> str:
        """Returns the system context block for LLM prompt injection."""
        w = self._prefs.get("workspace", {})
        return (
            f"[User Workspace Defaults]\n"
            f"OS: {w.get('os', 'Windows')} | "
            f"Browser: {w.get('browser', 'unknown')} | "
            f"Email: {w.get('email', 'unknown')} ({w.get('email_url', '')}) | "
            f"Terminal: {w.get('terminal', 'unknown')} | "
            f"Editor: {w.get('text_editor', 'unknown')}"
        )

    def get_pref(self, category: str, key: str, default=None):
        return self._prefs.get(category, {}).get(key, default)
