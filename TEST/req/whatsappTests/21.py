# Replace 'contact_name' with the name of the contact or group
contact_name = 'Satish Mam'

# Replace 'message_text' with the text you want to send
message_text = 'Hello, this is a AI test message.'

# Search for the contact or group
search_box = driver.find_element_by_xpath("//div[contains(@class, '_3FRCZ')]/label/input")
search_box.send_keys(contact_name)
search_box.send_keys(Keys.ENTER)

time.sleep(2)

# Locate the message input field and send the message
message_input = driver.find_element_by_xpath("//div[contains(@class, '_3u328')]")
message_input.send_keys(message_text)
message_input.send_keys(Keys.ENTER)

# Optional: Close the browser window after sending the message
# driver.quit()
