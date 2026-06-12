import os
import sys
import time
import subprocess
from pathlib import Path

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pywinauto import Application, Desktop
from pywinauto.findwindows import ElementNotFoundError
from rich.console import Console
from rich.table import Table

console = Console()

def print_banner():
    console.print("\n[bold cyan]==========================================================[/bold cyan]")
    console.print("[bold white]   JARVIS Windows UI Automation Accessibility Demo      [/bold white]")
    console.print("[bold cyan]==========================================================[/bold cyan]\n")

def main():
    print_banner()
    
    # 0. Clean up any existing Calculator instances to prevent matching collisions
    os.system("taskkill /f /im CalculatorApp.exe >nul 2>&1")
    os.system("taskkill /f /im Calculator.exe >nul 2>&1")
    time.sleep(0.5)

    # 1. Start the Windows Calculator App (calc.exe)
    console.print("[yellow][*] Starting Windows Calculator App (calc.exe)...[/yellow]")
    try:
        app = Application(backend="uia").start("calc.exe")
    except Exception as e:
        console.print(f"[red][x] Failed to launch Calculator: {e}[/red]")
        return
    
    # Give it time to load and render
    time.sleep(2.0)
    
    # 2. Locate Calculator Window in Desktop
    console.print("[yellow][*] Locating the Calculator window in UIA Tree...[/yellow]")
    try:
        desktop = Desktop(backend="uia")
        # Find by window text / title
        calc_window = desktop.window(title="Calculator")
        # Force window to top / active focus
        calc_window.set_focus()
        
        console.print("[green][+] Found Calculator Window![/green]")
        console.print(f"    Name: [cyan]{calc_window.window_text()}[/cyan]")
        console.print(f"    Class Name: [cyan]{calc_window.class_name()}[/cyan]")
        console.print(f"    Bounding Box: [cyan]{calc_window.rectangle()}[/cyan]\n")
        
        # 3. Perform a calculation: 5 + 3 = 8
        console.print("[yellow][*] Performing calculation via UIA Automation: 5 + 3 = ...[/yellow]")
        
        # Click "5"
        console.print("  -> Clicking '5' (num5Button)...")
        calc_window.child_window(auto_id="num5Button").click()
        time.sleep(0.3)
        
        # Click "+"
        console.print("  -> Clicking '+' (plusButton)...")
        calc_window.child_window(auto_id="plusButton").click()
        time.sleep(0.3)
        
        # Click "3"
        console.print("  -> Clicking '3' (num3Button)...")
        calc_window.child_window(auto_id="num3Button").click()
        time.sleep(0.3)
        
        # Click "="
        console.print("  -> Clicking '=' (equalButton)...")
        calc_window.child_window(auto_id="equalButton").click()
        time.sleep(0.5)
        
        # 4. Read Display Screen
        console.print("[yellow][*] Reading calculator display result...[/yellow]")
        results_elem = calc_window.child_window(auto_id="CalculatorResults")
        display_name = results_elem.window_text()
        console.print(f"[green][+] Calculator Display shows: '{display_name}'[/green]\n")
        
        # 5. Open History Panel
        console.print("[yellow][*] Locating History Button...[/yellow]")
        # Find the History button in standard layout
        try:
            btn_hist = calc_window.child_window(auto_id="HistoryButton")
            console.print(f"[green][+] Found History button: '{btn_hist.window_text()}' (ID: HistoryButton)[/green]")
            console.print("    Clicking to open History panel...")
            btn_hist.click()
            time.sleep(1.0)
        except ElementNotFoundError:
            # Fallback for small Calculator layouts: try toggle pane button or menu
            console.print("[yellow][!] Dedicated HistoryButton not found. Trying TogglePaneButton fallback...[/yellow]")
            calc_window.child_window(auto_id="TogglePaneButton").click()
            time.sleep(1.0)
            
        # 6. Extract History Entries using UIA
        console.print("[yellow][*] Scanning active UIA accessibility elements for History...[/yellow]")
        try:
            hist_list = calc_window.child_window(auto_id="HistoryListView")
            items = hist_list.children()
            
            if items:
                console.print(f"[green][+] Successfully retrieved {len(items)} history entries:[/green]")
                table = Table(title="Calculator History Entries (UIA Traversed)", header_style="bold magenta")
                table.add_column("Index", style="cyan", justify="right")
                table.add_column("UIA Name / Text Content", style="green")
                table.add_column("UIA Class", style="yellow")
                
                for idx, item in enumerate(items, 1):
                    table.add_row(str(idx), item.window_text(), item.class_name())
                console.print(table)
            else:
                console.print("[yellow][!] History list exists but is currently empty.[/yellow]")
        except ElementNotFoundError:
            console.print("[red][x] HistoryListView element not found. Please ensure history is populated and pane is open.[/red]")
            
        # 7. Close History / Navigate Back
        console.print("\n[yellow][*] Navigating back (closing history pane)...[/yellow]")
        try:
            close_hist = calc_window.child_window(auto_id="CloseHistoryFlyoutButton")
            close_hist.click_input()
            console.print("  -> Closed History Flyout.")
        except Exception:
            # Fallback: Click the main display area physically to dismiss the flyout
            try:
                results_elem.click_input()
                console.print("  -> Dismissed History flyout via click_input on display.")
            except Exception:
                try:
                    calc_window.click_input()
                    console.print("  -> Dismissed History flyout via click_input on window.")
                except Exception:
                    console.print("  -> Pane dismissed.")
            
        time.sleep(1.0)
        console.print("[green][+] Done! Successfully demonstrated full Windows UI Automation roundtrip![/green]")
        
    except Exception as e:
        console.print(f"[red][x] An error occurred during automation: {e}[/red]")
    finally:
        console.print("\n[bold cyan]==========================================================[/bold cyan]")

if __name__ == "__main__":
    main()
