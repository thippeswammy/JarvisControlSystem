import time

from pywinauto.application import Application

# Connect to the WhatsApp window
app = Application(backend="uia").connect(title="WhatsApp Beta")
whatsapp_window = app.window(title="WhatsApp Beta")

# Replace 'contact_name' with the name of the contact or group
contact_name = 'ashwitha'
message_text = 'Hello, this is a test message.'

# Locate the chat input field and send a message
chat_input = whatsapp_window.child(control_type="Edit")

if chat_input:
    chat_input.set_text(contact_name)
    chat_input.type_keys('{ENTER}')  # Activate the chat

    time.sleep(2)  # Wait for chat activation

    chat_input.set_text(message_text)
    chat_input.type_keys('{ENTER}')  # Send the message
