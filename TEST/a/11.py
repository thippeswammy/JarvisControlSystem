import subprocess

# Replace 'path_to_your_shortcut.lnk' with the actual path to your .lnk file
shortcut_path = r'C:\Users\thipp\Desktop\This PC.lnk'

# os.startfile(shortcut_path)
subprocess.Popen(shortcut_path, shell=True)
