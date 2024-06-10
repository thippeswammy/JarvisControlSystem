import time

import pyautogui

time.sleep(5)
# Locate the message input field
message_box = pyautogui.locateOnScreen(region=(800, 400, 800, 200), image="D:\whatsapp_message_input_field1.png")

# Click on the message input field
pyautogui.click(message_box)

# Type the message
pyautogui.write("Your message")

# Locate the send button
send_button = pyautogui.locateOnScreen(region=(1800, 600, 100, 100), image="D:\whatsapp_message_input_field.png")

# Click on the send button
pyautogui.click(send_button)
