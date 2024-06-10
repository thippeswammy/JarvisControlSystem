import time

from pywinauto.application import Application

time.sleep(5)
# Locate the WhatsApp window and send a message
app = Application(backend="uia").connect(title="WhatsApp Beta")
whatsapp_window = app.window(title="WhatsApp Beta")

# Locate the chat input field and send a message
chat_input = whatsapp_window.child(control_type="Edit", found_index=1)
if chat_input:
    chat_input.set_text("Your message here")

# Simulate button click to send the message (hypothetical, actual element IDs may vary)
send_button = whatsapp_window.child(title="Send")
if send_button:
    send_button.click()
