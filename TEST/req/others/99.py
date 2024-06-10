import subprocess


def search_in_windows(query):
    # Construct the PowerShell command to perform the search
    command = f"powershell -command \"Get-ChildItem -Path 'C:\\' -Recurse | Where-Object {{ $_.Name -match '{query}' }}\""

    # Execute the PowerShell command
    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    # Print the search result
    print(result.stdout)


# Example: Search for 'example.txt'
search_in_windows('goog')
