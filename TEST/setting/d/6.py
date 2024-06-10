import subprocess

# Define the command to be executed in CMD
cmd_command = 'powershell -Command "Get-PnpDevice | Where-Object {$_.Class -eq \'Bluetooth\' -and $_.Status -ne \'OK\'} | Enable-PnpDevice -Confirm:$false"'

# Execute the command in CMD
subprocess.run(cmd_command, shell=True)
