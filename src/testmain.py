import psutil
import subprocess
import time
import win32con
import win32gui
from press import WindowsInputSimulator
from input import click
import datetime
import pyautogui
import os
from readtext import readui, tesseract_path_init
import sys
import os

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# --- Logger Setup ---
import logging
import logging.handlers
import os
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding as rsa_padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import base64
import sys # For sys.stderr

# --- Constants ---
LOG_FILENAME = 'fo76bot.log'
HARDCODED_PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAvgxSvDJ2gON+2rxpyCK1
4y9xDiFYXoLNxJqcs1W4ogxBBdFlwndAq13phId+HCPTZPUHsyFx1ofpfPw3KPku
KZU140VbJG5xri54UUNo7pO4EQKjtfFN4iFCiLWiG81P83I52+cpqGOJ1SznCM8g
quhhPG5IiOn3vhIA85XadLZyMo928diTo12AmjRzDLTYsVvAS/F8b8GTaBim18v4
idHz33Qav4IgzxyS5T5DTmC6zoRRgwXzZru+YV0dqOZ9en2KJIeJmpeJt2k/EhDP
xmIkENWSbJAcefRskS2CrZzwv301m9eaJKIT11S5fKK+WdL5t04wyNky2XwHnfAB
XQIDAQAB
-----END PUBLIC KEY-----"""
# Example of a placeholder key for testing the check in setup_logger
# HARDCODED_PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
# MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAyReplaceWithYourKey...
# -----END PUBLIC KEY-----"""


# --- Internal Logger for Logging System Diagnostics ---
_LOGGING_MODULE_NAME = __name__
# Use a very distinct name for this logger to avoid any conflicts
_INTERNAL_DEBUG_LOGGER_NAME = f"{_LOGGING_MODULE_NAME}.ENCRYPTION_DEBUG"
_internal_logger = logging.getLogger(_INTERNAL_DEBUG_LOGGER_NAME)
_internal_logger.handlers.clear() # Ensure no old handlers
_internal_logger.setLevel(logging.DEBUG) # Crucial: set logger level

_console_handler_internal = logging.StreamHandler(sys.stderr) # Explicitly use stderr
_console_handler_internal.setLevel(logging.DEBUG) # Crucial: set handler level
_console_handler_internal.setFormatter(
    logging.Formatter(f"INTERNAL-ENCRYPTION-DEBUG [%(levelname)s] %(name)s -> %(funcName)s:%(lineno)d: %(message)s")
)
_internal_logger.addHandler(_console_handler_internal)
_internal_logger.propagate = False # Do not pass to root
_internal_logger.disabled = True # Ensure it's not disabled

_internal_logger.info(f"Internal debug logger '{_INTERNAL_DEBUG_LOGGER_NAME}' configured and active.")

# --- Encryption Helper Functions ---
def load_public_key_from_string(pem_string):
    _internal_logger.debug("Attempting to load public key from PEM string.")
    try:
        public_key = serialization.load_pem_public_key(
            pem_string.encode('utf-8'),
            backend=default_backend()
        )
        _internal_logger.debug("Public key loaded successfully from PEM string.")
        return public_key
    except Exception as e:
        # This error is critical because if the key is provided but invalid, encryption is expected but will fail.
        _internal_logger.critical(f"CRITICAL ERROR loading public key from string: {e}. Encryption WILL FAIL if this key was intended for use.", exc_info=True)
        raise ValueError(f"Invalid public key PEM string: {e}")

def encrypt_message_hybrid(message_bytes, public_key):
    _internal_logger.debug("encrypt_message_hybrid called.")
    aes_key = os.urandom(32)
    iv = os.urandom(12) # GCM standard IV size is 12 bytes (96 bits)
    cipher = Cipher(algorithms.AES(aes_key), modes.GCM(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(message_bytes) + encryptor.finalize()
    tag = encryptor.tag # GCM tag, typically 16 bytes
    
    encrypted_aes_key = public_key.encrypt(
        aes_key,
        rsa_padding.OAEP(
            mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    # Concatenate: Encrypted AES Key + IV + GCM Tag + Ciphertext
    result_bytes = encrypted_aes_key + iv + tag + ciphertext
    result_b64 = base64.b64encode(result_bytes)
    _internal_logger.debug(f"encrypt_message_hybrid completed. Output base64 length: {len(result_b64)}")
    return result_b64

# --- Custom Formatter ---
class EncryptedFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None, style='%', public_key_pem_string=None, file_handler_level=logging.INFO):
        super().__init__(fmt, datefmt, style)
        self.formatter_id = id(self) # For tracking instance
        _internal_logger.info(f"EncryptedFormatter instance {self.formatter_id} __init__ starting.")
        self.public_key = None
        self._file_handler_level = file_handler_level # Used for conditional internal logging

        if public_key_pem_string:
            try:
                # Responsibility for checking if public_key_pem_string *is* a placeholder
                # (and thus shouldn't be used) primarily lies with the calling code (e.g., setup_logger).
                # Here, we attempt to load whatever string is given.
                # load_public_key_from_string will raise ValueError if it's not a valid PEM.
                self.public_key = load_public_key_from_string(public_key_pem_string)
                _internal_logger.info(f"EncryptedFormatter {self.formatter_id}: Successfully initialized public key.")
            except ValueError as e: # Raised by load_public_key_from_string for invalid PEM
                _internal_logger.error(f"EncryptedFormatter {self.formatter_id}: Failed to initialize public key (Invalid PEM string provided): {e}. Encryption will be skipped.")
            except Exception as e: # Other unexpected errors during key loading
                _internal_logger.error(f"EncryptedFormatter {self.formatter_id}: Unexpected error initializing public key: {e}. Encryption will be skipped.", exc_info=True)
        else:
            _internal_logger.warning(f"EncryptedFormatter {self.formatter_id}: No public key PEM string provided. Encryption will be skipped.")
        
        _internal_logger.info(f"EncryptedFormatter instance {self.formatter_id} __init__ finished. Public key is {'SET' if self.public_key else 'NOT SET'}.")

    def format(self, record):
        _internal_logger.debug(f"--- EncryptedFormatter {self.formatter_id} format() CALLED for record: {record.name} - {record.levelname} - '{str(record.msg)[:50]}...' ---")
        _internal_logger.debug(f"  Formatter {self.formatter_id}: Current self.public_key is {'SET' if self.public_key else 'NOT SET'}.")

        # Store original state that defines getMessage() behavior and cached formatted exception text
        original_msg = record.msg
        original_args = record.args
        # getattr is used because record.exc_text might not be set yet by any formatter.
        original_exc_text = getattr(record, 'exc_text', None) 

        # Get the fully substituted message. This call itself does not alter 'record.message'.
        # It uses the current record.msg and record.args.
        log_message_to_process = record.getMessage()
        _internal_logger.debug(f"  Formatter {self.formatter_id}: log_message_to_process = '{log_message_to_process[:100]}...'")

        # These will be temporarily set on the record for super().format()
        # Default to original values, meaning no encryption or modification initially.
        msg_for_formatting = original_msg
        args_for_formatting = original_args

        if self.public_key and log_message_to_process: # Ensure there's content to encrypt
            _internal_logger.debug(f"  Formatter {self.formatter_id}: Public key IS SET. Attempting encryption for: '{log_message_to_process[:50]}...'")
            try:
                message_to_encrypt_bytes = log_message_to_process.encode('utf-8')
                encrypted_msg_b64 = encrypt_message_hybrid(
                    message_to_encrypt_bytes,
                    self.public_key
                )
                msg_for_formatting = f"[ENCRYPTED]{encrypted_msg_b64.decode('utf-8')}"
                args_for_formatting = () # The message is now fully formed, no args needed for formatting
                _internal_logger.debug(f"  Formatter {self.formatter_id}: Encryption SUCCEEDED. msg_for_formatting is now: '{msg_for_formatting[:60]}...'")
            except Exception as e:
                _internal_logger.error(
                    f"  Formatter {self.formatter_id}: Encryption FAILED for record [{record.name}/{record.levelname}]. Error: {e}. Original msg: {log_message_to_process[:100]}...",
                    exc_info=True # Log this specific exception to the internal logger
                )
                # Fallback: format the original message with a prefix indicating failure
                msg_for_formatting = f"[ENCRYPTION_FAILED] {log_message_to_process}"
                args_for_formatting = ()
                _internal_logger.debug(f"  Formatter {self.formatter_id}: msg_for_formatting after encryption failure: '{msg_for_formatting[:60]}...'")
        
        elif not self.public_key:
            _internal_logger.warning(f"  Formatter {self.formatter_id}: Public key IS NOT SET. Skipping encryption for '{log_message_to_process[:50]}...'.")
            # This internal warning is for diagnostics; the actual log record will be formatted plainly.
            if record.levelno >= self._file_handler_level: 
                 _internal_logger.warning(
                    f"  Formatter {self.formatter_id}: Public key not available for record [{record.name}/{record.levelname}]. "
                    f"Logging plain to file: '{log_message_to_process[:100]}...'"
                )
            # msg_for_formatting and args_for_formatting correctly remain as original_msg, original_args
        
        else: # log_message_to_process is empty (e.g. logger.info(""))
            _internal_logger.debug(f"  Formatter {self.formatter_id}: log_message_to_process is empty. Skipping encryption.")
            # msg_for_formatting and args_for_formatting correctly remain as original_msg, original_args

        # Temporarily modify record.msg and record.args for the call to super().format()
        record.msg = msg_for_formatting
        record.args = args_for_formatting
        
        _internal_logger.debug(f"  Formatter {self.formatter_id}: Before super().format(), record.msg is: '{str(record.msg)[:100]}...' (args {'present and non-empty' if record.args else 'cleared or empty'})")
        
        # Let the base Formatter do its job.
        # super().format(record) will:
        # 1. Call record.getMessage() using the (potentially modified) record.msg and record.args.
        # 2. Store the result in record.message.
        # 3. Format the entire log string using its format string (_fmt) and record.__dict__ (which includes the new record.message).
        # 4. If record.exc_info is present, it will format it and store it in record.exc_text (if not already there or if self.usesExceptionText() is true).
        formatted_log_string = super().format(record)
        _internal_logger.debug(f"  Formatter {self.formatter_id}: After super().format(), formatted_log_string is: '{formatted_log_string[:100]}...'")
        
        # --- CRITICAL: Restore record state for other handlers ---
        # This ensures that other handlers processing the same LogRecord instance
        # will use the original message and arguments.
        record.msg = original_msg
        record.args = original_args
        
        # Restore exc_text to its state before this formatter ran.
        # If super().format() populated it, and original_exc_text was None,
        # this sets it back to None. Subsequent formatters will recompute if needed.
        # If original_exc_text was already populated (e.g., by a prior custom formatter), this restores it.
        record.exc_text = original_exc_text
        
        # record.message is left as whatever super().format() set it to.
        # The next handler's formatter will call record.getMessage() again (using the now-restored msg/args),
        # and will overwrite record.message with its own formatted version. This is standard and expected.
        
        _internal_logger.debug(f"  Formatter {self.formatter_id}: record.msg, record.args, record.exc_text RESTORED to their original states for subsequent handlers.")
        _internal_logger.debug(f"--- EncryptedFormatter {self.formatter_id} format() COMPLETED for record: {record.name} - {record.levelname} ---")
        
        return formatted_log_string

# --- Application Logger (Fo76Bot) ---
logger = logging.getLogger('Fo76Bot')

def setup_logger():
    _internal_logger.info(f"--- Running setup_logger() for '{logger.name}' ---")
    
    if logger.hasHandlers():
        _internal_logger.debug(f"Clearing existing handlers for '{logger.name}' logger.")
        logger.handlers.clear()

    logger.setLevel(logging.DEBUG) # Set level on the logger itself
    log_format_str = '%(asctime)s - %(name)s - %(levelname)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s'

    active_public_key_pem = None
    # Check for a generic placeholder string within the hardcoded key
    if "yReplaceWithYourKey" in HARDCODED_PUBLIC_KEY_PEM: # A common pattern for placeholders
        _internal_logger.critical(
            "FATAL: Placeholder public key detected in HARDCODED_PUBLIC_KEY_PEM based on 'yReplaceWithYourKey' string. File logging will NOT be encrypted."
        )
    else:
        active_public_key_pem = HARDCODED_PUBLIC_KEY_PEM
        _internal_logger.info("Actual public key PEM will be used for EncryptedFormatter.")

    # File Handler - Encrypted
    file_handler_level = logging.INFO
    fh = logging.handlers.RotatingFileHandler(
        LOG_FILENAME, maxBytes=5*1024*1024, backupCount=3, mode='a', encoding='utf-8'
    )
    fh.setLevel(file_handler_level) # Handler level
    encrypted_formatter = EncryptedFormatter(log_format_str, public_key_pem_string=active_public_key_pem, file_handler_level=file_handler_level)
    fh.setFormatter(encrypted_formatter)
    logger.addHandler(fh)
    _internal_logger.info(f"Added RotatingFileHandler to '{logger.name}' with EncryptedFormatter (ID: {id(encrypted_formatter)}, Level: {logging.getLevelName(file_handler_level)}).")

    # Console Handler - Plain Text
    console_handler_level = logging.DEBUG
    ch = logging.StreamHandler(sys.stdout) # Explicitly use stdout for application logs
    ch.setLevel(console_handler_level) # Handler level
    plain_formatter = logging.Formatter(log_format_str)
    ch.setFormatter(plain_formatter)
    logger.addHandler(ch)
    _internal_logger.info(f"Added StreamHandler to '{logger.name}' with plain_formatter (Level: {logging.getLevelName(console_handler_level)}).")

    logger.propagate = False # Prevent passing to root logger
    _internal_logger.info(f"Set '{logger.name}.propagate = False'.")

    _internal_logger.info(f"--- setup_logger() for '{logger.name}' COMPLETED ---")
    
    # Test log messages immediately after setup
    # These will be processed by both handlers if their levels permit.
    logger.info("Fo76Bot logger setup complete. File logs (INFO+) should be encrypted. Console logs (DEBUG+) plain.")
    logger.debug("This is a Fo76Bot DEBUG message (Console only, plain).") # Below INFO, so only console
    try:
        1 / 0
    except ZeroDivisionError:
        # exc_info=True will cause exception info to be added to the LogRecord
        logger.error("Fo76Bot ERROR with exception (File encrypted, Console plain).", exc_info=True)

# Example of how to run (if this were the main script)
if __name__ == '__main__':
    _internal_logger.info(f"Running example usage from __main__ in {_LOGGING_MODULE_NAME}")
    setup_logger()
    logger.warning("This is a test WARNING message after setup.")
    logger.info("Another INFO message for testing: User %s logged in.", "test_user")
    logger.info("") # Test with empty message
    _internal_logger.info("Example usage finished.")


falloutpath = None

inputs = WindowsInputSimulator()
leavefail = 0
lastss = datetime.datetime.now()
numofevents = 0

def print_mouse_position():
    position = pyautogui.position()
    logger.debug(f"Mouse position: {position}")


def mposcheck():  # Testing
    for _ in range(10):
        print_mouse_position()
        time.sleep(1)


def close_exe():
    killed_by_psutil = False
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] in ["Fallout76.exe", "Project76.exe", "Project76_GamePass.exe"]:
            try:
                proc.kill()
                killed_by_psutil = True
                logger.info("Fallout76.exe process killed via psutil.")
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                logger.warning(f"Could not kill Fallout76.exe with psutil: {e}")
                pass

    if killed_by_psutil:
        time.sleep(5)

    while fo76running():
        logger.info("Fallout76.exe still running, attempting taskkill.")
        subprocess.call(["taskkill", "/f", "/im", "Fallout76.exe"])
        time.sleep(2)
    logger.info("Fallout76.exe process closed.")


def open_exe():
    global falloutpath
    success = False
    try:
        if not falloutpath or not os.path.exists(falloutpath):
            logger.error(f"Fallout 76 executable path not valid: {falloutpath}")
            return False
        logger.info(f"Attempting to launch game. File path: {falloutpath}")
        subprocess.Popen(falloutpath)
        
        wait_tries = 0
        while not fo76running() and wait_tries < 6:
            time.sleep(10)
            wait_tries += 1
        
        if not fo76running():
            logger.warning("Fallout76.exe did not start after 60 seconds.")
            return False

        logger.info("Fallout76.exe started. Attempting to switch to window.")
        switch_tries = 0
        while switch_tries < 10:
            if switch_to_application(open_if_not_found=False):
                success = True
                break
            logger.warning(f"Failed to switch window, attempt {switch_tries + 1}. Retrying in 5s.")
            time.sleep(5)
            switch_tries += 1
        if not success:
            logger.error("Failed to switch to Fallout76 window after multiple tries.")

    except FileNotFoundError:
        logger.error(f"Error: Fallout 76 executable not found at {falloutpath}")
        success = False
    except Exception as e:
        logger.exception("Exception during open_exe:")
        success = False
    return success

def switch_to_application(open_if_not_found=True):
    hwnd = win32gui.FindWindow(None, 'Fallout76')
    if hwnd == 0:
        hwnd = win32gui.FindWindow(None, 'Project76')
        if hwnd == 0:
            logger.warning(f"Window of Fallout76 not found.")
            if open_if_not_found: time.sleep(5)
            return open_exe() if open_if_not_found else False

    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                time.sleep(0.2)

            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.1) 
            if win32gui.GetForegroundWindow() == hwnd:
                logger.info(f"Successfully switched to Fallout 76.")
                return True
            else:
                if attempt < max_attempts - 1:
                    logger.warning(f"SetForegroundWindow for Fallout 76 did not result in foreground. Attempt {attempt + 1}/{max_attempts}. Retrying...")
                    time.sleep(1)
                else:
                     current_fg_window_hwnd = win32gui.GetForegroundWindow()
                     current_fg_window_title = win32gui.GetWindowText(current_fg_window_hwnd) if current_fg_window_hwnd else "None"
                     logger.error(f"Failed to bring Fallout 76 to foreground. Current foreground: '{current_fg_window_title}'")


        except Exception as e:
            logger.error(f"Unexpected error on attempt {attempt + 1} for Fallout 76: {e}")
            return False 
            
    logger.error(f"Could not set window Fallout 76 to foreground after {max_attempts} attempts.")
    return False


def fo76running():
    for process in psutil.process_iter(['pid', 'name']):
        try:
            if process.info['name'] in ["Fallout76.exe", "Project76.exe", "Project76_GamePass.exe"]:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False


def find_icon_positions(icon_image):
    try:
        icon_image = resource_path(icon_image)
        icon_locations = list(pyautogui.locateAllOnScreen(icon_image, confidence=0.9))
        if icon_locations:
            icon_positions = []
            for icon_location in icon_locations:
                icon_x, icon_y = pyautogui.center(icon_location)
                icon_positions.append((icon_x, icon_y))
            return icon_positions
        else:
            return [] # Return empty list instead of False for consistency
    except pyautogui.PyAutoGUIException as e:
        logger.error(f"PyAutoGUI error in find_icon_positions for {icon_image}: {e}")
        return []
    except Exception as e: # Catch other unexpected errors, e.g., image file not found by pyautogui
        logger.error(f"Unexpected error in find_icon_positions for {icon_image}: {e}")
        if not os.path.exists(icon_image):
            logger.error(f"Icon image file not found: {icon_image}")
        return []


def press_left_mouse():
    pyautogui.mouseDown()
    time.sleep(0.1)
    pyautogui.mouseUp()

def debugscreenshot():
    global lastss
    screenshot_path_val = ""
    try:
        if not fo76running():
            raise RuntimeError("Fallout76 not running, screenshot attempt aborted.")

        current_datetime = datetime.datetime.now()
        
        logger.info(f"Attempting screenshot at: {current_datetime}.")
        directory = 'debug'
        if not os.path.exists(directory):
            os.makedirs(directory)
        
        screenshot = pyautogui.screenshot()
        filename = f'screenshot_{current_datetime.strftime("%Y-%m-%d_%H-%M-%S")}.png'
        screenshot_path_val = os.path.join(directory, filename)
        screenshot.save(screenshot_path_val)
        logger.info(f"Screenshot saved to {screenshot_path_val}")
        lastss = current_datetime
        
    except RuntimeError as e:
        logger.warning(f"Screenshot pre-condition failed: {e}")
    except Exception as e:
        logger.exception("Failed to take or save a screenshot:")
    
    return "" # Original function returned empty string


def closemap():
    time.sleep(0.3)
    scoreicon = 'icons/scoreicon.png'
    dailyops = 'icons/tester.png'

    scorepos_list = find_icon_positions(scoreicon)
    opspos_list = find_icon_positions(dailyops) + find_icon_positions('icons/tester1.png') + find_icon_positions('icons/tester2.png')

    if scorepos_list and opspos_list:
        logger.info("Map identified as open, attempting to close.")
        max_tries = 4
        for tries_count in range(max_tries):
            inputs.press("m", 0.1)
            time.sleep(2)
            
            current_scorepos_list = find_icon_positions(scoreicon)
            current_opspos_list = find_icon_positions(dailyops) + find_icon_positions('icons/tester1.png')
            
            if not (current_scorepos_list and current_opspos_list):
                logger.info("Map closed successfully.")
                return True
            else:
                inputs.press("tab", 0.1)
                time.sleep(1)
            if tries_count == max_tries - 1:
                logger.warning(f"Couldn't close map after {max_tries} tries.")
                return False
        return False 
    
    elif scorepos_list and not opspos_list:
        logger.info("Score icon found but not dailyops icon (map context), assuming player is dead.")
        dead()
        return False
    
    else:
        logger.info("Map not detected as open (score/dailyops icons not found as expected). Assuming closed or irrelevant.")
        return True

def premainmenu():
    switch_to_application()
    
    if ismainmenu():
        logger.info("Already at main menu, skipping pre-main menu steps.")
        return True

    max_checks = 3
    for _ in range(max_checks):
        if ismainmenu():
            logger.info("Reached main menu.")
            return True

        uitext = readui(False, 1).lower()
        logger.debug(f"Pre-main menu check, UI text: '{uitext[:100]}...'")
        
        keywords = ["press", "any", "button", "start", "continue"]
        found_keyword = any(word in uitext for word in keywords)
        
        if found_keyword:
            logger.info("Found pre-main menu ('press any key' screen).")
            inputs.press("tab", 0.1)
            time.sleep(6)
            if ismainmenu():
                logger.info("Successfully navigated past pre-main menu to main menu.")
                return True
            else:
                logger.info("Pressed key on pre-main menu, but main menu not detected yet.")
        
        time.sleep(1)

    logger.warning("Pre-main menu ('press any key' screen) not found or navigation failed.")
    return False

def openmap():
    scoreicon = 'icons/scoreicon.png'
    dailyops = 'icons/tester.png'
    max_failcount = 1
    okcheck()
    for fail_attempt in range(max_failcount):
        scorepos_list = find_icon_positions(scoreicon)
        opspos_list = find_icon_positions('icons/tester.png') + find_icon_positions('icons/tester1.png') + find_icon_positions('icons/tester2.png')


        if scorepos_list and opspos_list:
            logger.info("Map already open.")
            okcheck()
            return True

        inputs.press("m", 0.1)
        time.sleep(3)

        scorepos_list_after_press = find_icon_positions(scoreicon)
        opspos_list_after_press = find_icon_positions(dailyops) + find_icon_positions('icons/tester1.png') + find_icon_positions('icons/tester2.png')

        if scorepos_list_after_press and opspos_list_after_press:
            logger.info("Map opened successfully.")
            okcheck()
            return True
        
        if scorepos_list_after_press and not opspos_list_after_press:
            logger.info("Score icon found post 'm' press, but not dailyops. Checking for dead state.")
            dead()
            continue 

        
        
        # logger.warning(f"Map not identified after 'm' press (attempt {fail_attempt + 1}/{max_failcount}). Retrying.")
        # time.sleep(5)

    logger.error(f"Failed to open map after {max_failcount} attempts.")
    return False

def isplayer():
    if openmap():
        return True
    if closemap():
        return True
    return False

def findevent():
    global numofevents
    icon_path = 'icons/lowresicon.png'
    overweight_icon = "icons/overweight.png"
    dailyops = 'icons/tester.png'
    if not openmap():
        logger.warning("Could not open map to find event.")
        return False
    try:
        target_icon_list = find_icon_positions(dailyops) + find_icon_positions('icons/tester1.png') + find_icon_positions('icons/tester2.png')
        target_icon_pos = target_icon_list[0]
        logger.info("Clicking on daily ops to reveal events.")
        pyautogui.moveTo(target_icon_pos[0], target_icon_pos[1], 0.4)
        for attempt in range(3):
            try:
                click(target_icon_pos[0], target_icon_pos[1])
                time.sleep(1)
                target_icon_list = find_icon_positions(dailyops) + find_icon_positions('icons/tester1.png') + find_icon_positions('icons/tester2.png')
                target_icon_pos = target_icon_list[0]
            except IndexError:
                logger.info("No daily ops icon found. Assuming click failed and cursor blocking icon.")
                time.sleep(1)
                continue
            break
        
        max_join_attempts = 3
        for attempt in range(max_join_attempts):
            icons_list = find_icon_positions(icon_path) + find_icon_positions('icons/mutieevent.png') + find_icon_positions('icons/lowresicon1.png')
            if not icons_list:
                inputs.press("TAB", 0.1)
                logger.info("Event icon not found on map.")
                return False

            numofevents = len(icons_list)
            logger.info(f"Found {numofevents} event icon(s). Targeting the first one.")
            target_icon_pos = icons_list[0]
            
            
            pyautogui.moveTo(target_icon_pos[0], target_icon_pos[1], 0.4)
            click(target_icon_pos[0], target_icon_pos[1])
            time.sleep(0.3)

            inputs.press("ENTER", 0.1)
            time.sleep(0.3)
            inputs.press("ENTER", 0.1)
            time.sleep(0.5)


            if find_icon_positions(overweight_icon):
                logger.warning("Player overweight, cannot fast travel to event. Shutting down.")
                okcheck()
                leave()
                exit(1)

            if not find_icon_positions('icons/scoreicon.png'):
                logger.info("Map closed after attempting to join event, assuming fast travel initiated.")
                return True 

            if attempt < max_join_attempts - 1:
                logger.info(f"Re-attempmting to join event (attempt {attempt + 2}).")
            else:
                logger.warning("Failed to confirm event join after multiple attempts (icon still present).")
                return True # True because the next decisionTree scan will handle it
            time.sleep(0.1)
            openmap()
        
        return False

    except Exception as e:
        logger.exception("Error during findevent:")
        return False

def okcheck():
    limit = 0
    while limit < 3: 
        ok_icon_list = find_icon_positions("icons/ok.png")
        if ok_icon_list:
            okicon = ok_icon_list[0]
            logger.info(f"Found 'OK' button at {okicon}. Clicking.")
            pyautogui.moveTo(okicon[0], okicon[1], 0.2)
            time.sleep(0.1)
            inputs.press("enter", 0.1) 
            time.sleep(0.2)
            return True 
        else:
            limit += 1
            if limit < 3 : time.sleep(0.1) 
    
    return False


def whenplayerload():
    logger.info("Checking if player loaded in...")
    max_load_checks = 12 
    for check_num in range(max_load_checks):
        if not fo76running():
            logger.warning("Game not running during player load check.")
            return False

        if isplayer():
            logger.info("Player loaded in.")
            return True
        
        logger.info(f"Player not loaded yet (check {check_num + 1}/{max_load_checks}). Waiting 10 seconds.")
        time.sleep(10)

        if okcheck():
            logger.info("Handled an 'OK' popup during load check.")

    logger.error("Load time exceeded 2 minutes. Assuming fatal error.")
    debugscreenshot()
    return False

def leave():
    global leavefail

    logger.info("Attempting to leave game to main menu.")

    if not openmap():
        logger.warning("Could not open map to initiate leaving sequence.")
        return True # Cannot proceed to leave if map can't be opened, true because it is not a failure of leaving itself but of preconditions

    max_leave_attempts = 2
    for attempt_num in range(max_leave_attempts):
        if not fo76running():
            logger.warning("Game closed during leave attempt.")
            return False 

        if ismainmenu():
            logger.info("Successfully reached main menu.")

            leavefail = 0
            return True

        logger.info(f"Leave attempt #{attempt_num + 1}")
        
        inputs.press("c", 0.1)
        time.sleep(0.35)
        pyautogui.moveTo(1200, 100, 0.5)
        click(1200, 100)
        time.sleep(0.5)
        inputs.press("enter", 0.1)
        time.sleep(0.25)
        inputs.press("enter", 0.1)
        time.sleep(2)
        if ismainmenu():
            leavefail = 0
            return True

        for _ in range(5): 
            if ismainmenu(): 
                leavefail = 0
                return True 
            time.sleep(1)
        else: 
            if attempt_num < max_leave_attempts - 1:
                 logger.info("Main menu not reached yet, will try next method or retry.")
                 time.sleep(1)
    
    logger.error("Failed to leave to main menu after all attempts.")
    if leavefail == 9: 
        logger.error("Leave attempts failed 9 times in a row, assuming persistent issue.")
    leavefail += 1
    return True


def join():
    logger.info("Attempting to join game from main menu.")
    if not ismainmenu():
        logger.warning("Not at main menu, cannot execute join sequence.")
        return False

    for _ in range(3):
        retry = False
        pyautogui.moveTo(175, 260, 0.3)
        click(175, 260)
        time.sleep(0.4)
        inputs.press("enter", 0.1)
        time.sleep(0.4)
        inputs.press("enter", 0.1)
        
        logger.info("Join initiated, waiting for popups/load screen...")
        time.sleep(2) 

        if not ismainmenu():
            logger.info("Left main menu.")
            out = readui(False, 1)
            checks = ["tab)", "more info", "t)", "enter)"]
            for check in checks:
                if check in out:
                    logger.info("Failed to join. Identified '{check}' on screen.")
                    inputs.press("tab", 0.1)
                    time.sleep(0.2)
                    retry = True
            if ismainmenu(): continue
            if retry: return False
            return True
            
    if ismainmenu():
        logger.warning("Still on main menu after join attempt and Tab presses. Join might have failed.")
        return False
    else:
        logger.info("No longer on main menu (final check). Assuming join is in progress.")
        return True


def checkevent(badeventcheck=False):
    global numofevents
    icon_path = 'icons/lowresicon.png'
    scoreicon = "icons/scoreicon.png"

    logger.info(f"Checking event status. Badeventcheck mode: {badeventcheck}")

    if not badeventcheck:
        if not openmap():
            logger.warning("Cannot open map for event check.")
        else:
            max_map_checks = 4
            event_found_on_map = False
            for _ in range(max_map_checks):
                current_icons = find_icon_positions(icon_path) + find_icon_positions('icons/mutieevent.png') + find_icon_positions('icons/lowresicon1.png')
                if current_icons:
                    if len(current_icons) < numofevents:
                        logger.info("Fewer event icons than before. Trying to re-target/join a new one.")
                        if findevent():
                            return True 
                        else:
                            event_found_on_map = False
                            break 
                    else:
                        logger.info("Event icon(s) still present on map.")
                        event_found_on_map = True
                        break 
                else: 
                    logger.info("No event icons found on map.")
                    event_found_on_map = False
                    time.sleep(1) 
            
            closemap()
            if event_found_on_map:
                logger.info("Event check (map): Event seems active/available.")
                return True
            else:
                logger.info("Event check (map): No suitable event found or confirmed via map icons.")
    
    logger.info("Proceeding with UI text based event check.")
    okcheck() 
    
    _score_list = find_icon_positions(scoreicon)
    if _score_list:
        dailyopslist = find_icon_positions('icons/tester.png') + find_icon_positions('icons/tester1.png') + find_icon_positions('icons/tester2.png')
        if not dailyopslist:
            logger.info("UI Check: Score icon present, dailyops not. Player might be dead.")
            dead()
            return False 
    else:
        logger.info("UI Check: Score icon not found. Pressing space (generic interaction).")
        inputs.press("space", 0.1)
        time.sleep(1)

    event_keywords = ["event", "event:"]
    bad_event_keywords = ["feed the people", "feed", "people", "beasts of burden", "beasts", "burden", "distinguished guests", "distinguished", "jail break", "jail"]
    
    max_ui_reads = 3
    found_good_event_text = False
    
    for _ in range(max_ui_reads):
        uitext = readui(True, 0).lower()
        logger.debug(f"UI Text for event check: '{uitext[:100]}...'")

        is_generic_event = any(word in uitext for word in event_keywords)
        
        if is_generic_event:
            return True
            is_bad_event = any(bad_word in uitext for bad_word in bad_event_keywords)
            if is_bad_event:
                logger.info("UI Text: Detected a 'bad' event.")
                return False 
            else:
                logger.info("UI Text: Detected a generic (and not explicitly bad) event.")
                found_good_event_text = True
                break 
        else: 
            logger.info("UI Text: No event-related keywords found.")
        
        if found_good_event_text: break
        time.sleep(2)

    if found_good_event_text:
        logger.info("Event check (UI): Confirmed a 'good' event is active.")
        return True
    else:
        logger.info("Event check (UI): Did not confirm a 'good' event via UI text.")
        return False

def mapclick(x, y):
    scoreicon = "icons/scoreicon.png"
    time.sleep(0.05)
    pyautogui.moveTo(x,y,0.1) 
    pyautogui.click(x, y)
    time.sleep(0.2)
    inputs.press("enter", 0.05)
    time.sleep(0.2)
    inputs.press("enter", 0.05)
    time.sleep(0.3)
    if find_icon_positions(scoreicon): 
        return True 
    else:
        return False 


def pipboyeventcheck():
    switch_to_application()
    datatab_icon = "icons/datatab.png"
    eventtab_icon = "icons/eventtab.png"
    scoreicon = "icons/scoreicon.png"

    if find_icon_positions(scoreicon):
        logger.info("Map is open, pressing 'm' to close before accessing PipBoy.")
        inputs.press("m", 0.05)
        time.sleep(0.5)

    logger.info("Opening PipBoy (Tab).")
    inputs.press("tab", 0.05)
    time.sleep(1)

    max_find_data_tab_tries = 10
    data_tab_found = False
    datapos = None 
    for i in range(max_find_data_tab_tries):
        datapos_list = find_icon_positions(datatab_icon)
        if datapos_list:
            datapos = datapos_list[0]
            logger.info(f"Found data tab at {datapos}.")
            pyautogui.click(datapos[0], datapos[1])
            data_tab_found = True
            break
        else:
            logger.warning(f"Data tab not found (attempt {i+1}). Waiting briefly.")
            time.sleep(0.3) 
    
    if not data_tab_found:
        logger.error("Failed to find or click the Data tab in PipBoy.")
        inputs.press("tab", 0.05)
        return

    max_find_event_tab_tries = 6
    event_tab_found = False
    for i in range(max_find_event_tab_tries):
        eventpos_list = find_icon_positions(eventtab_icon)
        if eventpos_list:
            eventpos = eventpos_list[0]
            logger.info(f"Found event sub-tab at {eventpos}.")
            pyautogui.click(eventpos[0], eventpos[1])
            event_tab_found = True
            break
        else:
            logger.info(f"Event sub-tab not found, pressing right arrow (attempt {i+1}).")
            inputs.arrow("right")
            time.sleep(0.3)

    if not event_tab_found:
        logger.error("Failed to find or click the Event sub-tab.")
    else:
        logger.info("Successfully navigated to PipBoy event tab.")
    
    time.sleep(0.5)
    logger.info("Closing PipBoy (Tab).")
    inputs.press("tab", 0.05)


def dead():
    logger.info("Player is dead or needs respawn. Searching for respawn location on map.")
    
    inputs.press("space", 0.05)
    x, y = 640, 400 
    mult = 1
    stage = 1
    meta = 2 
    
    max_spiral_iterations = 50 
    iterations_done = 0
    map_still_open_after_click = True 
    time.sleep(5)
    while map_still_open_after_click and iterations_done < max_spiral_iterations:
        current_stage_clicks = 0
        target_clicks_in_stage = 0

        if stage == 1: target_clicks_in_stage = mult
        elif stage == 2: target_clicks_in_stage = mult
        elif stage == 3: target_clicks_in_stage = 2 * mult
        elif stage == 4: target_clicks_in_stage = 2 * mult
        elif stage == 5: target_clicks_in_stage = 2 * mult
        elif stage == 6: target_clicks_in_stage = 2 * mult 

        for _ in range(target_clicks_in_stage):
            if stage == 1: y -= 10
            elif stage == 2: x -= 10
            elif stage == 3: y += 10
            elif stage == 4: x += 10
            elif stage == 5: y -= 10
            elif stage == 6: 
                if current_stage_clicks < mult: x -=10
                else: y -= 10
            
            map_still_open_after_click = mapclick(x, y)
            if not map_still_open_after_click:
                logger.info("Respawn point likely selected or map closed during search.")
                return True
            current_stage_clicks +=1
        
        if not map_still_open_after_click: return True

        stage += 1
        if stage > 6:
            stage = 1
            mult += 1 
            if mult >= (5 + meta):
                mult = int(round(float(mult) / meta)) 
                meta += 1
                if mult < 1: mult = 1

        iterations_done += 1
        if iterations_done >= max_spiral_iterations:
            logger.warning("Max spiral iterations reached for dead/respawn. Aborting search.")
            return False
    
    if find_icon_positions("icons/scoreicon.png"): 
        logger.info("Closing map after respawn search attempt.")
        closemap()

def perkselect():
    logger.info("Executing perkselect function (currently minimal).")
    switch_to_application("Fallout76") or switch_to_application("Project76")
    time.sleep(0.3)
    inputs.press("tab", 0.1)
    time.sleep(0.3)
    
    pyautogui.moveTo(650, 460, 0.3)
    pyautogui.click(650, 460)
    time.sleep(0.1) 
    inputs.press("enter", 0.1)
    time.sleep(0.1) 
    inputs.press("q", 0.1)
    logger.info("Perkselect: Navigated to perk interface (assumed) and pressed 'q'. Further implementation needed.")
    time.sleep(0.5)
    inputs.press("tab", 0.1)


def ismainmenu():
    if find_icon_positions("icons/menuicon.png") or find_icon_positions("icons/fo1menuicon.png"):
        logger.debug("Menu identified.") # Changed to debug as it can be frequent
        return True
    else:
        return False

def event():
    findevent()
    
    return

def noevent():
    return

def decisionTree():
    if not (switch_to_application()):
        return False
    
    # Scans for images
    # 0: Menu, 1: Map Event, 2: Ok, 3: Overweight, 4: Score, 5: Daily Ops, 6: Watericon
    iconList =  [find_icon_positions("icons/menuicon.png") + find_icon_positions("icons/fo1menuicon.png"), # Menu icon
    find_icon_positions("icons/mutieevent.png") + find_icon_positions("icons/lowresicon.png") + find_icon_positions("icons/lowresicon1.png"), # Event map icon
    find_icon_positions("icons/ok.png"),
    find_icon_positions("icons/overweight.png"),
    find_icon_positions("icons/scoreicon.png"), 
    find_icon_positions("icons/tester.png") + find_icon_positions('icons/tester2.png') + find_icon_positions('icons/tester1.png'), # Daily ops map icon
    find_icon_positions("icons/watericon.png")]
    iconBoolList = [] # 0: Menu, 1: Map Event, 2: Ok, 3: Overweight, 4: Score, 5: Daily Ops, 6: Watericon
    
    logger.info(f"iconList:\n{iconList}")
    if iconList[2] != []: return okcheck() # Returns true/false
    iconCount = 0
    for icon in iconList: 
        if icon != []:
            iconBoolList.append(True)
            iconCount += 1
        else:
            iconBoolList.append(False)
    logger.info(f"iconBoolList:\n{iconBoolList}")
    
    # Reads screen
    uiText = readui(False, 1)
    uiText = f"{uiText} {readui(False, 0)}"
    print(uiText)
    uiText = uiText.split()
    logger.info(f"uiText:\n{uiText}")

    # Dictionairy init
    preMainDict = {"press" : 0, "any" : 1, "button" : 2, "start" : 3, "continue" : 4, "tab)" : 5}
    generalNavDict = {"tab)" : 0, "t)" : 1, "enter)" : 2, "respawn" : 3, "back": 4}
    eventDict = {"event" : 0, "event:" : 1}
    loadingDict = {"loading" : 4, "by...": 5, "loading." : 7, "loading.." : 8, "loading..." : 9}
    badeventDict = {"free" : 0, "range" : 1, "distinguished" : 2, "guests": 3} #, "load" : 2, "baring" : 3}# "moonshine" : 4, "jamboree" : 5} # "feed" : 0, "the" : 1, "people" : 2, "beasts" : 3, "of" : 4, "burden" : 5, "distinguished" : 6, "guests" : 7, "jail" : 8, "break" : 9, }
    
    # Read ui results formatting/init
    resultTable = [[],[],[],[],[]] # 0: Premain results, 1: General Nav results, 2: Event results, 3: Loading results
    preMainCount = 0
    generalNavCount = 0
    eventCount = 0
    loadingCount = 0
    badEventCount = 0
    for item in uiText:
        
        itm = f"{item.strip()}"
        try:
            resultTable[0].append(preMainDict[itm])
            preMainCount += 1
        except KeyError:
            True
        except Exception as e:
            import traceback
            print(traceback.format_exc())
        try:
            resultTable[1].append(generalNavDict[itm])
            generalNavCount += 1
        except KeyError:
            True
        except Exception as e:
            import traceback
            print(traceback.format_exc())
        try:
            resultTable[2].append(eventDict[itm])
            eventCount += 1
        except KeyError:
            True
        except Exception as e:
            import traceback
            print(traceback.format_exc())
        try:
            resultTable[3].append(loadingDict[itm])
            loadingCount += 1
        except KeyError:
            True
        except Exception as e:
            import traceback
            print(traceback.format_exc())
        try:
            resultTable[4].append(badeventDict[itm])
            badEventCount += 1
        except KeyError:
            True
        except Exception as e:
            import traceback
            print(traceback.format_exc())
    
    logger.info(f"ReadUI Result Table:\n{resultTable}")
    
    # If no icons are found
    if iconCount == 0:
        
        # Loading
        if loadingCount > 0:
            logger.info("Loading...")
            time.sleep(5)
            return True
        
        # Premain menu
        if preMainCount > 1:
            premainBool = True
            for item in iconList:
                if item != []: 
                    premainBool = False
                    logger.info("preMain words found but icon also found, assuming not preMainMenu.")
                    break
            if premainBool:
                logger.info("pre main menu identified.")
                inputs.press("tab", 0.1)
                time.sleep(0.3)
                inputs.press("tab", 0.1)
                time.sleep(5)
                return True
        
        if 3 in resultTable[1]: return dead() # Respawn
        
        if badEventCount > 1 and eventCount > 0: return leave() # Bad event detected, leave
        
        hehe = openmap() # Check if in game
        
        if hehe and eventCount == 0 and not findevent(): return leave() # Not in event, leave
        elif not hehe:
            inputs.press("tab", 0.1)
            time.sleep(0.1)
            inputs.press("space", 0.1)
        closemap()
        # This code isnt used, but kept for reference
        """if 1 <= resultTable[2]: 
            inputs.press("space", 0.1)
            logger.info("Player still in event.")
            time.sleep(5)
            return True"""
            
        if generalNavCount > 0: inputs.press("tab", 0.1)
        if eventCount > 0: time.sleep(10)
        else: time.sleep(2)
        logger.info("Player still in event or stuck in pre-main menu.")
        return True
    
    
    # 0: Menu, 1: Map Event, 2: Ok, 3: Overweight, 4: Score, 5: Daily Ops, 6: Watericon, 7: mutie event icon
    match iconBoolList:
        case [True, False, False, False, False, False, False]: # At Main menu
            return join() # Returns true/false
        case [False, False, False, False, True, True, False]: # Map open, no event
            return leave() # Returns true/false
        case [False, True, False, False, True, True, False]: # Map open, is event
            if findevent():
                time.sleep(5)
                return True
            return False
        case [False, False, False, False, False, False, True]: # Loaded in
            """# If Not In Event
            if eventCount == 0:
                openmap()
                if not findevent(): 
                    return leave() # Returns true/false
            """
            # if In Event
            return True
        
    # Failure to decide
    if generalNavCount > 0: inputs.press("tab", 0.1)
    logger.info("Decision tree could not determine state, waiting briefly.")
    time.sleep(5)

"""ef main1(tesseract_path=r'C:\Program Files\Tesseract-OCR\tesseract.exe', fallout_path=r'F:\SteamLibrary\steamapps\common\Fallout76\Fallout76.exe'):
    global falloutpath, leavefail, lastss, numofevents
    falloutpath = fallout_path
    tesseract_path_init(tesseract_path)

    send_email("[FO76 Bot] Bot starting sequence...", "Bot is initializing or restarting.")
    logger.info("Starting bot sequence...")

    while True:
        current_game_state_problem = None

        if not fo76running():
            logger.info("Fallout76 not running. Attempting to launch.")
            if not open_exe():
                logger.critical("Failed to open Fallout76. Shutting down bot cycle.")
                send_email("[Fo76 Bot] Critical: Failed to launch game", "Game could not be started. Bot stopping.")
                debugscreenshot()
                return 
            else:
                logger.info("Game launched successfully.")
                time.sleep(10) 
        
        if not switch_to_application():
            logger.warning("Could not switch to Fallout76 window. Restarting game process.")
            send_email("[Fo76 Bot] Issue: Cannot switch to game window", "Attempting to close and restart game.")
            close_exe()
            time.sleep(5)
            continue

        okcheck()

        if not ismainmenu():
            if premainmenu():
                logger.info("Successfully navigated pre-main menu screen.")
            else:
                if not ismainmenu():
                    logger.warning("Failed to navigate pre-main menu and not at main menu. Checking if in game.")
                    if isplayer():
                        logger.info("Player loaded in, but not at main menu.")
                        current_game_state_problem = "loaded but not at main menu"
                    else:
                        current_game_state_problem = "pre-main menu navigation failure"
                else:
                    logger.info("Reached main menu despite premainmenu() returning False.")
        
        if not current_game_state_problem and not ismainmenu():
             logger.error("Still not at main menu after pre-main menu handling. Critical error.")
             current_game_state_problem = "stuck before main menu"

        if not current_game_state_problem and ismainmenu():
            logger.info("At main menu. Attempting to join game world.")
            if join():
                logger.info("Join sequence initiated. Waiting for player to load.")
                if not whenplayerload():
                    logger.error("Player failed to load into the world after join.")
                    send_email("[Fo76 Bot] Player load failure", "Player did not load into world after timeout.")
                    debugscreenshot()
                    current_game_state_problem = "player load failure"
                else:
                    logger.info("Player successfully loaded into the world.")
            else:
                logger.warning("Failed to initiate join from main menu.")
                current_game_state_problem = "join game failure"
        
        if (not current_game_state_problem or isplayer()) and fo76running() and not ismainmenu():
            current_game_state_problem = None # Reset if we are in game
            logger.info("In game. Looking for events.")
            if findevent():
                logger.info("Event join attempt made. Verifying load and event status.")
                if whenplayerload():
                    time.sleep(1)
                    max_event_active_checks = 5
                    event_confirmed_active = False
                    for _ in range(max_event_active_checks):
                        if not fo76running(): break
                        if checkevent():
                            event_confirmed_active = True
                            break
                        logger.info("Event not confirmed active yet. Retrying checkevent/findevent.")
                        if findevent():
                            if whenplayerload():
                                continue 
                            else:
                                current_game_state_problem = "load failure after re-finding event"
                                break 
                        else:
                            time.sleep(5)
                    
                    if not fo76running(): current_game_state_problem = "game closed during event"

                    if not current_game_state_problem and event_confirmed_active:
                        logger.info("Event active. Monitoring event completion.")
                        send_email("[FO76 Bot] Event joined.", "Monitoring event.")
                        inputs.press("LEFT_CTRL", 0.1)
                        time.sleep(15)

                        event_duration_checks = 0
                        max_event_duration_checks = 51 
                        
                        while checkevent(False) and event_duration_checks < max_event_duration_checks:
                            if not fo76running():
                                current_game_state_problem = "game closed during active event"
                                break
                            inputs.press("a", 0.2)
                            time.sleep(20)
                            inputs.press("d", 0.2)
                            event_duration_checks += 1
                        
                        if not current_game_state_problem:
                            if event_duration_checks >= max_event_duration_checks:
                                logger.warning("Event took longer than expected.")
                                send_email("[Fo76 Bot] Event duration exceeded limit", "Unexpected behaviour or very long event. Screenshot taken.")
                                debugscreenshot()
                            else:
                                logger.info("Event completed or no longer detected by checkevent.")
                                send_email("[Fo76 Bot] Event complete", "Event assumed complete.")
                                debugscreenshot()
                        
                        if not current_game_state_problem:
                            if not leave():
                                logger.error("Failed to leave to main menu after event.")
                                current_game_state_problem = "failed to leave after event"
                            else:
                                logger.info("Successfully left to main menu after event.")

                    elif not current_game_state_problem:
                        logger.warning("Could not confirm an active (good) event after multiple attempts.")
                        send_email("[FO76 Bot] Event confirmation failed", "Could not confirm active event. Screenshot.")
                        debugscreenshot()
                        if not leave():
                             current_game_state_problem = "failed to leave after event confirmation failure"
                else:
                    logger.error("Failed to load after initial event join attempt.")
                    current_game_state_problem = "player load failure post findevent"
            
            else:
                logger.info("No event found or failed to join. Leaving world.")
                if not leave():
                    logger.error("Failed to leave to main menu (no event found path).")
                    current_game_state_problem = "failed to leave (no event)"
                else:
                    logger.info("Successfully left to main menu (no event found path).")
        
        elif not current_game_state_problem and fo76running() and not ismainmenu() and not isplayer():
            logger.error("Cannot identify player state correctly (not main menu, but isplayer() is false).")
            send_email("[FO76 Bot] Player state identification issue", "Could not identify player state. Screenshot.")
            debugscreenshot()
            current_game_state_problem = "player state unidentifiable"

        if current_game_state_problem:
            logger.error(f"Encountered problem: {current_game_state_problem}. Restarting game.")
            send_email("[FO76 Bot] Restarting game due to issue", f"Problem: {current_game_state_problem}. Restarting Fallout76.")
            close_exe()
            time.sleep(15)
            continue

        if not fo76running():
            logger.warning("Fallout76 instance not found unexpectedly. Bot will attempt to restart it.")
            send_email("[FO76 Bot] Game instance lost", "Fallout76 closed unexpectedly. Bot will restart.")
            debugscreenshot()
            continue

        logger.info("Bot cycle completed. Going back to start.")"""

def main(tesseract_path, fallout_path, ini_path, height, width, loc_x, loc_y, fullscreen, borderless):
    global falloutpath, leavefail, lastss, numofevents
    falloutpath = fallout_path
    tesseract_path_init(tesseract_path)
    if [height, width, loc_x, loc_y, fullscreen, borderless] != [800,1280,0,0,0,1]:
        close_exe()
        import configparser
        # Create a ConfigParser object
        config = configparser.ConfigParser()
        config.read(ini_path)
        config.set('Display', 'iSize H', '800')
        config.set('Display', 'iSize W', '1280')
        config.set('Display', 'iLocation X', '0')
        config.set('Display', 'iLocation Y', '0')
        config.set('Display', 'bFull Screen', '0')
        config.set('Display', 'bBorderless', '1')
        with open(ini_path, 'w') as configfile:
            config.write(configfile)
    setup_logger() # Initialize the logger
    while True:
        if decisionTree() == False:
            close_exe()
            time.sleep(5)
        time.sleep(1)