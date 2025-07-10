import os
import shutil # For shutil.which
import getpass # To get current username
from typing import Optional, Set

# Attempt to import components for .lnk resolution
try:
    import winshell
    from win32com.client import Dispatch
    CAN_RESOLVE_LNK = True
except ImportError:
    CAN_RESOLVE_LNK = False
    # print("Warning: 'winshell' or 'pywin32' not installed. .lnk file resolution will be skipped.")

# Import from local modules after system/external imports
from Jarvis.Data.XLSX_Information_Center import FileLocationHandeling, XLSX_ReadData, File_save

FileType_Application = ['.exe', '.lnk']

def get_expanded_user_path(path_template: str) -> Optional[str]:
    """Expands environment variables in a path and returns it if it exists."""
    expanded_path = os.path.expandvars(path_template)
    if os.path.isdir(expanded_path):
        return expanded_path
    return None

def get_base_scan_paths() -> Set[str]:
    """Returns a set of base paths to scan for applications."""
    paths_to_check = [
        'C:/ProgramData/Microsoft/Windows/Start Menu/Programs',
        get_expanded_user_path('%APPDATA%/Microsoft/Windows/Start Menu/Programs'),
        get_expanded_user_path('%LOCALAPPDATA%/Programs'),
        'C:/Program Files',
        'C:/Program Files (x86)',
        os.path.join(os.environ.get('ProgramW6432', 'C:/Program Files'), 'WindowsApps'), # Windows Store Apps (restricted access)
        os.path.join(os.environ.get('ProgramFiles(x86)', 'C:/Program Files (x86)'), 'WindowsApps'), # (restricted)
    ]

    # User and Public Desktops
    try:
        user_desktop = os.path.join(winshell.desktop()) if CAN_RESOLVE_LNK else os.path.join(os.path.expanduser('~'), 'Desktop')
        if os.path.isdir(user_desktop):
            paths_to_check.append(user_desktop)
    except Exception: # Handle cases where winshell might not be available or fail
        alt_user_desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
        if os.path.isdir(alt_user_desktop):
            paths_to_check.append(alt_user_desktop)

    try:
        public_desktop = os.path.join(winshell.common_desktop()) if CAN_RESOLVE_LNK else os.path.join(os.environ.get('PUBLIC', 'C:/Users/Public'), 'Desktop')
        if os.path.isdir(public_desktop):
            paths_to_check.append(public_desktop)
    except Exception:
        alt_public_desktop = os.path.join(os.environ.get('PUBLIC', 'C:/Users/Public'), 'Desktop')
        if os.path.isdir(alt_public_desktop):
            paths_to_check.append(alt_public_desktop)

    # User-specific Start Menu (alternative way)
    user_profile = os.environ.get('USERPROFILE')
    if user_profile:
        user_start_menu = os.path.join(user_profile, r'AppData\Roaming\Microsoft\Windows\Start Menu\Programs')
        if os.path.isdir(user_start_menu):
            paths_to_check.append(user_start_menu)

    # Filter out None values and return a set for uniqueness
    return set(p for p in paths_to_check if p and os.path.isdir(p))


def get_lnk_target(lnk_path: str) -> Optional[str]:
    """Resolves .lnk file to its target executable path if possible."""
    if not CAN_RESOLVE_LNK:
        return None
    try:
        shell = Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(lnk_path)
        target = shortcut.TargetPath
        # Follow .lnk to .lnk if necessary, up to a limit
        count = 0
        while target and target.lower().endswith(".lnk") and count < 5:
            shortcut = shell.CreateShortCut(target)
            target = shortcut.TargetPath
            count += 1
        return target if target and not target.lower().endswith(".lnk") else None
    except Exception as e:
        # print(f"Could not resolve .lnk: {lnk_path}, Error: {e}")
        return None


def GetAllFilePath(addr: str) -> str:
    """Scans all configured paths for .exe and .lnk files and saves them to AppNameList.xlsx."""
    # print("Starting GetAllFilePath...")
    flh = FileLocationHandeling(fileName="AppNameList") # Manages AppNameList.xlsx
    entry_number = 1 # This is the 'Count' in AddElements and determines the row
    processed_targets: Set[str] = set()  # Avoid duplicate processing of same executable path

    current_scan_paths = get_base_scan_paths()
    # print(f"Scanning {len(current_scan_paths)} base paths: {current_scan_paths}")

    for path_dir in current_scan_paths:
        try:
            for root, dirs, files in os.walk(path_dir):
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    file_lower = file_name.lower()

                    try:
                        if file_lower.endswith(".lnk"):
                            if CAN_RESOLVE_LNK:
                                target_path = get_lnk_target(file_path)
                                if target_path and target_path.lower().endswith(".exe") and target_path not in processed_targets:
                                    app_name_for_list = os.path.splitext(file_name)[0] # Use shortcut name as AppName
                                    flh.AddElements(AppName=app_name_for_list, PathFile=target_path, Count=entry_number, i=entry_number)
                                    processed_targets.add(target_path)
                                    entry_number += 1
                        elif file_lower.endswith(".exe"):
                            # Basic check to avoid system executables from deep system folders if not desired
                            # This simple check might be too broad or too narrow.
                            is_likely_system_internal = "\\windows\\system32" in root.lower() or \
                                                        "\\windows\\winsxs" in root.lower()
                            if file_path not in processed_targets and not is_likely_system_internal:
                                app_name_for_list = os.path.splitext(file_name)[0] # Use exe name as AppName
                                flh.AddElements(AppName=app_name_for_list, PathFile=file_path, Count=entry_number, i=entry_number)
                                processed_targets.add(file_path)
                                entry_number += 1
                    except Exception as e_inner: # Catch error during file processing
                        # print(f"Error processing file {file_path}: {e_inner}")
                        continue # Skip to next file
        except OSError as e_os: # Catch errors from os.walk (e.g. permission denied for a directory)
            # print(f"Cannot access path {path_dir} for scanning: {e_os}. Skipping.")
            continue # Skip to next path_dir

    if entry_number > 1:  # Only save if we found any apps
        flh.save_workbook()
        # print(f"GetAllFilePath completed. Found and saved {entry_number - 1} applications to AppNameList.xlsx.")
    else:
        # print("GetAllFilePath completed. No new applications found to save.")
        # Ensure an empty AppNameList.xlsx with headers is created if it doesn't exist
        if not os.path.exists(flh.excel_path):
            flh.save_workbook() # This will create it with headers via __init__ logic
            # print("Created empty AppNameList.xlsx with headers as no apps were found.")


    addr_out = addr + "GetAllFilePath -> "
    return addr_out


def GetFilePath(app_name_query: str, addr: str) -> str:
    """
    Retrieves the path of a given app_name_query.
    1. Cleans the query name (e.g., "Google Chrome" from "open google chrome").
    2. Checks the AppNameList.xlsx (populated by GetAllFilePath).
    3. If not found, uses shutil.which() to check system PATH.
    4. If still not found, performs a limited dynamic scan of base_paths.
    """
    # print(f"GetFilePath called for: '{app_name_query}'")
    cleaned_app_name = app_name_query.lower().replace(".exe", "").strip()

    # 1. Try reading from the pre-scanned list first
    df = XLSX_ReadData("AppNameList") # Uses the function from XLSX_Information_Center
    if df is not None and not df.empty:
        if 'AppName' in df.columns and 'PathFile' in df.columns:
            # Exact match on cleaned AppName (case-insensitive)
            for index, row in df.iterrows():
                excel_app_name = str(row['AppName']).lower().strip()
                if cleaned_app_name == excel_app_name:
                    path = str(row['PathFile'])
                    # print(f"Found '{app_name_query}' in AppNameList.xlsx: {path}")
                    return path
            # Substring match if no exact match (more flexible but can be less precise)
            for index, row in df.iterrows():
                excel_app_name = str(row['AppName']).lower().strip()
                if cleaned_app_name in excel_app_name:
                    path = str(row['PathFile'])
                    # print(f"Found substring match for '{app_name_query}' in AppNameList.xlsx: {path} (AppName: {row['AppName']})")
                    return path
        else:
            # print("Warning: 'AppName' or 'PathFile' column not found in AppNameList.xlsx.")
            pass

    # 2. If not found in Excel, try shutil.which (checks PATH)
    # print(f"'{app_name_query}' not in AppNameList.xlsx. Trying shutil.which...")
    which_path = shutil.which(cleaned_app_name)
    if which_path:
        # print(f"Found '{app_name_query}' via shutil.which: {which_path}")
        return which_path
    # Try with .exe if original query didn't have it
    if not cleaned_app_name.endswith(".exe"):
        which_path_exe = shutil.which(cleaned_app_name + ".exe")
        if which_path_exe:
            # print(f"Found '{cleaned_app_name}.exe' via shutil.which: {which_path_exe}")
            return which_path_exe

    # 3. Fallback: Limited dynamic scan if not found by other means (can be slow)
    # print(f"'{app_name_query}' not found via shutil.which. Performing limited dynamic scan...")
    # This dynamic scan is a simplified version of GetAllFilePath, focused on finding one app.
    # It does NOT update AppNameList.xlsx.
    current_scan_paths = get_base_scan_paths()
    for path_dir in current_scan_paths:
        try:
            for root, dirs, files in os.walk(path_dir):
                for file in files:
                    file_lower = file.lower()
                    base_name_no_ext, ext = os.path.splitext(file_lower)

                    if ext in FileType_Application: # Check if .exe or .lnk
                        # Match against the name without extension
                        if cleaned_app_name == base_name_no_ext:
                            full_path = os.path.join(root, file)
                            if ext == ".exe":
                                # print(f"Found '{app_name_query}' by dynamic scan (exe): {full_path}")
                                return full_path
                            elif ext == ".lnk" and CAN_RESOLVE_LNK:
                                target = get_lnk_target(full_path)
                                if target and target.lower().endswith(".exe"):
                                    # print(f"Found '{app_name_query}' by dynamic scan (lnk to exe): {target}")
                                    return target
        except OSError as e_os_dyn: # os.walk error
            # print(f"Cannot access path {path_dir} for dynamic scan: {e_os_dyn}. Skipping.")
            continue


    addr_out = addr + f"GetFilePath (not found for '{app_name_query}') -> "
    # print(f"GetFilePath: '{app_name_query}' not found after all checks.")
    return ""

# Example usage (for testing purposes, comment out in production):
# if __name__ == "__main__":
#     print("Running SystemFilePathScanner directly for testing.")
#     # Ensure AGENTS.md is not expecting this to run in a specific way during tests.
#
#     # Test GetAllFilePath - this will create/update AppNameList.xlsx
#     print("\nTesting GetAllFilePath...")
#     GetAllFilePath("test_addr_getall -> ")
#     print("GetAllFilePath finished. Check Jarvis/Data/Data_Information_Value/AppNameList.xlsx")

#     # Test GetFilePath
#     print("\nTesting GetFilePath with various app names:")
#     test_apps = ["notepad", "chrome", "firefox", "explorer", "cmd", "code", "slack"] # Add more as needed
#     for app in test_apps:
#         print(f"\nSearching for: '{app}'")
#         path_found = GetFilePath(app, "test_addr_getpath -> ")
#         if path_found:
#             print(f"==> Path for '{app}': {path_found}")
#         else:
#             print(f"==> Path for '{app}': NOT FOUND")

#     non_existent_app = "ThisApplicationShouldNotExist12345"
#     print(f"\nSearching for non-existent app: '{non_existent_app}'")
#     path_found_non_existent = GetFilePath(non_existent_app, "test_addr_getpath_nonexistent -> ")
#     if path_found_non_existent:
#         print(f"==> Path for '{non_existent_app}': {path_found_non_existent} (ERROR, should not be found)")
#     else:
#         print(f"==> Path for '{non_existent_app}': NOT FOUND (Correct)")

#     # Example of how ApplicationManager might call GetFilePath
#     print("\nSimulating call from ApplicationManager for 'notepad':")
#     am_path = GetFilePath("notepad", "AM_sim_addr -> ")
#     print(f"ApplicationManager simulated GetFilePath('notepad') result: {am_path}")
