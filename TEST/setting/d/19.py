import subprocess

try:
    subprocess.call(["control.exe", "/name", "Microsoft.NetworkAndSharingCenter"])  # Open Network and Sharing Center
except:
    print("Error opening Network and Sharing Center.")
