import pygetwindow as gw

# Get all open windows
windows = gw.getAllTitles()

# Print the names of all open windows
for window in windows:
    print(window)
