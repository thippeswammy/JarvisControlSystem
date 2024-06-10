import pygetwindow as gw

# Get all windows and filter only visible ones
visible_windows = [window.title for window in gw.getAllWindows() if window.isVisible]

# Print titles of visible windows
for window_title in visible_windows:
    print(window_title)
