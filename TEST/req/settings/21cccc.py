import subprocess

result = subprocess.run('netsh wlan show interfaces', capture_output=True, text=True, shell=True)
output_lines = result.stdout.split('\n')

for line in output_lines:
    if 'SSID' in line:
        ssid = line.split(':')[1].strip()
        print(f"SSID: {ssid}")
