import pytesseract
import time
import win32con
import win32gui
import pyautogui
from PIL import Image
from press import WindowsInputSimulator
import numpy as np
import cv2 # Import OpenCV

inputs = WindowsInputSimulator()
path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Path to Tesseract executable

def tesseract_path_init(input_path):
    global path
    path = input_path

def switch_to_application(window_title):
    try:
        hwnd = win32gui.FindWindow(None, window_title)
        if hwnd == 0:
            print(f"Window '{window_title}' not found")
            return False
        
        # Use SW_SHOW instead of SW_RESTORE for a more reliable activation
        win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
        win32gui.SetForegroundWindow(hwnd)
        return True
    except Exception as e:
        print(f"Error occurred while switching to window: {e}")
        return False

def screenshot():
    # Take a screenshot of the window
    if switch_to_application("Fallout76"):
        # pyautogui is fine, but consider mss for higher performance if needed
        screenshot_img = pyautogui.screenshot(region=(0, 0, 1280, 800))
        return screenshot_img
    return None

def readui(playing, vers):
    global path
    print("Reading text")
    pytesseract.pytesseract.tesseract_cmd = path

    screenshot1_pil = screenshot()
    if screenshot1_pil is None:
        return ""

    # Convert PIL Image to an OpenCV/NumPy array.
    # OpenCV uses BGR color order, so we convert from RGB.
    frame1 = cv2.cvtColor(np.array(screenshot1_pil), cv2.COLOR_RGB2BGR)

    if playing:
        # This loop is a fixed 1.5s delay. If it's not essential, removing it is the biggest time save.
        for _ in range(30):
            inputs.move_mouse(10, 10)
            time.sleep(0.05)
        
        screenshot2_pil = screenshot()
        if screenshot2_pil is None:
            return ""
        frame2 = cv2.cvtColor(np.array(screenshot2_pil), cv2.COLOR_RGB2BGR)
        
        # OPTIMIZATION 1: Use NumPy/OpenCV for fast image comparison
        # This replaces your first pixel-by-pixel loop
        diff = cv2.absdiff(frame1, frame2)
        # Convert difference to grayscale to create a mask
        mask = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        # If the difference is below a threshold, it's considered static
        threshold = 15
        static_mask = mask < threshold
        
        # Create a black image and copy only the static parts from the original frame
        processed_image = np.zeros_like(frame1)
        processed_image[static_mask] = frame1[static_mask]
    else:
        processed_image = frame1

    # OPTIMIZATION 2: Use cv2.inRange for ultra-fast color filtering
    # This replaces your second and third pixel-by-pixel loops
    if vers == 0:
        # Note: OpenCV uses BGR, so the order is (Blue, Green, Red)
        yellow_lower = np.array([0, 130, 130])
        yellow_upper = np.array([100, 255, 255])
    elif vers == 1:
        yellow_lower = np.array([100, 130, 130])
        yellow_upper = np.array([203, 255, 255])

    # Create a mask containing only the pixels within the yellow range
    yellow_mask = cv2.inRange(processed_image, yellow_lower, yellow_upper)
    
    # Create a final black image. Pixels that were yellow will be turned white.
    final_image = np.zeros_like(yellow_mask)
    final_image[yellow_mask > 0] = 255 # Make yellow pixels white

    # OPTIMIZATION 3: Configure Tesseract for better performance
    # --psm 6: Assume a single uniform block of text.
    # --psm 7: Treat the image as a single text line.
    # Experiment to see which works best for your use case.
    custom_config = r'--oem 3 --psm 6'
    
    try:
        # Perform OCR directly on the NumPy array (Pillow conversion is handled by pytesseract)
        text = str(pytesseract.image_to_string(final_image, lang="eng", config=custom_config))
    except Exception as e:
        print(f"Error during OCR: {e}")
        text = ""
        
    return text.lower()