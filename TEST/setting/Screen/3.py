import os

import pyautogui
import pytesseract
from PIL import Image

# Set the TESSDATA_PREFIX environment variable (replace with your own path)
os.environ['TESSDATA_PREFIX'] = r'D:\Installs\Tesseract-OCR'

# Set the path to the Tesseract executable (replace with your own path)
pytesseract.pytesseract.tesseract_cmd = r'D:\Installs\Tesseract-OCR\tesseract.exe'


def move_mouse_to_text(text):
    # Capture the screen
    screenshot = pyautogui.screenshot()

    # Save the screenshot as an image file
    screenshot.save('screenshot.png')

    # Use Tesseract to perform OCR on the image
    detected_text = pytesseract.image_to_string(Image.open('screenshot.png'))

    # Check if the desired text is present in the detected text
    if text.lower() in detected_text.lower():
        # Find the coordinates of the text on the screen
        location = pyautogui.locateOnScreen('screenshot.png', confidence=0.8)

        if location:
            # Move the mouse to the center of the detected region
            print(location)
            x, y, w, h = location.left, location.top, location.width, location.height
            pyautogui.moveTo(x + 0.5 * w, y + 0.5 * h)
            print(f"Mouse moved to the position of '{text}'.", x, y, w, h)
        else:
            print(f"Unable to find the position of '{text}'.")
    else:
        print(f"The text '{text}' is not displayed on the screen.")


# Example usage:
text_to_check = "Screen"
move_mouse_to_text(text_to_check)
