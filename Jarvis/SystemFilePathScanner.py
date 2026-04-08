import os
import shutil
from typing import Optional, Set

# Optional Windows shortcut resolution
try:
    import winshell
    from win32com.client import Dispatch

    CAN_RESOLVE_LNK = True
except ImportError:
    CAN_RESOLVE_LNK = False

from Jarvis.Data.XLSX_Information_Center import FileLocationHandeling, XLSX_ReadData

# Supported app file extensions
SUPPORTED_EXTS = ['.exe', '.lnk']


def expand_and_verify(path_template: str) -> Optional[str]:
    """Expands environment variables and returns if path exists."""
    path = os.path.expandvars(path_template)
    return path if os.path.isdir(path) else None


def get_base_scan_paths() -> Set[str]:
    """Returns key directories to scan for application shortcuts and binaries."""
    paths = {
        'C:/ProgramData/Microsoft/Windows/Start Menu/Programs',
        expand_and_verify('%APPDATA%/Microsoft/Windows/Start Menu/Programs'),
        expand_and_verify('%LOCALAPPDATA%/Programs'),
        'C:/Program Files',
        'C:/Program Files (x86)',
        os.path.join(os.environ.get('ProgramW6432', 'C:/Program Files'), 'WindowsApps'),
        os.path.join(os.environ.get('ProgramFiles(x86)', 'C:/Program Files (x86)'), 'WindowsApps')
    }

    # Add desktop shortcuts
    if CAN_RESOLVE_LNK:
        paths.add(winshell.desktop())
        paths.add(winshell.common_desktop())
    else:
        paths.add(os.path.join(os.path.expanduser('~'), 'Desktop'))
        paths.add(os.path.join(os.environ.get('PUBLIC', 'C:/Users/Public'), 'Desktop'))

    # Fallback start menu
    user_start_menu = os.path.join(os.environ.get('USERPROFILE', ''),
                                   'AppData/Roaming/Microsoft/Windows/Start Menu/Programs')
    if os.path.isdir(user_start_menu):
        paths.add(user_start_menu)

    return {p for p in paths if p and os.path.isdir(p)}


def resolve_lnk(lnk_path: str) -> Optional[str]:
    """Resolves a Windows .lnk shortcut to its target."""
    if not CAN_RESOLVE_LNK:
        return None
    try:
        shell = Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(lnk_path)
        target = shortcut.TargetPath

        # Resolve nested .lnk (max 5 levels)
        for _ in range(5):
            if target.lower().endswith('.lnk'):
                shortcut = shell.CreateShortCut(target)
                target = shortcut.TargetPath
            else:
                break

        return target if target.lower().endswith('.exe') else None
    except Exception:
        return None


def GetAllFilePath(addr: str) -> str:
    """
    Scans predefined directories for `.exe` and `.lnk` files,
    resolves and saves app names + paths to `AppNameList.xlsx`.
    """
    flh = FileLocationHandeling(fileName="AppNameList")
    seen_paths = set()
    entry_number = 1

    for base_dir in get_base_scan_paths():
        try:
            for root, _, files in os.walk(base_dir):
                for file in files:
                    full_path = os.path.join(root, file)
                    ext = os.path.splitext(file)[1].lower()

                    try:
                        if ext == '.lnk' and CAN_RESOLVE_LNK:
                            target = resolve_lnk(full_path)
                            if target and target not in seen_paths:
                                app_name = os.path.splitext(file)[0]
                                flh.AddElements(app_name, target, entry_number, entry_number)
                                seen_paths.add(target)
                                entry_number += 1

                        elif ext == '.exe':
                            if full_path not in seen_paths and not any(sys_folder in root.lower()
                                                                       for sys_folder in
                                                                       ['\\windows\\system32', '\\windows\\winsxs']):
                                app_name = os.path.splitext(file)[0]
                                flh.AddElements(app_name, full_path, entry_number, entry_number)
                                seen_paths.add(full_path)
                                entry_number += 1

                    except Exception:
                        continue
        except Exception:
            continue

    if entry_number > 1 or not os.path.exists(flh.excel_path):
        flh.save_workbook()

    return addr + "GetAllFilePath -> "


def GetFilePath(app_name: str, addr: str) -> str:
    """
    Retrieves full path of an app based on name. Steps:
    1. Match in saved AppNameList.xlsx
    2. Try `shutil.which` in system PATH
    3. Limited fallback scan
    """
    query = app_name.lower().replace(".exe", "").strip()
    df = XLSX_ReadData("AppNameList")

    # 1. Search in Excel file
    if df is not None and not df.empty and {'AppName', 'PathFile'}.issubset(df.columns):
        # Exact match
        for _, row in df.iterrows():
            if query == str(row['AppName']).lower().strip():
                return row['PathFile']
        # Substring match
        for _, row in df.iterrows():
            if query in str(row['AppName']).lower().strip():
                return row['PathFile']

    # 2. Fallback to system PATH
    sys_path = shutil.which(query) or shutil.which(query + ".exe")
    if sys_path:
        return sys_path

    # 3. Final fallback: Scan common paths again
    for base_dir in get_base_scan_paths():
        try:
            for root, _, files in os.walk(base_dir):
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    name = os.path.splitext(file.lower())[0]
                    if ext in SUPPORTED_EXTS and name == query:
                        full_path = os.path.join(root, file)
                        if ext == ".exe":
                            return full_path
                        elif ext == ".lnk" and CAN_RESOLVE_LNK:
                            resolved = resolve_lnk(full_path)
                            if resolved:
                                return resolved
        except Exception:
            continue

    return ""  # Not found
