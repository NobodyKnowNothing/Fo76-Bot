from input import input
import math


def walk(angle, time):  # 0/2pi is forward
    y = math.sin(angle) * time
    x = math.cos(angle) * time
    thread1 = threading.Thread(target=walkx, args=(x,))
    thread2 = threading.Thread(target=walky, args=(y,))

    thread1.start()
    thread2.start()

    thread1.join()
    thread2.join()


def walkx(x):
    if x > 0:
        print("Walking forward")
        input("w", x)
    elif x < 0:
        print("Walking backward")
        input("s", abs(x))


def walky(y):
    if y > 0:
        print("Walking left")
        input("a", y)
    elif y < 0:
        print("Walking right")
        input("d", abs(y))
