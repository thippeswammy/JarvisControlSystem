import time

from selenium import webdriver
from selenium.webdriver.common.keys import Keys

# Provide the path to your Chrome WebDriver
chrome_driver_path = 'C:\Program Files\Google\Chrome\Application\chrome.exe'

# Initialize Chrome WebDriver
driver = webdriver.Chrome()
driver.get('https://web.whatsapp.com/')

# Wait for the user to scan the QR code to log in
while True:
    try:
        driver.find_element_by_xpath("//div[contains(@class, 'QBdPU')]")
        break
    except:
        pass
    time.sleep(1)

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
