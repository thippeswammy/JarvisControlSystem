"""
Log Analyzer
============
Advanced utilities for parsing and analyzing Jarvis system logs.
"""

import re
import os
from datetime import datetime, timedelta
from collections import Counter
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.text import Text

class LogAnalyzer:
    def __init__(self, log_path: str):
        self.log_path = Path(log_path)
        self.console = Console()

    def tail(self, n: int = 50, color: bool = True):
        """Read last N lines of logs."""
        if not self.log_path.exists():
            return [f"❌ Log file not found: {self.log_path}"]
        
        with open(self.log_path, "r", encoding="utf-8") as f:
            # Efficiently read last N lines
            lines = f.readlines()[-n:]
            
            if not color:
                return [l.strip() for l in lines]
            
            formatted = []
            for line in lines:
                text = Text(line.strip())
                if "[ERROR]" in line:
                    text.stylize("bold red")
                elif "[WARNING]" in line:
                    text.stylize("yellow")
                elif "[DEBUG]" in line:
                    text.stylize("dim")
                formatted.append(text)
            return formatted

    def analyze(self, since: str = "1h") -> dict:
        """Analyze log patterns within a time window."""
        if not self.log_path.exists():
            return {"error": "Log file not found"}

        # Parse duration
        match = re.match(r"(\d+)([hmd])", since)
        if not match:
            delta = timedelta(hours=1)
        else:
            val, unit = match.groups()
            val = int(val)
            if unit == "h": delta = timedelta(hours=val)
            elif unit == "m": delta = timedelta(minutes=val)
            else: delta = timedelta(days=val)

        cutoff = datetime.now() - delta
        
        stats = {
            "total_lines": 0,
            "levels": Counter(),
            "subsystems": Counter(),
            "errors": [],
            "skills_called": Counter(),
            "ollama_hits": 0,
            "mock_hits": 0
        }

        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                stats["total_lines"] += 1
                
                # Parse log line: HH:MM:SS [LEVEL] name — message
                # Note: Our format in main.py is just HH:MM:SS
                # We need to handle full ISO if it's there, but let's assume HH:MM:SS
                parts = re.match(r"(\d{2}:\d{2}:\d{2}) \[(\w+)\] ([\w\.]+) — (.*)", line)
                if not parts: continue
                
                ts_str, level, subsystem, msg = parts.groups()
                
                # Check level
                stats["levels"][level] += 1
                stats["subsystems"][subsystem] += 1
                
                if level == "ERROR":
                    stats["errors"].append(f"{ts_str} {msg}")
                
                if "Processing utterance via session" in msg:
                    # Potential start of an interaction
                    pass
                
                if "[LLMRouter] local/ollama" in msg and "healthy" not in msg:
                    stats["ollama_hits"] += 1
                elif "[LLMRouter] mock" in msg and "healthy" not in msg:
                    stats["mock_hits"] += 1
                
                # Skill calls (from SkillBus or ChannelManager)
                if "Discovered" in msg and "skills" in msg:
                    continue # Skip discovery log
                
                # Search for skill execution patterns if any
                
        return stats

    def clear(self):
        """Clear the current log file."""
        if self.log_path.exists():
            with open(self.log_path, "w", encoding="utf-8") as f:
                f.write(f"--- Log cleared at {datetime.now().isoformat()} ---\n")
            return True
        return False
