import pygetwindow as gw

# Get a list of all currently open windows
windows = gw.getAllTitles()

# Filter out background or non-visible windows
visible_windows = [window for window in windows if gw.getWindowsWithTitle(window)[0]]
# visible_windows=[]
''' 

for i in range(len(visible_windows1)):
    if visible_windows1[i].visible():
        visible_windows.append(visible_windows1[i])

'''
# Check if there are at least two visible windows
if len(visible_windows) >= 2:
    # Focus on the second visible window
    second_window = gw.getWindowsWithTitle(visible_windows[2])[0]
    second_window.activate()
    print(f"Switched focus to: {second_window.title}", visible_windows)
else:
    print("Not enough visible windows to switch to the second window.")
