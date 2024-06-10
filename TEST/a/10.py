import subprocess


def search_in_windows(query):
    # Define the directory to search in (replace with your directory)
    search_directory = "C:\\Windows\\System32"

    # Construct the Windows command to perform the search
    command = f"dir {search_directory} /s /b | findstr /i {query}"

    # Execute the command and capture the output
    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    # Display the search results
    print(result.stdout)
    print("COMPLETED")


# Example: Search for 'example.txt' in the System32 directory
search_in_windows()
