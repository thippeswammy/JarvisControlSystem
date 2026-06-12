import subprocess

binary = "native/Microsoft-UI-UIAutomation/src/UIAutomation/x64/Release/UIAutomationServer.exe"
print(f"Running {binary}...")

p = subprocess.Popen([binary], cwd="native/Microsoft-UI-UIAutomation/src/UIAutomation/x64/Release", stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

# Send initialize
p.stdin.write('{"jsonrpc": "2.0", "method": "initialize", "params": {"use_remote_operations": false}, "id": 1}\n')
p.stdin.flush()

# Read response
stdout_line = p.stdout.readline()
print("STDOUT response:", repr(stdout_line))

stderr_content = p.stderr.read()
print("STDERR response:", repr(stderr_content))

p.terminate()
p.wait()
print("Exit code:", p.returncode)
