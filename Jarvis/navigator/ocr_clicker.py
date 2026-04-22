import os
import difflib
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class VisualClicker:
    """
    Ultimate fallback: Uses OCR (easyocr) to physically read the screen
    and find the bounding box of text to click via PyAutoGUI.
    """
    
    def __init__(self):
        self._reader = None

    def _get_reader(self):
        """Lazy load easyocr since it takes a moment to initialize."""
        if self._reader is None:
            logger.info("Initializing EasyOCR Model (first time only)...")
            import easyocr
            # Load English only, using CPU or GPU depending on the system config
            self._reader = easyocr.Reader(['en'])
        return self._reader

    def find_text_coordinates(self, target_text: str, fuzzy_threshold: float = 0.7) -> Optional[Tuple[int, int]]:
        """
        Takes a screenshot, performs OCR, and finds the closest matching text.
        Returns the (x, y) center point of the bounding box, or None.
        """
        try:
            from PIL import ImageGrab
            import numpy as np
        except ImportError as e:
            logger.error(f"Missing image processing deps for OCR: {e}")
            return None

        logger.info(f"Visual Scan: Taking screenshot to find '{target_text}'...")
        
        # 1. Capture the primary screen
        screenshot = ImageGrab.grab(all_screens=False)
        img_array = np.array(screenshot)

        # 2. Run OCR
        reader = self._get_reader()
        logger.info("Visual Scan: Reading screen text...")
        results = reader.readtext(img_array)

        # results format: [([[x1,y1], [x2,y1], [x2,y2], [x1,y2]], 'text', prob), ...]
        
        best_match = None
        best_score = 0.0
        
        target_lower = target_text.lower().strip()

        for box, text, prob in results:
            text_lower = text.lower().strip()
            if not text_lower:
                continue
                
            # Direct substr check
            if target_lower in text_lower:
                score = 1.0
            else:
                s = difflib.SequenceMatcher(None, target_lower, text_lower)
                score = s.ratio()
                
                # Boost score if a significant word matches exactly (handles OCR split boxes)
                words = target_lower.split()
                if len(words) > 1:
                    for word in words:
                        if len(word) > 3 and word in text_lower:
                            score = max(score, 0.75)

            if score > best_score and score >= fuzzy_threshold:
                best_score = score
                best_match = (box, text, score)

        if not best_match:
            logger.warning(f"Visual Scan: Could not find '{target_text}' visually.")
            return None

        # Calculate center point
        box, matched_text, score = best_match
        logger.info(f"Visual Scan: Found '{matched_text}' (score: {score:.2f})")
        
        # box is [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
        x1, y1 = box[0]
        x2, y2 = box[2]
        
        center_x = int((x1 + x2) / 2)
        center_y = int((y1 + y2) / 2)
        
        return (center_x, center_y)

    def click_text(self, target_text: str) -> bool:
        """Finds the text via OCR and clicks its center coordinate."""
        try:
            import pyautogui
        except ImportError:
            logger.error("Visual Scan: PyAutoGUI is missing.")
            return False
            
        coords = self.find_text_coordinates(target_text)
        if coords is None:
            return False
            
        x, y = coords
        logger.info(f"Visual Scan: Clicking coordinates ({x}, {y})")
        
        # Physical mouse move & click
        pyautogui.moveTo(x, y, duration=0.2)
        pyautogui.click()
        return True
