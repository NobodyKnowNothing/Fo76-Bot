'''
Created on May 4, 2024

@author: NobodyKnowNothing
'''
import win32con
import ctypes
import time


class WindowsInputSimulator:
    def __init__(self):
        PUL = ctypes.POINTER(ctypes.c_ulong)
        # Define the INPUT structure

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

        self.KEYBDINPUT = KeyBdInput
        self.INPUT_I = Input_I
        self.INPUT = Input

        self.MOUSEINPUT = MouseInput

        # Retrieve scan codes dynamically
        self.scan_codes = {"ESC": 0x01, "1": 0x02, "2": 0x03, "3": 0x04, "4": 0x05, "5": 0x06, "6": 0x07, "7": 0x08, "8": 0x09, "9": 0x0A,
                           "0": 0x0B, "MINUS": 0x0C, "EQUAL": 0x0D, "BACKSPACE": 0x0E, "TAB": 0x0F, "Q": 0x10, "W": 0x11, "E": 0x12,
                           "R": 0x13, "T": 0x14, "Y": 0x15, "U": 0x16, "I": 0x17, "O": 0x18, "P": 0x19, "LEFT_BRACKET": 0x1A,
                           "RIGHT_BRACKET": 0x1B, "ENTER": 0x1C, "LEFT_CTRL": 0x1D, "A": 0x1E, "S": 0x1F, "D": 0x20, "F": 0x21, "G": 0x22,
                           "H": 0x23, "J": 0x24, "K": 0x25, "L": 0x26, "SEMICOLON": 0x27, "APOSTROPHE": 0x28, "GRAVE": 0x29,
                           "LEFT_SHIFT": 0x2A, "BACKSLASH": 0x2B, "Z": 0x2C, "X": 0x2D, "C": 0x2E, "V": 0x2F, "B": 0x30, "N": 0x31,
                           "M": 0x32, "COMMA": 0x33, "PERIOD": 0x34, "SLASH": 0x35, "RIGHT_SHIFT": 0x36, "NUM_ASTERISK": 0x37,
                           "LEFT_ALT": 0x38, "SPACE": 0x39, "CAPS_LOCK": 0x3A, "F1": 0x3B, "F2": 0x3C, "F3": 0x3D, "F4": 0x3E, "F5": 0x3F,
                           "F6": 0x40, "F7": 0x41, "F8": 0x42, "F9": 0x43, "F10": 0x44, "NUM_LOCK": 0x45, "SCROLL_LOCK": 0x46,
                           "NUM_7": 0x47, "NUM_8": 0x48, "NUM_9": 0x49, "NUM_MINUS": 0x4A, "NUM_4": 0x4B, "NUM_5": 0x4C, "NUM_6": 0x4D,
                           "NUM_PLUS": 0x4E, "NUM_1": 0x4F, "NUM_2": 0x50, "NUM_3": 0x51, "NUM_0": 0x52, "NUM_PERIOD": 0x53,
                           "F11": 0x57, "F12": 0x58, "F12": 0x58, "ARROWD": 0x50
                           }

        # Define mouse click constants
        self.mouse_clicks = {
            "LEFTD": win32con.MOUSEEVENTF_LEFTDOWN,
            "RIGHTD": win32con.MOUSEEVENTF_RIGHTDOWN,
            "MIDDLED": win32con.MOUSEEVENTF_MIDDLEDOWN,
            "LEFTU": win32con.MOUSEEVENTF_LEFTUP,
            "RIGHTU": win32con.MOUSEEVENTF_RIGHTUP,
            "MIDDLEU": win32con.MOUSEEVENTF_MIDDLEUP
        }

    def press_key(self, hexKeyCode):
        extra = ctypes.c_ulong(0)
        ii_ = self.INPUT_I()
        ii_.ki = self.KEYBDINPUT(
            0, hexKeyCode, 0x0008, 0, ctypes.pointer(extra))
        x = self.INPUT(ctypes.c_ulong(1), ii_)
        ctypes.windll.user32.SendInput(1, ctypes.byref(x), ctypes.sizeof(x))

    def release_key(self, hexKeyCode):
        extra = ctypes.c_ulong(0)
        ii_ = self.INPUT_I()
        ii_.ki = self.KEYBDINPUT(
            0, hexKeyCode, 0x0008 | 0x0002, 0, ctypes.pointer(extra))
        x = self.INPUT(ctypes.c_ulong(1), ii_)
        ctypes.windll.user32.SendInput(1, ctypes.byref(x), ctypes.sizeof(x))

    def press(self, key, time2):
        hexCode = self.scan_codes[key.upper()]
        self.press_key(hexCode)
        time.sleep(time2)
        self.release_key(hexCode)

    def arrow(self, key):
        arrows = {"up": 0x48, "down": 0x50, "left": 0x4B, "right": 0x4D}
        hexCode = arrows[key.lower()]
        self.press_key(0xE0)
        self.press_key(hexCode)
        time.sleep(0.01)
        self.release_key(0xE0)
        self.release_key(hexCode)

    def click_mouse(self, button):
        button1 = self.mouse_clicks[button.upper()+"D"]
        button2 = self.mouse_clicks[button.upper()+"U"]
        inputs = [
            self.INPUT(type=win32con.INPUT_MOUSE, ii=self.INPUT_I(
                mi=self.MOUSEINPUT(0, 0, 0, button1, 0, ctypes.pointer(ctypes.c_ulong(0))))),
            self.INPUT(type=win32con.INPUT_MOUSE, ii=self.INPUT_I(
                mi=self.MOUSEINPUT(0, 0, 0, button2, 0, ctypes.pointer(ctypes.c_ulong(0)))))
        ]
        ctypes.windll.user32.SendInput(len(inputs), ctypes.byref(
            inputs[0]), ctypes.sizeof(self.INPUT))
        time.sleep(0.1)

    def move_mouse(self, dx, dy):
        input_ = self.INPUT(type=win32con.INPUT_MOUSE, ii=self.INPUT_I(mi=self.MOUSEINPUT(
            dx, dy, 0, win32con.MOUSEEVENTF_MOVE, 0, ctypes.pointer(ctypes.c_ulong(0)))))
        ctypes.windll.user32.SendInput(
            1, ctypes.byref(input_), ctypes.sizeof(self.INPUT))

    def click_and_wait(self, button, wait_time):
        self.click_mouse(button)
        time.sleep(wait_time)

    def move_and_wait(self, dx, dy, wait_time):
        self.move_mouse(dx, dy)
        time.sleep(wait_time)

    def send_input(self, inputs):
        ctypes.windll.user32.SendInput(len(inputs), ctypes.byref(
            inputs[0]), ctypes.sizeof(self.INPUT))
