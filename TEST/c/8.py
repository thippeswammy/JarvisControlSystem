import pyautogui

# Define the tab position (relative to the top left corner)
tab_x, tab_y = 100, 50

# Click the desired tab position
pyautogui.click(tab_x, tab_y)

# Alternatively, use keyboard shortcuts
pyautogui.hotkey("ctrl", "2")  # Switch to second tab

# Get the current window title (assumes browser window title reflects the tab title)
current_title = pyautogui.getActiveWindowTitle()

print(f"Switched to tab with title: {current_title}")
