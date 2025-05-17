'''
Created on May 5, 2024

@author: NobodyKnowNothing
'''

import math
from input import MoveMouse

import threading
import time

pi = math.pi


def look(disx, disy):  # 0/2pi is forward
    thread = threading.Thread(target=lookthread, args=(disx, disy,))

    thread.start()

    thread.join()


def lookthread(disx, disy):
    count = 0
    max = disx
    min = disy
    if max < disy:
        max = disy
        min = disx
    gap = max // min
    while count <= max:
        if count % gap == 0:
            MoveMouse(1, 1)
        elif max == disx:
            MoveMouse(1, 0)
        elif max == disy:
            MoveMouse(0, 1)
        count += 1


while True:
    look(100, 20)
