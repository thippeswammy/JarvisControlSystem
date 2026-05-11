"""
TUI Status Bar
==============
Rich-based status bar for the Jarvis TUI.
"""

from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from datetime import datetime

class TUIStatusBar:
    """
    Render a live status bar showing system health, sessions, and uptime.
    """
    def __init__(self, start_time: datetime):
        self._start_time = start_time

    def render(self, status: dict) -> Panel:
        uptime = datetime.now() - self._start_time
        uptime_str = str(uptime).split(".")[0] # HH:MM:SS
        
        # Channel status icons
        channels = status.get("channels", [])
        chan_icons = []
        for c in channels:
            color = "green" if c["status"] == "running" else "grey50"
            chan_icons.append(Text(f"● {c['name']}", style=color))
        
        left_col = Text.assemble(
            ("JARVIS v2.1", "bold cyan"),
            "  |  ",
            ("Sessions: ", "white"),
            (str(status.get("sessions", 0)), "bold yellow")
        )
        
        center_col = Columns(chan_icons, padding=2)
        
        right_col = Text.assemble(
            ("Uptime: ", "white"),
            (uptime_str, "bold green")
        )
        
        content = Columns([left_col, center_col, right_col], expand=True)
        
        return Panel(
            content,
            style="on blue",
            border_style="cyan"
        )
