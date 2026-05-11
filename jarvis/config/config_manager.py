"""
Config Manager
==============
Handles reading, writing, and validating Jarvis YAML configuration files.
Supports nested key access using dot notation (e.g. 'llm.primary').
"""

import yaml
from pathlib import Path
from typing import Any, Optional

class ConfigManager:
    def __init__(self, config_path: str):
        self.path = Path(config_path)
        self._cfg = {}
        self.load()

    def load(self):
        """Load configuration from disk."""
        if not self.path.exists():
            # Create default structure if missing? 
            # For now, just raise if missing during critical operations
            self._cfg = {}
            return
            
        with open(self.path, "r", encoding="utf-8") as f:
            self._cfg = yaml.safe_load(f) or {}

    def save(self):
        """Save current configuration to disk."""
        with open(self.path, "w", encoding="utf-8") as f:
            yaml.dump(self._cfg, f, default_flow_style=False, sort_keys=False)

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get value using dot notation (e.g. 'llm.primary')."""
        parts = key_path.split(".")
        val = self._cfg
        try:
            for part in parts:
                val = val[part]
            return val
        except (KeyError, TypeError):
            return default

    def set(self, key_path: str, value: Any):
        """Set value using dot notation."""
        parts = key_path.split(".")
        target = self._cfg
        
        # Traverse to the parent of the target key
        for part in parts[:-1]:
            if part not in target or not isinstance(target[part], dict):
                target[part] = {}
            target = target[part]
        
        # Type conversion attempt
        if isinstance(value, str):
            if value.lower() == "true": value = True
            elif value.lower() == "false": value = False
            elif value.isdigit(): value = int(value)
            elif value.replace(".", "", 1).isdigit(): value = float(value)
            
        target[parts[-1]] = value
        self.save()

    def unset(self, key_path: str) -> bool:
        """Remove a key using dot notation."""
        parts = key_path.split(".")
        target = self._cfg
        for part in parts[:-1]:
            if part not in target or not isinstance(target[part], dict):
                return False
            target = target[part]
        
        if parts[-1] in target:
            del target[parts[-1]]
            self.save()
            return True
        return False

    def validate(self) -> list[str]:
        """Check for mandatory keys and common errors. Returns list of issues."""
        issues = []
        required = ["llm.primary", "memory.db_path", "gateway"]
        for r in required:
            if self.get(r) is None:
                issues.append(f"Missing required key: {r}")
        
        # Check channel enabled/disabled
        if not self.get("channels"):
            issues.append("No 'channels' section defined.")
            
        return issues

    def show(self, mask_secrets: bool = True) -> dict:
        """Return full config with optional secret masking."""
        import copy
        cfg_copy = copy.deepcopy(self._cfg)
        
        if mask_secrets:
            # Mask common secrets
            if "channels" in cfg_copy:
                for chan in cfg_copy["channels"].values():
                    if isinstance(chan, dict) and "token" in chan:
                        chan["token"] = "********"
            if "llm" in cfg_copy and "api_key" in cfg_copy["llm"]:
                cfg_copy["llm"]["api_key"] = "********"
                
        return cfg_copy
