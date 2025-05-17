import pytesseract
import time
import win32con
import win32gui
import pyautogui
from PIL import Image
from press import WindowsInputSimulator
inputs = WindowsInputSimulator()
path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Path to Tesseract executable

def tesseract_path_init(input_path):
    global path
    path = input_path

def switch_to_application(window_title):
    success = False
    try:
        # Find the window handle of the target application by its title
        hwnd = win32gui.FindWindow(None, window_title)
        if hwnd == 0:
            print("Window not found")

        # Bring the window to the foreground
        # Restore window if minimized
        tries = 0
        while not success and tries < 9:
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                time.sleep(0.1)
                win32gui.SetForegroundWindow(hwnd)

                success = True
            except:
                tries += 1
                time.sleep(5)
            if tries >= 9:
                raise "Could not set window to foreground after 9 attempts"
    except:
        print("Error occurred while finding window")
    return success


def screenshot():
    # Take a screenshot of the window
    if switch_to_application("Fallout76"):
        screenshot = pyautogui.screenshot(
            region=(0, 0, 1280, 800))
    else:
        screenshot = ""
    return screenshot


def readui(playing, vers):
    global path
    print("Reading text")
    # Set the path to the Tesseract executable (if it's not in your PATH)
    pytesseract.pytesseract.tesseract_cmd = path
    # Load the two screenshots
    # Need to take 2 screenshots
    screenshot1 = screenshot()
    if playing:
        for i in range(30):
            inputs.move_mouse(10, 10)
            time.sleep(0.05)
        screenshot2 = screenshot()
    if vers == 0:
        yellow_lower = (130, 130, 0)
        yellow_upper = (255, 255, 100)
    elif vers == 1:
        yellow_lower = (130, 130, 100)
        yellow_upper = (255, 255, 203)

    # Define a threshold for pixel similarity
    threshold = 15  # You may need to adjust this value based on your specific requirements

    # Create a new image to store the result
    if playing:
        result_image = Image.new('RGB', screenshot1.size)
        # Process the images pixel by pixel
        for y in range(screenshot1.size[1]):
            for x in range(screenshot1.size[0]):
                pixel1 = screenshot1.getpixel((x, y))
                pixel2 = screenshot2.getpixel((x, y))

                # Calculate the Euclidean distance between the RGB values of the two pixels
                distance = sum((a - b) ** 2 for a,
                               b in zip(pixel1, pixel2)) ** 0.5

                # Check if the distance is below the threshold
                if distance < threshold:
                    # If pixels are similar, use the pixel from the first screenshot
                    result_image.putpixel((x, y), pixel1)
                else:
                    # If pixels are not similar, use a black pixel
                    result_image.putpixel((x, y), (0, 0, 0))
    else:
        result_image = screenshot1

    image = result_image
    # Process the image to make all pixels except yellow ones black
    try:
        for y in range(image.size[1]):
            for x in range(image.size[0]):
                pixel = image.getpixel((x, y))
                if not (yellow_lower[0] <= pixel[0] <= yellow_upper[0] and
                        yellow_lower[1] <= pixel[1] <= yellow_upper[1] and
                        yellow_lower[2] <= pixel[2] <= yellow_upper[2]):
                    # Make non-yellow pixels black
                    image.putpixel((x, y), (0, 0, 0))
                    # Process the image to make yellow pixels more white

        for y in range(image.size[1]):
            for x in range(image.size[0]):
                pixel = image.getpixel((x, y))
                if yellow_lower[0] <= pixel[0] <= yellow_upper[0] and \
                        yellow_lower[1] <= pixel[1] <= yellow_upper[1] and \
                        yellow_lower[2] <= pixel[2] <= yellow_upper[2]:
                    # Increase RGB values to make yellow pixels more white
                    image.putpixel((x, y), (255, 255, 255))
        # Perform OCR on the image
        text = str(pytesseract.image_to_string(image, lang="eng"))
        # Print the extracted text
    except:
        text = ""
    return text.lower()
