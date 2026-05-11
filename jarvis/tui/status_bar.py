"""
TUI Status Bar
==============
Rich-based status bar for the Jarvis TUI.
"""

from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from datetime import datetime

import psutil
import platform
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.table import Table
from datetime import datetime

class TUIStatusBar:
    """
    Render a high-tech status bar showing system health, sessions, and uptime.
    """
    def __init__(self, start_time: datetime):
        self._start_time = start_time
        self._cpu_count = psutil.cpu_count()

    def _get_resource_usage(self) -> Text:
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        
        cpu_color = "green" if cpu < 50 else "yellow" if cpu < 80 else "red"
        ram_color = "green" if ram < 50 else "yellow" if ram < 80 else "red"
        
        return Text.assemble(
            ("CPU ", "dim"), (f"{cpu}%", cpu_color),
            ("  ", ""),
            ("RAM ", "dim"), (f"{ram}%", ram_color)
        )

    def render(self, status: dict) -> Panel:
        uptime = datetime.now() - self._start_time
        uptime_str = str(uptime).split(".")[0] # HH:MM:SS
        
        # Channel status icons
        channels = status.get("channels", [])
        chan_texts = []
        for c in channels:
            icon = "⦿" if c["status"] == "running" else "○"
            color = "#00ffaf" if c["status"] == "running" else "grey37"
            chan_texts.append(Text(f"{icon} {c['name']}", style=color))
        
        # Build the header content
        table = Table.grid(expand=True)
        table.add_column(justify="left", ratio=1)
        table.add_column(justify="center", ratio=1)
        table.add_column(justify="right", ratio=1)
        
        left = Text.assemble(
            (" 🛰  ", "#00d7ff"),
            ("JARVIS CORE ", "bold #00d7ff"),
            (f"v2.1", "dim #00d7ff"),
            ("\n"),
            (" SESSIONS: ", "white"),
            (str(status.get("sessions", 0)), "bold #ffaf00")
        )
        
        center = Text.assemble(
            ("SYSTEM STATUS\n", "dim"),
            *([t + "  " for t in chan_texts] if chan_texts else [Text("NO CHANNELS", style="red")])
        )
        
        right = Text.assemble(
            (self._get_resource_usage()),
            ("\n"),
            ("UPTIME: ", "white"),
            (uptime_str, "bold #00ff00")
        )
        
        table.add_row(left, center, right)
        
        return Panel(
            table,
            title=f"[bold #00d7ff]{platform.node().upper()}[/bold #00d7ff]",
            title_align="left",
            border_style="#005f87",
            padding=(0, 1)
        )

