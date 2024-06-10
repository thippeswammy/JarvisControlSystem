from pywinauto import Application

app = Application(backend="win32").connect(title="Start")  # Connect to the Start menu
search_bar = app.window(title="Search").child_window(auto_id="SearchBox")  # Identify the search bar element

# Open the search bar
search_bar.click()

# Type some text
search_bar.type_keys("Hello world!")
