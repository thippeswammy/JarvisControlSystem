import subprocess

# Example: Show available WiFi networks
output = subprocess.run(['netsh', 'wlan', 'show', 'network'], capture_output=True, text=True)
print(output.stdout)
