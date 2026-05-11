"""
Jarvis Doctor
=============
Diagnoses and checks system health, configuration, and dependencies.
"""

import os
import sys
import shutil
from rich.console import Console
from rich.table import Table

def run_doctor(gateway):
    console = Console()
    table = Table(title="🩺 Jarvis System Diagnostic", border_style="magenta")
    table.add_column("Component", style="bold")
    table.add_column("Check")
    table.add_column("Result")
    
    # 1. Environment
    python_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    table.add_row("Python", "Version Check", f"[green]OK[/green] {python_ver}")
    
    # 2. Config
    if os.path.exists(gateway._config_path):
        table.add_row("Configuration", "File Existence", f"[green]OK[/green] {os.path.basename(gateway._config_path)}")
    else:
        table.add_row("Configuration", "File Existence", "[red]Missing![/red]")
        
    # 3. LLM Router / Backends
    if gateway.router:
        health = gateway.router.status()
        p_name = gateway.router._primary.name
        res = "[green]Healthy[/green]" if health.get(p_name) else "[red]Down[/red]"
        table.add_row("LLM Backend", f"Primary ({p_name})", res)
    else:
        table.add_row("LLM Backend", "Router Init", "[red]Failed[/red]")
        
    # 4. Memory
    if gateway.memory:
        db_path = gateway.memory.get_db_path()
        if os.path.exists(db_path):
            size = os.path.getsize(db_path) // 1024
            table.add_row("Memory DB", "Connectivity", f"[green]Connected[/green] ({size} KB)")
        else:
            table.add_row("Memory DB", "Connectivity", "[red]Missing file[/red]")
    else:
        table.add_row("Memory DB", "Initialization", "[red]Failed[/red]")
        
    # 5. External Tools
    ollama_path = shutil.which("ollama")
    if ollama_path:
        table.add_row("Ollama", "Binary Check", "[green]Installed[/green]")
    else:
        table.add_row("Ollama", "Binary Check", "⚠️  Not found in PATH")
        
    console.print(table)
    
    # Recommendations
    recs = []
    if not gateway.router or not health.get(gateway.router._primary.name):
        recs.append("Check if Ollama is running (`ollama serve`).")
    if not os.path.exists(gateway._config_path):
        recs.append("Run `jarvis setup` to create a default configuration.")
        
    if recs:
        console.print("\n[bold yellow]Recommendations:[/bold yellow]")
        for r in recs:
            console.print(f"  • {r}")
