from pywinauto.application import Application

# Replace 'YourWindowTitle' with the title of your window
app = Application(backend="uia").connect(title="YourWindowTitle")

# Replace 'TabTitle' with the title of your tab (or any identifier)
tab = app.window(title="TabTitle")
tab.set_focus()
