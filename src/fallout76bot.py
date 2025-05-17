'''
Created on May 5, 2024

@author: NobodyKnowNothing
'''

import cv2
import numpy as np
import pyautogui


import cv2
import numpy as np
import pyautogui


def get_marker_location(marker_image):
    map_image = pyautogui.screenshot(region=(x_start, y_start, width, height))
    map_image = cv2.cvtColor(np.array(map_image), cv2.COLOR_RGB2BGR)

    marker_template = cv2.imread(marker_image, cv2.IMREAD_GRAYSCALE)
    w, h = marker_template.shape[::-1]

    res = cv2.matchTemplate(map_image, marker_template, cv2.TM_CCOEFF_NORMED)
    threshold = 0.8
    loc = np.where(res >= threshold)

    if len(loc[0]) > 0:
        return (loc[1][0] + w / 2, loc[0][0] + h / 2)
    else:
        return None


def calculate_distance_vector(player_pos, target_pos):
    if player_pos is None or target_pos is None:
        return None
    else:
        dx = target_pos[0] - player_pos[0]
        dy = target_pos[1] - player_pos[1]
        distance_vector = np.array([dx, dy])
        distance_magnitude = np.linalg.norm(distance_vector)
        return distance_vector, distance_magnitude


# Set the region of the screen where the map is located
x_start, y_start, width, height = 100, 100, 800, 600

# Load marker images
player_marker = 'player_marker.png'

# Get the locations of player marker
player_pos = get_marker_location(player_marker)

# Assuming target marker is a rotating triangle, you might need a different approach to locate it
target_marker = 'target_marker.png'

# Get the locations of target marker
target_pos = get_marker_location(target_marker)

# Calculate distance vector and magnitude
distance_vector, distance_magnitude = calculate_distance_vector(
    player_pos, target_pos)

if distance_vector is not None:
    print("Distance Vector:", distance_vector)
    print("Distance Magnitude:", distance_magnitude)
else:
    print("Marker not found.")
