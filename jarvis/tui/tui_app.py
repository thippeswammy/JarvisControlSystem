"""
Jarvis TUI Application
======================
Interactive terminal interface using Rich and PromptToolkit.
"""

import sys
import threading
import time
from datetime import datetime
from typing import Optional

from rich.console import Console
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

class TUIApp:
    def __init__(self, profile: str = "default"):
        self.console = Console()
        self.layout = Layout()
        self.gateway = GatewayDaemon(profile=profile)
        self.adapter = TUIAdapter()
        self.status_bar = TUIStatusBar(start_time=datetime.now())
        self._running = False
        
    def _setup_layout(self):
        self.layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body")
        )
        self.layout["header"].update(self.status_bar.render(self.gateway.status()))
        self.layout["body"].update(Panel("Welcome to JARVIS v2.1\nType your command below.", title="Chat", border_style="green"))

    def _output_loop(self):
        """Poll the adapter for messages from the gateway and print them."""
        out_queue = self.adapter.get_output_queue()
        while self._running:
            try:
                # Use a short timeout to check for shutdown
                msg = out_queue.get(timeout=0.5)
                with patch_stdout():
                    self.console.print(f"\n[bold green]🤖 JARVIS:[/bold green] {msg}")
            except:
                continue

    def run(self):
        self._running = True
        
        # 1. Bootstrap gateway
        self.gateway.bootstrap()
        
        # 2. Inject TUI adapter
        self.gateway.channel_mgr.add_channel(self.adapter)
        
        # 3. Start gateway
        self.gateway.start()
        
        # 4. Start output listener thread
        threading.Thread(target=self._output_loop, daemon=True).start()
        
        self.console.print("[bold cyan]🛰 Systems Online.[/bold cyan] Gateway active with TUI adapter.")
        
        # 5. Input loop
        session = PromptSession(
            history=FileHistory(".jarvis_history"),
            auto_suggest=AutoSuggestFromHistory()
        )
        
        try:
            while self._running:
                # Render header periodically?
                # For now, just a static header or printed once
                
                with patch_stdout():
                    # Show status summary before prompt
                    stat = self.gateway.status()
                    chans = ", ".join([c['name'] for c in stat['channels'] if c['status'] == 'running'])
                    self.console.print(f"[dim]Sessions: {stat['sessions']} | Channels: {chans}[/dim]", style="grey50")
                    
                    text = session.prompt("Jarvis› ").strip()
                
                if not text:
                    continue
                
                if text.lower() in ("/exit", "/quit", "exit", "quit"):
                    break
                
                # Send to gateway
                self.adapter.simulate_input(text)
                
                # Small sleep to let logs/output settle if needed
                time.sleep(0.1)
                
        except (KeyboardInterrupt, EOFError):
            pass
        finally:
            self.stop()

    def stop(self):
        self._running = False
        self.console.print("\n[bold red]Stopping Gateway...[/bold red]")
        self.gateway.stop()
        self.console.print("[bold green]Goodbye.[/bold green]")

def main():
    app = TUIApp()
    app.run()

if __name__ == "__main__":
    main()
