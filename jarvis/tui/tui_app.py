"""
Jarvis TUI Application
======================
Interactive terminal interface using Rich and PromptToolkit.
"""

import sys
import threading
import time
import logging
from datetime import datetime
from typing import List, Optional

from rich.console import Console, Group
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.patch_stdout import patch_stdout

from jarvis.gateway.gateway import GatewayDaemon
from jarvis.input.adapters import TUIAdapter
from jarvis.tui.status_bar import TUIStatusBar

# Disable internal logging for TUI
logging.getLogger("rich").setLevel(logging.WARNING)

class TUIMessageHistory:
    def __init__(self, max_messages: int = 50):
        self.messages: List[Text] = []
        self.max_messages = max_messages

    def add(self, sender: str, message: str, style: str = "#00d7ff"):
        # Convert raw ANSI if present, otherwise handle as markup
        try:
            if "\x1b" in message or "\033" in message:
                content = Text.from_ansi(message)
            else:
                content = Text.from_markup(message)
        except Exception:
            content = Text(message)
            
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Color mapping for senders
        sender_colors = {
            "JARVIS": "#00ffaf",
            "USER": "#ffffff",
            "SYSTEM": "#00d7ff",
            "BOOT": "dim #00d7ff"
        }
        sender_style = sender_colors.get(sender, style)
        
        prefix = Text.assemble(
            (f"[{timestamp}] ", "dim"),
            (f" {sender} ", f"bold {sender_style}"),
            (" › ", "dim")
        )
        
        full_msg = Text.assemble(prefix, content)
        self.messages.append(full_msg)
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)

    def render(self, height: int = 20) -> Group:
        # Only show the last N messages that fit in height roughly
        return Group(*self.messages[-height:])

class TUIApp:
    def __init__(self, profile: str = "default"):
        self.console = Console(force_terminal=True)
        self.layout = Layout()
        self.gateway = GatewayDaemon(profile=profile)
        self.adapter = TUIAdapter()
        self.status_bar = TUIStatusBar(start_time=datetime.now())
        self.history = TUIMessageHistory()
        self._running = False
        self._last_input = ""
        
        # Initial messages
        self.history.add("SYSTEM", "[bold #00d7ff]🛰 JARVIS OS LOADED[/bold #00d7ff]", style="#00d7ff")
        
    def _setup_layout(self):
        self.layout.split_column(
            Layout(name="header", size=4),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )
        
    def _update_layout(self):
        status_data = self.gateway.status()
        self.layout["header"].update(self.status_bar.render(status_data))
        
        # Calculate body height (rough estimate)
        body_height = self.console.size.rows - 12
        self.layout["body"].update(
            Panel(
                self.history.render(height=body_height), 
                title="[bold #00d7ff] ⚡ COMMUNICATIONS HUB [/bold #00d7ff]", 
                border_style="#005f87",
                padding=(1, 2)
            )
        )
        
        # Show prompt info in footer
        self.layout["footer"].update(
            Panel(
                Text.assemble(
                    (" JARVIS ACTIVE ", "bold #00d7ff"),
                    (" › ", "dim"),
                    (self._last_input if self._last_input else "Waiting for command...", "white")
                ), 
                title="[dim]INPUT STATUS[/dim]", 
                border_style="#005f87"
            )
        )

    def _output_loop(self):
        """Poll the adapter for messages from the gateway."""
        out_queue = self.adapter.get_output_queue()
        while self._running:
            try:
                msg = out_queue.get(timeout=0.1)
                if msg is None: break
                self.history.add("JARVIS", msg, style="#00ffaf")
            except:
                continue

    def run(self):
        self._running = True
        self._setup_layout()
        self._silence_terminal_logging()
        
        try:
            # 1. Start Gateway
            self.gateway.bootstrap()
            self.gateway.channel_mgr.add_channel(self.adapter)
            self.gateway.start()
            
            # 2. Start output listener
            threading.Thread(target=self._output_loop, daemon=True).start()
            
            # 3. Input Session
            session = PromptSession(
                history=FileHistory(".jarvis_history"),
                auto_suggest=AutoSuggestFromHistory()
            )
            
            # 4. Main Loop
            with Live(self.layout, console=self.console, refresh_per_second=4, screen=False) as live:
                while self._running:
                    self._update_layout()
                    
                    with patch_stdout():
                        try:
                            text = session.prompt("Jarvis› ").strip()
                            self._last_input = text
                            
                            if not text: continue
                            if text.lower() in ("/exit", "/quit"):
                                break
                            
                            self.history.add("USER", text, style="white")
                            self.adapter.simulate_input(text)
                            
                        except (KeyboardInterrupt, EOFError):
                            break
        finally:
            self.stop()
            self._restore_terminal_logging()

    def _silence_terminal_logging(self):
        root = logging.getLogger()
        self._old_handlers = []
        for h in root.handlers[:]:
            if isinstance(h, logging.StreamHandler):
                root.removeHandler(h)
                self._old_handlers.append(h)

    def _restore_terminal_logging(self):
        root = logging.getLogger()
        for h in self._old_handlers:
            root.addHandler(h)

    def stop(self):
        self._running = False
        self.console.print("\n[bold red]SHUTTING DOWN SYSTEMS...[/bold red]")
        self.gateway.stop()
        self.console.print("[bold green]OFFLINE.[/bold green]")

def main():
    app = TUIApp()
    app.run()

if __name__ == "__main__":
    main()
