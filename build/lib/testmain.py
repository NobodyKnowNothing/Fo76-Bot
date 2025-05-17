import psutil
import subprocess
import time
import win32con
import win32gui
from press import WindowsInputSimulator
from emailapi import send_email
import datetime
import pyautogui
import os
from readtext import readui, tesseract_path_init
import logging
import logging.handlers

# --- Logger Setup ---
LOG_FILENAME = 'fo76_bot.log'
logger = logging.getLogger('Fo76Bot')

def setup_logger():
    logger.setLevel(logging.DEBUG)  # Capture all levels from DEBUG upwards

    # File Handler - logs INFO and higher
    fh = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=5*1024*1024, backupCount=3, mode='a') # 5MB per file, 3 backups
    fh.setLevel(logging.INFO)

    # Console Handler - logs DEBUG and higher (for real-time feedback)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    # Add handlers to the logger
    if not logger.handlers: # Avoid adding multiple handlers if script is re-run in some environments
        logger.addHandler(fh)
        logger.addHandler(ch)
# --- End Logger Setup ---

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
        if proc.info['name'] == "Fallout76.exe":
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
        while not fo76running() and wait_tries < 30:
            time.sleep(1)
            wait_tries += 1
        
        if not fo76running():
            logger.warning("Fallout76.exe did not start after 30 seconds.")
            return False

        logger.info("Fallout76.exe started. Attempting to switch to window.")
        switch_tries = 0
        while switch_tries < 10:
            if switch_to_application("Fallout76"):
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

def switch_to_application(window_title):
    hwnd = win32gui.FindWindow(None, window_title)
    if hwnd == 0:
        logger.warning(f"Window '{window_title}' not found.")
        return False

    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                time.sleep(0.2)

            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.1) 
            if win32gui.GetForegroundWindow() == hwnd:
                logger.info(f"Successfully switched to '{window_title}'.")
                return True
            else:
                if attempt < max_attempts - 1:
                    logger.warning(f"SetForegroundWindow for '{window_title}' did not result in foreground. Attempt {attempt + 1}/{max_attempts}. Retrying...")
                    time.sleep(1)
                else:
                     current_fg_window_hwnd = win32gui.GetForegroundWindow()
                     current_fg_window_title = win32gui.GetWindowText(current_fg_window_hwnd) if current_fg_window_hwnd else "None"
                     logger.error(f"Failed to bring '{window_title}' to foreground. Current foreground: '{current_fg_window_title}'")


        except win32gui.error as e:
            logger.warning(f"win32gui.error on attempt {attempt + 1} for '{window_title}': {e}")
            if attempt < max_attempts - 1:
                time.sleep(1)
        except Exception as e:
            logger.error(f"Unexpected error on attempt {attempt + 1} for '{window_title}': {e}")
            return False 
            
    logger.error(f"Could not set window '{window_title}' to foreground after {max_attempts} attempts.")
    return False


def fo76running():
    process_name = "Fallout76.exe"
    for process in psutil.process_iter(['pid', 'name']):
        try:
            if process.info['name'] == process_name:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False


def find_icon_positions(icon_image):
    try:
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
        if abs(current_datetime - lastss).total_seconds() <= 180:
            send_email("[Fo76 Bot] Screenshots taken less then 3 mins apart", "Logic error maybe or frequent issues.")
        
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
        send_email("[Fo76 Bot] Debug screenshot pre-condition fail", str(e))
    except Exception as e:
        logger.exception("Failed to take or save a screenshot:")
        send_email("[Fo76 Bot] Debug screenshot failure", f"Error: {e}. Storage space limited maybe?")
    
    return "" # Original function returned empty string


def closemap():
    switch_to_application("Fallout76")
    time.sleep(0.3)
    scoreicon = 'icons/scoreicon.png'
    dailyops = 'icons/tester.png'

    scorepos_list = find_icon_positions(scoreicon)
    opspos_list = find_icon_positions(dailyops)

    if scorepos_list and opspos_list:
        logger.info("Map identified as open, attempting to close.")
        max_tries = 4
        for tries_count in range(max_tries):
            inputs.press("m", 0.1)
            time.sleep(0.7)
            
            current_scorepos_list = find_icon_positions(scoreicon)
            current_opspos_list = find_icon_positions(dailyops)
            
            if not (current_scorepos_list and current_opspos_list):
                logger.info("Map closed successfully.")
                return True
            
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
    switch_to_application("Fallout76")
    
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
        
        keywords = ["press", "any", "button", "start", "enter)", "tab)"]
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
    max_failcount = 5
    
    for fail_attempt in range(max_failcount):
        scorepos_list = find_icon_positions(scoreicon)
        opspos_list = find_icon_positions(dailyops)

        if scorepos_list and opspos_list:
            logger.info("Map already open.")
            okcheck()
            return True

        inputs.press("m", 0.1)
        time.sleep(0.7)

        scorepos_list_after_press = find_icon_positions(scoreicon)
        opspos_list_after_press = find_icon_positions(dailyops)

        if scorepos_list_after_press and opspos_list_after_press:
            logger.info("Map opened successfully.")
            okcheck()
            return True
        
        if scorepos_list_after_press and not opspos_list_after_press:
            logger.info("Score icon found post 'm' press, but not dailyops. Checking for dead state.")
            dead()
            continue 

        if ismainmenu():
            logger.info("Detected main menu while trying to open map. Aborting openmap.")
            return False

        current_ui_text = readui(False, 1).lower()
        if "respawn" in current_ui_text:
            logger.info("Found 'respawn' in UI text. Pressing space.")
            inputs.press("space", 0.1)
            time.sleep(1)
            continue
        
        logger.warning(f"Map not identified after 'm' press (attempt {fail_attempt + 1}/{max_failcount}). Retrying.")
        time.sleep(5)

    logger.error(f"Failed to open map after {max_failcount} attempts.")
    return False

def isplayer():
    if openmap():
        time.sleep(0.5)
        if closemap():
            return True
    return False

def findevent():
    global numofevents
    icon_path = 'icons/lowresicon.png'
    overweight_icon = "icons/overweight.png"

    if not openmap():
        logger.warning("Could not open map to find event.")
        return False

    try:
        icons_list = find_icon_positions(icon_path)
        if not icons_list:
            logger.info("Event icon not found on map.")
            closemap()
            return False

        numofevents = len(icons_list)
        logger.info(f"Found {numofevents} event icon(s). Targeting the first one.")
        target_icon_pos = icons_list[0]
        
        max_join_attempts = 3
        for attempt in range(max_join_attempts):
            pyautogui.moveTo(target_icon_pos[0], target_icon_pos[1], 0.4)
            time.sleep(0.4)
            pyautogui.click(target_icon_pos[0], target_icon_pos[1])
            time.sleep(0.3)
            pyautogui.click(target_icon_pos[0], target_icon_pos[1])
            time.sleep(0.3)
            inputs.click_mouse("LEFT")
            time.sleep(0.3)
            inputs.press("ENTER", 0.1)
            time.sleep(0.3)
            inputs.press("ENTER", 0.1)
            time.sleep(0.5)


            if find_icon_positions(overweight_icon):
                logger.warning("Player overweight, cannot fast travel to event.")
                send_email("[FO76 Bot] Player overweight, action needed",
                           "Bot failed to fast travel due to weight, please fix.")
                exit(1)

            if not find_icon_positions('icons/scoreicon.png'):
                logger.info("Map closed after attempting to join event, assuming fast travel initiated.")
                return True 

            if attempt < max_join_attempts - 1:
                logger.info(f"Re-attempmting to join event (attempt {attempt + 2}).")
            else:
                logger.warning("Failed to confirm event join after multiple attempts (icon still present).")
                return False
            closemap()
            time.sleep(0.1)
            openmap()
        
        closemap()
        return False

    except Exception as e:
        logger.exception("Error during findevent:")
        closemap()
        return False

def okcheck():
    limit = 0
    ok_found_and_pressed = False
    while limit < 3: 
        ok_icon_list = find_icon_positions("icons/ok.png")
        if ok_icon_list:
            okicon = ok_icon_list[0]
            logger.info(f"Found 'OK' button at {okicon}. Clicking.")
            pyautogui.moveTo(okicon[0], okicon[1], 0.2)
            time.sleep(0.1)
            inputs.press("enter", 0.1) 
            time.sleep(0.2)
            ok_found_and_pressed = True
            return True 
        else:
            if ok_found_and_pressed: 
                break
            limit += 1
            if limit < 3 : time.sleep(0.1) 
    
    return ok_found_and_pressed 


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
    send_email("[Fo76 Bot] Load time took >2 mins", "Fatal error likely, player not detected in game.")
    debugscreenshot()
    return False

def leave():
    global leavefail

    logger.info("Attempting to leave game to main menu.")

    if not openmap():
        logger.warning("Could not open map to initiate leaving sequence.")
        if ismainmenu():
            logger.info("Already at main menu.")
            if leavefail >= 10:
                 send_email("[FO76 Bot] Bot left game successfully, disregard last",
                            "Bot failed to leave game 10 times in a row but then succeeded again")
            leavefail = 0
            return True
        return False 

    max_leave_attempts = 5
    for attempt_num in range(max_leave_attempts):
        if not fo76running():
            logger.warning("Game closed during leave attempt.")
            return False 

        if ismainmenu():
            logger.info("Successfully reached main menu.")
            if leavefail >= 10:
                 send_email("[FO76 Bot] Bot left game successfully, disregard last",
                            "Bot failed to leave game 10 times in a row but then succeeded again")
            leavefail = 0
            return True

        logger.info(f"Leave attempt #{attempt_num + 1}")
        
        inputs.press("c", 0.1)
        time.sleep(0.35)
        pyautogui.moveTo(1200, 100, 0.5)
        time.sleep(0.5)
        inputs.press("enter", 0.1)
        time.sleep(0.25)
        inputs.press("enter", 0.1)
        time.sleep(2)
        if ismainmenu(): continue

        inputs.press("c", 0.25)
        time.sleep(0.3)
        pyautogui.moveTo(1200, 100, 0.5)
        pyautogui.click(1200, 100)
        time.sleep(0.3)
        inputs.press("enter", 0.1)
        pyautogui.moveTo(900, 160, 0.3) 
        pyautogui.click(900, 160)
        time.sleep(0.3)
        inputs.press("enter", 0.1)
        time.sleep(2)
        if ismainmenu(): continue

        for _ in range(10): 
            if ismainmenu(): break 
            time.sleep(0.5)
        else: 
            if attempt_num < max_leave_attempts - 1:
                 logger.info("Main menu not reached yet, will try next method or retry.")
                 time.sleep(1)
    
    logger.error("Failed to leave to main menu after all attempts.")
    if leavefail == 9: 
        send_email("[FO76 Bot] Failed to leave game 10 times",
                   "Bot failed to leave game 10 times in a row, unknown error likely")
    leavefail += 1
    closemap() 
    return False


def join():
    logger.info("Attempting to join game from main menu.")
    if not ismainmenu():
        logger.warning("Not at main menu, cannot execute join sequence.")
        return False

    for _ in range(3):
        retry = False
        pyautogui.moveTo(175, 260, 0.3)
        pyautogui.click(175, 260)
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
                current_icons = find_icon_positions(icon_path)
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
        if not find_icon_positions('icons/tester.png'):
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
    switch_to_application("Fallout76")
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
    
    if not openmap():
        logger.warning("Could not open map for dead/respawn process. Aborting dead().")
        return

    x, y = 640, 400 
    mult = 1
    stage = 1
    meta = 2 
    
    max_spiral_iterations = 50 
    iterations_done = 0
    map_still_open_after_click = True 

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
                break 
            current_stage_clicks +=1
        
        if not map_still_open_after_click: break

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
            break
    
    if find_icon_positions("icons/scoreicon.png"): 
        logger.info("Closing map after respawn search attempt.")
        closemap()

def perkselect():
    logger.info("Executing perkselect function (currently minimal).")
    switch_to_application("Fallout76")
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
    if find_icon_positions("icons/menuicon.png"):
        logger.debug("Menu identified.") # Changed to debug as it can be frequent
        return True
    else:
        return False


def main(tesseract_path=r'C:\Program Files\Tesseract-OCR\tesseract.exe', fallout_path=r'F:\SteamLibrary\steamapps\common\Fallout76\Fallout76.exe'):
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
        
        if not switch_to_application("Fallout76"):
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

        logger.info("Bot cycle completed. Going back to start.")

if __name__ == "__main__":  
    setup_logger() # Initialize the logger
    main()