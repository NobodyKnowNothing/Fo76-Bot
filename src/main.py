'''
Created on May 4, 2024

@author: NobodyKnowNothing
'''
# 900w x 600w
import keyboard
import pyautogui
pi = math.pi
# Remember to fix pixel color


def main():
    while True:
        walk(pi/4, 10)
    """
    # Specify the path to the image you want to locate
    image_path = 'test.png'wa
    # Check if the image is found
    while True:
        print("check")
        try:
            image_location = pyautogui.locateOnScreen(image_path)
        except Exception as e:
            print(f"fail: {e}")
        try:
            if image_location != '':
                print("Image found at:", image_location)
                # image_location contains the coordinates of the top-left corner of the image and its width and height
                # You can access these values individually like this:
                x, y, width, height = image_location
                break
            else:
                print("Image not found")
        except Exception as e:
            print(f"fail1: {e}")
    print("done")
    """


if __name__ == '__main__':
    main()
