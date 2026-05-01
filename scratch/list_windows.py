from pywinauto import Desktop
desktop = Desktop(backend="uia")
for win in desktop.windows():
    print(f"'{win.window_text()}'")
