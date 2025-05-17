'''
Created on May 4, 2024

@author: NobodyKnowNothing
'''
import ctypes
import win32api, win32con
import time

# C struct redefinitions
PUL = ctypes.POINTER(ctypes.c_ulong)
scan_codes = {
    "ESC": 0x01,
    "1": 0x02,
    "2": 0x03,
    "3": 0x04,
    "4": 0x05,
    "5": 0x06,
    "6": 0x07,
    "7": 0x08,
    "8": 0x09,
    "9": 0x0A,
    "0": 0x0B,
    "MINUS": 0x0C,
    "EQUAL": 0x0D,
    "BACKSPACE": 0x0E,
    "TAB": 0x0F,
    "Q": 0x10,
    "W": 0x11,
    "E": 0x12,
    "R": 0x13,
    "T": 0x14,
    "Y": 0x15,
    "U": 0x16,
    "I": 0x17,
    "O": 0x18,
    "P": 0x19,
    "LEFT_BRACKET": 0x1A,
    "RIGHT_BRACKET": 0x1B,
    "ENTER": 0x1C,
    "LEFT_CTRL": 0x1D,
    "A": 0x1E,
    "S": 0x1F,
    "D": 0x20,
    "F": 0x21,
    "G": 0x22,
    "H": 0x23,
    "J": 0x24,
    "K": 0x25,
    "L": 0x26,
    "SEMICOLON": 0x27,
    "APOSTROPHE": 0x28,
    "GRAVE": 0x29,
    "LEFT_SHIFT": 0x2A,
    "BACKSLASH": 0x2B,
    "Z": 0x2C,
    "X": 0x2D,
    "C": 0x2E,
    "V": 0x2F,
    "B": 0x30,
    "N": 0x31,
    "M": 0x32,
    "COMMA": 0x33,
    "PERIOD": 0x34,
    "SLASH": 0x35,
    "RIGHT_SHIFT": 0x36,
    "NUM_ASTERISK": 0x37,
    "LEFT_ALT": 0x38,
    "SPACE": 0x39,
    "CAPS_LOCK": 0x3A,
    "F1": 0x3B,
    "F2": 0x3C,
    "F3": 0x3D,
    "F4": 0x3E,
    "F5": 0x3F,
    "F6": 0x40,
    "F7": 0x41,
    "F8": 0x42,
    "F9": 0x43,
    "F10": 0x44,
    "NUM_LOCK": 0x45,
    "SCROLL_LOCK": 0x46,
    "NUM_7": 0x47,
    "NUM_8": 0x48,
    "NUM_9": 0x49,
    "NUM_MINUS": 0x4A,
    "NUM_4": 0x4B,
    "NUM_5": 0x4C,
    "NUM_6": 0x4D,
    "NUM_PLUS": 0x4E,
    "NUM_1": 0x4F,
    "NUM_2": 0x50,
    "NUM_3": 0x51,
    "NUM_0": 0x52,
    "NUM_PERIOD": 0x53,
    "F11": 0x57,
    "F12": 0x58,
}


class KeyBdInput(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort),
                ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]


class HardwareInput(ctypes.Structure):
    _fields_ = [("uMsg", ctypes.c_ulong),
                ("wParamL", ctypes.c_short),
                ("wParamH", ctypes.c_ushort)]


class MouseInput(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long),
                ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]


class Input_I(ctypes.Union):
    _fields_ = [("ki", KeyBdInput),
                ("mi", MouseInput),
                ("hi", HardwareInput)]


class Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong),
                ("ii", Input_I)]

def set_pos(x, y):
    x = 1 + int(x * 65536./1920.)
    y = 1 + int(y * 65536./1080.)
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    ii_.mi = MouseInput(x, y, 0, (0x0001 | 0x8000), 0, ctypes.pointer(extra))
    command = Input(ctypes.c_ulong(0), ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(command), ctypes.sizeof(command))

def left_click():
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    ii_.mi = MouseInput(0, 0, 0, 0x0002, 0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(0), ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    ii_.mi = MouseInput(0, 0, 0, 0x0004, 0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(0), ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

# Actuals Functions


def PressKey(hexKeyCode):
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    ii_.ki = KeyBdInput(0, hexKeyCode, 0x0008, 0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(1), ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))


def ReleaseKey(hexKeyCode):
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    ii_.ki = KeyBdInput(0, hexKeyCode, 0x0008 | 0x0002, 0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(1), ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))


def MoveMouse(dx=0, dy=0):
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    # Assuming dwFlags 0x0001 for MOUSEEVENTF_MOVE
    ii_.mi = MouseInput(dx, dy, 0, 0x0001, 0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(0), ii_)  # Assuming type 0 for mouse input
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

def click(x, y, duration=30, delay=0.3): 
    win32api.SetCursorPos((x,y))
    time.sleep(0.05)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN,x,y,0,0)
    time.sleep(duration / 1000)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP,x,y,0,0)
    time.sleep(delay)

def xinput(x, waittime=0.01):
    try:
        for key in x:
            key = scan_codes[key.upper()]
            PressKey(key)
            time.sleep(waittime)
        x.reverse()
        for key in x:
            key = scan_codes[key.upper()]
            ReleaseKey(key)
            time.sleep(waittime)
        return 0
    except:
        try:
            return f"Input error: '{x}', at {key}."
        except:
            return f"Input error: '{x}'."

def input(x, waittime=0.05):
    try:
        key = scan_codes[x.upper()]
        PressKey(key)
        time.sleep(waittime)
        ReleaseKey(key)
        return 0
    except:
        return f"input error: '{x}'"

def inputs(words, waittime=0.1):
    for letter in words:
        out = False
        if letter == ' ': letter = "SPACE"
        if letter == '.': letter = "PERIOD"
        if letter == ':': 
            out = xinput(["LEFT_SHIFT", "SEMICOLON"])
        else:
            out = input(letter)
        if out != 0: print(out); time.sleep(9999)
        time.sleep(waittime)
