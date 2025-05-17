import pygetwindow as gw
import pyautogui
import time
from python_imagesearch.imagesearch import imagesearch
import numpy as np
import cv2


def gamescreenshot(game_title):
    # Get the game window
    game_windows = gw.getWindowsWithTitle(game_title)
    if game_windows:
        print("Game windows found:")
        for window in game_windows:
            print(window.title)
        # Assume the first window is the correct one
        game_window = game_windows[0]
        game_window.activate()
        # Get the position and size of the game window
        left, top, width, height = game_window.left, game_window.top, game_window.width, game_window.height
        # Adjusting the region to capture a larger area around the game window
        capture_region = (left, int(height//2), width//2, height//2)

        start_time = time.time()  # Start time for profiling
        screenshot = pyautogui.screenshot(region=capture_region)
        print("Screenshot captured in {:.2f} seconds".format(
            time.time() - start_time))  # Print capture time

        # Convert the screenshot to OpenCV format
        screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        return screenshot, width, height
    else:
        print("Game window not found")
        return None


def find_icon(template_path, screenshot):
    # Use imagesearch library to find the template icon in the screenshot
    positions = imagesearch(template_path, screenshot)
    return positions


def eventcheck():
    # Paths to the template icon and the screenshot
    icon_path = "pubeventicon.png"
    game_title = "Fallout76"
    screenshot, width, height = gamescreenshot(game_title)
    # Load the template icon
    if screenshot is not None:
        # Display the captured screenshot
        cv2.imshow("Captured Screenshot", screenshot)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

        # Find the icon in the screenshot
        icon_position = find_icon(icon_path, screenshot)
        if icon_position:
            print("Icon found at positions:", icon_position)
            for pos in icon_position:
                # Overlay the icon on the screenshot for visualization
                icon_image = cv2.imread(icon_path, cv2.IMREAD_UNCHANGED)
                icon_height, icon_width = icon_image.shape[:2]
                x, y = pos
                # Overlay icon ignoring alpha channel
                screenshot[y:y+icon_height, x:x +
                           icon_width] = icon_image[:, :, :3]
            # Display the screenshot with the overlaid icon
            cv2.imshow("Screenshot with Icon", screenshot)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        else:
            print("Icon not found")

    else:
        print("Failed to capture screenshot")


if __name__ == "__main__":
    eventcheck()
