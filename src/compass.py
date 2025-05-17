'''
Created on May 5, 2024

@author: NobodyKnowNothing
'''
import pyautogui
from PIL import Image

import cv2
import numpy as np
from PIL import ImageGrab  # For capturing the screen


def find_image_on_screen(template_path, screen, y_value, threshold=0.8):
    # Read the template image
    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
    screen = np.array(screen)
    # Convert the screen capture to grayscale
    screen_gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)

    # Perform template matching
    result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)

    # Find the locations where the template matches above a threshold
    loc = np.where(result >= threshold)

    closest_x = None
    min_distance = float('inf')

    # Iterate through the matched locations
    for pt in zip(*loc[::-1]):
        print("e1")
        # Compute the x position of the middle of the matched rectangle
        x_middle = pt[0] + template.shape[1] // 2

        # Compute the distance between the middle x position and the specified y value
        distance = abs(pt[1] + template.shape[0] // 2 - y_value)

        # Update closest_x if the current distance is smaller
        if distance < min_distance:
            closest_x = x_middle
            min_distance = distance

    return closest_x


def get_window_size(window_title):
    window = pyautogui.getWindowsWithTitle(window_title)[0]
    return window.width, window.height


def capture_screen(x, y, width, height):
    screenshot = pyautogui.screenshot(region=(x, y, width, height))
    return screenshot


def findcompass(image, start_x, start_y, color_threshold):
    img_width, img_height = image.size

    y = start_y
    while y >= 0:
        pixel_color = image.getpixel((start_x, y))
        if all(abs(component - target) <= color_threshold for component, target in zip(pixel_color, TARGET_COLOR)):
            liney = y
            print(f"found: {y}")
            break
        y -= 1
    linecol = pixel_color
    endline = True
    x = start_x
    while endline:
        pixel_color = image.getpixel((x, liney))
        if all(abs(component - target) <= color_threshold for component, target in zip(pixel_color, linecol)):
            rightend = x
        else:
            endline = False
        x += 1
    endline = True
    x = start_x
    while endline:
        pixel_color = image.getpixel((x, liney))
        if all(abs(component - target) <= color_threshold for component, target in zip(pixel_color, linecol)):
            leftend = x
        else:
            endline = False
        x -= 1

    return (rightend, y), (leftend, y), linecol


def downlist(x, start_y, length, line_color):
    global screenshot, COLOR_THRESHOLD
    image = screenshot
    height = image.height
    colours = []
    for y in range(start_y, start_y + length):
        pixel_color = image.getpixel((x-2, y))
        colours.append(pixel_color)
        if all(abs(component - target) <= COLOR_THRESHOLD for component, target in zip(pixel_color, line_color)):
            colours.append(pixel_color)
    return colours  # 7


def find_matching_pixel(image, start_x, end_x, start_y, color_threshold, line_color):

    img_width, img_height = image.size
    print(start_x, end_x, start_y, color_threshold, line_color)
    # Iterate over pixels underneath the line
    y = start_y + 2
    for x in range(start_x, end_x):
        pixel_color = image.getpixel((x, y))
        # Check if the pixel color matches the line color within the threshold
        if all(abs(component - target) <= COLOR_THRESHOLD for component, target in zip(pixel_color, line_color)):
            pyautogui.moveTo(x, y)
            return x, y  # Return the position of the matching pixel

    # If no matching pixel is found, return None
    return None


# Specify the window title
window_title = "Fallout76"

# Get the window size
window_width, window_height = get_window_size(window_title)

# Specify the starting position at the bottom center
start_x = window_width // 2
start_y = window_height - 1

# Specify the target color (in RGB format)
TARGET_COLOR = (255, 255, 203)

# Set the color threshold (how close should the color match)
COLOR_THRESHOLD = 40

# Capture the screen
screenshot = capture_screen(0, 0, window_width, window_height)
# Find the color line
left, right, linecol = findcompass(
    screenshot, start_x, start_y, COLOR_THRESHOLD)
matching_pixel = find_matching_pixel(
    screenshot, right[0], left[0], left[1], COLOR_THRESHOLD, linecol)
find_image_on_screen('north.png', screenshot, left[1])
xpos = find_image_on_screen('north.png', screenshot, left[1])
print(xpos)
print(f"e1: {left[0] - right[0]}")
print(round(
    (left[0] - right[0])*0.0641, 0))
print(f"f: {linecol}")
colors = downlist(matching_pixel[0], matching_pixel[1], int(round(
    (left[0] - right[0])*0.0641, 0)), linecol)
if left is not None:
    print(f"Found color line at y = {left[1]}")
else:
    print("Color line not found.")
print(right[0], left[0])
if matching_pixel is not None:
    print(f"Found matching pixel at position: {matching_pixel}")
else:
    print("Matching pixel not found.")
print(colors)
