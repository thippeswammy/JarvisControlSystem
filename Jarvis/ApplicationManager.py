import os
import psutil
import subprocess
from Jarvis.SystemFilePathScanner import GetFilePath # Assuming GetFilePath is robust
from typing import Optional, Union

# Helper function to clean application name queries
def clean_app_name(name: str) -> str:
    """ Basic cleaning for app name queries.
        Removes common prefixes like "open", "start", "run", "launch"
        and common extensions like ".exe", ".lnk".
        Converts to lowercase and strips whitespace.
    """
    if not isinstance(name, str): # Ensure name is a string
        return ""

    name_lower = name.lower()
    prefixes = ["open ", "start ", "run ", "launch "]
    for prefix in prefixes:
        if name_lower.startswith(prefix):
            name_lower = name_lower[len(prefix):] # Slice off the prefix
            break # Remove only one prefix if multiple somehow exist (e.g. "open start app")

    # Remove extensions
    name_lower = name_lower.replace(".exe", "").replace(".lnk", "")
    return name_lower.strip()


def open_application(app_name_query: str, app_path_override: Optional[str] = None, addr: str = "") -> Union[bool, str]:
    """
    Opens an application.
    Args:
        app_name_query: The name of the application to open (e.g., "notepad", "Google Chrome").
                        This will be cleaned before processing.
        app_path_override: If provided, this path is used directly, bypassing GetFilePath.
        addr: Logging/tracing address string.

    Returns:
        True if successfully launched.
        False if the application cannot be found or fails to launch.
        (The "Search by windows" string return is removed as GetFilePath should be more definitive)
    """
    # print(f"{addr}open_application: Query='{app_name_query}', Override='{app_path_override}'")

    final_app_path = ""

    if app_path_override and os.path.exists(app_path_override): # If override is provided and valid
        # print(f"{addr}Using direct path override: {app_path_override}")
        final_app_path = app_path_override
    else:
        cleaned_name = clean_app_name(app_name_query)
        if not cleaned_name:
            # print(f"{addr}Cleaned app name is empty for query: '{app_name_query}'. Cannot open.")
            return False

        # print(f"{addr}Calling GetFilePath with cleaned name: '{cleaned_name}'")
        found_path = GetFilePath(cleaned_name, addr + "GetFilePath -> ")
        if found_path:
            final_app_path = found_path
        else: # GetFilePath returned empty string
            # print(f"{addr}Application '{cleaned_name}' not found by GetFilePath.")
            return False # Explicitly False if path not found

    # print(f"{addr}Attempting to open application using path: '{final_app_path}'")
    try:
        if os.path.exists(final_app_path): # Double check existence, though GetFilePath should ensure it
            subprocess.Popen(final_app_path, shell=True) # shell=True from original, consider implications
            # print(f"{addr}Successfully launched: {final_app_path}")
            return True
        else:
            # This case should be rare if GetFilePath works as expected or override is valid.
            # print(f"{addr}Application path '{final_app_path}' does not exist (unexpected).")
            return False
    except Exception as e:
        # print(f"{addr}Error opening application '{final_app_path}': {e}")
        return False


def close_application_by_name(app_name_query: str, addr: str = "") -> bool:
    """
    Closes an application by its process name.
    It cleans the input name and tries to match 'cleaned_name.exe' or 'cleaned_name' within running process names.
    """
    cleaned_name = clean_app_name(app_name_query)
    if not cleaned_name:
        # print(f"{addr}close_application_by_name: Cleaned name is empty for query '{app_name_query}'.")
        return False

    # print(f"{addr}close_application_by_name: Attempting to close processes matching '{cleaned_name}'")

    app_exe_name_lower = cleaned_name.lower() + ".exe"
    cleaned_name_lower = cleaned_name.lower()

    terminated_any = False
    for process in psutil.process_iter(['pid', 'name']):
        try:
            p_name_lower = process.info['name'].lower()
            # Primary match: process name is exactly 'cleaned_name.exe'
            # Secondary match: process name is 'cleaned_name' (e.g. 'Code' for VS Code)
            # Tertiary match: 'cleaned_name' is a substring of process name (e.g. 'chrome' in 'chrome.exe')
            if (p_name_lower == app_exe_name_lower or
                p_name_lower == cleaned_name_lower or
                cleaned_name_lower in p_name_lower):
                # print(f"{addr}Found process '{process.info['name']}' (PID: {process.info['pid']}) matching '{cleaned_name}'. Terminating...")
                psutil.Process(process.info['pid']).terminate()
                # print(f"{addr}Terminated '{process.info['name']}'.")
                terminated_any = True
                # Continue, to close all instances if multiple are running
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
            # print(f"{addr}Error terminating process {process.info.get('name', 'N/A')}: {e}")
            continue
        except Exception as e_gen:
            # print(f"{addr}Generic error handling process {process.info.get('name', 'N/A')}: {e_gen}")
            continue

    if not terminated_any:
        # print(f"{addr}No running processes found matching '{cleaned_name}'.")
        pass
    return terminated_any


def close_application_by_path(app_name_query: str, addr: str = "") -> bool:
    """
    Closes an application by its executable path, obtained via GetFilePath.
    More precise if the process executable path can be determined.
    """
    cleaned_name = clean_app_name(app_name_query)
    if not cleaned_name:
        # print(f"{addr}close_application_by_path: Cleaned name is empty for query '{app_name_query}'.")
        return False

    # print(f"{addr}close_application_by_path: Finding path for '{cleaned_name}' to close.")
    app_path = GetFilePath(cleaned_name, addr + "GetFilePath (for close_by_path) -> ")

    if not app_path:
        # print(f"{addr}Could not find path for '{cleaned_name}' to close by path.")
        return False # Cannot proceed without a path

    # print(f"{addr}Found path '{app_path}'. Attempting to close processes with this executable path.")
    terminated_any = False
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            if proc.info['exe'] and os.path.exists(proc.info['exe']) and os.path.samefile(proc.info['exe'], app_path):
                pid = proc.pid
                # print(f"{addr}Found process '{proc.info['name']}' (PID: {pid}) with matching exe path '{app_path}'. Terminating...")
                psutil.Process(pid).terminate()
                # print(f"{addr}Terminated PID {pid}.")
                terminated_any = True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
            # print(f"{addr}Error terminating process PID {proc.pid if proc else 'N/A'} (path match): {e}")
            continue
        except FileNotFoundError: # os.samefile can raise this if proc.info['exe'] becomes invalid during iteration
            # print(f"{addr}File not found error for process exe path '{proc.info['exe']}'. Skipping.")
            continue
        except Exception as e:
            # print(f"{addr}Generic error comparing or terminating process for path '{app_path}': {e}")
            continue

    if not terminated_any:
        # print(f"{addr}No running process found with executable path '{app_path}'.")
        pass
    return terminated_any


def close_application(app_name_query: str, addr: str = "") -> bool:
    """
    Primary function to close an application.
    It first attempts to close by name. If that fails or finds nothing,
    it attempts to close by path as a fallback.
    This replaces the original `close_application` function.
    """
    # print(f"{addr}close_application (dispatcher): Received query '{app_name_query}'.")

    closed_by_name = close_application_by_name(app_name_query, addr + "AttemptCloseByName -> ")
    if closed_by_name:
        # print(f"{addr}Successfully closed '{app_name_query}' by name.")
        return True

    # print(f"{addr}Failed to close '{app_name_query}' by name, or no instances found. Trying by path.")
    closed_by_path = close_application_by_path(app_name_query, addr + "AttemptCloseByPath -> ")
    if closed_by_path:
        # print(f"{addr}Successfully closed '{app_name_query}' by path.")
        return True

    # print(f"{addr}Failed to close '{app_name_query}' by any method (name or path).")
    return False
