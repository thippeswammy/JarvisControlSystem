import logging
import psutil
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from pywinauto import Desktop
    from pywinauto.application import Application
    _HAS_PYWINAUTO = True
except ImportError:
    _HAS_PYWINAUTO = False

try:
    import win32gui
    import win32process
    _HAS_WIN32 = True
except ImportError:
    _HAS_WIN32 = False


@dataclass
class UISnapshot:
    window_title: str = ""
    app_name: str = "Unknown"
    exe_path: str = ""
    panels: list[str] = field(default_factory=list)
    buttons: list[str] = field(default_factory=list)
    inputs: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    list_items: list[str] = field(default_factory=list)
    menu_items: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not any([
            self.panels, self.buttons, self.inputs, self.links,
            self.list_items, self.menu_items
        ])


def _get_process_info(hwnd) -> tuple[str, str]:
    """Returns app_name (from exe) and full exe_path for a window handle."""
    if not _HAS_WIN32:
        return "Unknown", ""
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        p = psutil.Process(pid)
        exe_path = p.exe()
        app_name = p.name()
        if app_name.lower().endswith(".exe"):
            app_name = app_name[:-4]
        return app_name, exe_path
    except Exception:
        return "Unknown", ""


def _clean_name(name) -> str:
    if not isinstance(name, str):
        return ""
    return name.strip()


def extract_window_elements(hwnd=None, max_per_category: int = 20) -> Optional[UISnapshot]:
    """
    Extracts structured, categorized UI elements from the foreground window (or specified hwnd).
    Uses pywinauto (UIA backend) to crawl control types.
    """
    if not _HAS_PYWINAUTO or not _HAS_WIN32:
        return None

    try:
        target_hwnd = hwnd or win32gui.GetForegroundWindow()
        if not target_hwnd:
            return None

        title = win32gui.GetWindowText(target_hwnd)
        if hasattr(title, "strip") and not title.strip():
            # If standard win32gui title is empty, wait for pywinauto to get the UIA name
            pass
            
        app_name, exe_path = _get_process_info(target_hwnd)
        
        desktop = Desktop(backend="uia")
        win = desktop.window(handle=target_hwnd).wrapper_object()
        
        if not title:
            try:
                title = win.window_text() or "Unknown Window"
            except Exception:
                title = "Unknown Window"

        snap = UISnapshot(window_title=title, app_name=app_name, exe_path=exe_path)

        # Chrome components (universal things we don't care about)
        chrome_ignores = {"minimize", "maximize", "close", "restore", "system"}

        # Sets to ensure uniqueness
        seen_panels = set()
        seen_buttons = set()
        seen_inputs = set()
        seen_links = set()
        seen_list_items = set()
        seen_menu_items = set()

        try:
            # We fetch all descendants once to minimize RPC overhead, then bucket them.
            descendants = win.descendants()
            
            for elem in descendants:
                try:
                    ctrl_type = elem.element_info.control_type
                    name = _clean_name(elem.window_text())
                    
                    if not name or len(name) <= 1:
                        continue
                        
                    name_lower = name.lower()
                    if name_lower in chrome_ignores:
                        continue
                        
                    # Bucket by control type
                    if ctrl_type in ("Pane", "Group", "TabItem", "Tab"):
                        if name not in seen_panels and len(snap.panels) < max_per_category:
                            snap.panels.append(name)
                            seen_panels.add(name)
                            
                    elif ctrl_type == "Button":
                        if name not in seen_buttons and len(snap.buttons) < max_per_category:
                            snap.buttons.append(name)
                            seen_buttons.add(name)
                            
                    elif ctrl_type in ("Edit", "ComboBox", "Document"):
                        if name not in seen_inputs and len(snap.inputs) < max_per_category:
                            snap.inputs.append(name)
                            seen_inputs.add(name)
                            
                    elif ctrl_type == "Hyperlink":
                        if name not in seen_links and len(snap.links) < max_per_category:
                            snap.links.append(name)
                            seen_links.add(name)
                            
                    elif ctrl_type in ("ListItem", "TreeItem"):
                        if name not in seen_list_items and len(snap.list_items) < max_per_category:
                            # Flag selected items
                            try:
                                if elem.is_selected():
                                    name = f"{name} [active]"
                            except Exception:
                                pass
                            snap.list_items.append(name)
                            seen_list_items.add(name)
                            
                    elif ctrl_type == "MenuItem":
                        if name not in seen_menu_items and len(snap.menu_items) < max_per_category:
                            snap.menu_items.append(name)
                            seen_menu_items.add(name)
                            
                except Exception:
                    continue
                    
        except Exception as e:
            logger.debug(f"Failed extracting pywinauto descendants: {e}")

        return snap

    except Exception as e:
        logger.error(f"UI extraction failed completely: {e}")
        return None
