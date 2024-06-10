import subprocess

subprocess.run('netsh interface set interface "Wi-Fi" admin=enable', shell=True)

print("Wi-Fi enabled")
