import subprocess
import pandas as pd


def run_powershell_command(command):
    process = subprocess.Popen(["powershell", "-Command", command], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    output = stdout.decode('utf-8')
    error = stderr.decode('utf-8')
    return output, error


# PowerShell commands to get the list of installed applications from various registry paths and WMI
commands = [
    """
    Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows_icon\\CurrentVersion\\Uninstall\\*,
    HKLM:\\Software\\WOW6432Node\\Microsoft\\Windows_icon\\CurrentVersion\\Uninstall\\*,
    HKCU:\\Software\\Microsoft\\Windows_icon\\CurrentVersion\\Uninstall\\* |
    Select-Object DisplayName, DisplayVersion, Publisher, InstallDate |
    Where-Object {$_.DisplayName -and $_.DisplayName -ne ""} |
    Sort-Object DisplayName
    """,
    """
    Get-WmiObject -Query "SELECT Name, Version, Vendor, InstallDate FROM Win32_Product" |
    Select-Object Name, Version, Vendor, InstallDate |
    Sort-Object Name
    """
]

installed_apps = []

for command in commands:
    output, error = run_powershell_command(command)

    if error:
        print("Error:", error)
    else:
        # Split the output into lines
        lines = output.split('\n')

        # Process each line and extract application details
        for line in lines[3:]:  # Skip the header lines
            parts = line.split(maxsplit=3)
            if len(parts) >= 4:
                install_date = parts[3].strip()
                publisher = parts[2].strip()
                display_version = parts[1].strip()
                display_name = parts[0].strip()
                installed_apps.append({
                    'DisplayName': display_name,
                    'DisplayVersion': display_version,
                    'Publisher': publisher,
                    'InstallDate': install_date
                })
            elif len(parts) == 3:
                publisher = parts[2].strip()
                display_version = parts[1].strip()
                display_name = parts[0].strip()
                installed_apps.append({
                    'DisplayName': display_name,
                    'DisplayVersion': display_version,
                    'Publisher': publisher,
                    'InstallDate': ""
                })
            elif len(parts) == 2:
                display_version = parts[1].strip()
                display_name = parts[0].strip()
                installed_apps.append({
                    'DisplayName': display_name,
                    'DisplayVersion': display_version,
                    'Publisher': "",
                    'InstallDate': ""
                })
            elif len(parts) == 1:
                display_name = parts[0].strip()
                installed_apps.append({
                    'DisplayName': display_name,
                    'DisplayVersion': "",
                    'Publisher': "",
                    'InstallDate': ""
                })

# Create a DataFrame
df = pd.DataFrame(installed_apps)

# Display the DataFrame
print(df)

# Save the DataFrame to an Excel file
df.to_excel('installed_apps.xlsx', index=False)
