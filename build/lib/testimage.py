import psutil
import subprocess
import time
import win32con
import win32gui
import sys
from press import WindowsInputSimulator
from emailapi import send_email
import datetime
import pyautogui
import os
from readtext import readui, tesseract_path_init

falloutpath = None
# Setup
sys.setrecursionlimit(55)
inputs = WindowsInputSimulator()
leavefail = 0
lastss = datetime.datetime.now()
numofevents = 0

def print_mouse_position():
    position = pyautogui.position()
    print(f"Mouse position: {position}")


def mposcheck():  # Testing
    for _ in range(10):
        print_mouse_position()
        time.sleep(1)


def close_exe():
    for proc in psutil.process_iter():
        if proc.name() == f"Fallout76.exe":
            proc.kill()
    time.sleep(5)
    while fo76running():
        subprocess.call(["taskkill", "/f", "/im", "Fallout76.exe"])
        time.sleep(2)


def open_exe():
    try:
        global falloutpath
        print("Attempting to launch game. File path: " + falloutpath)
        subprocess.Popen(falloutpath)
        while not fo76running():
            time.sleep(1)
        tries = 0
        while tries < 10:
            try:
                success = switch_to_application("Fallout76")
                if success: break
            except:
                time.sleep(5)
                success = False
                tries += 1
    except:
        import traceback
        traceback.print_exc()
        success = False
    return success

def switch_to_application(window_title):
    success = False
    try:
        # Find the window handle of the target application by its title
        hwnd = win32gui.FindWindow(None, window_title)
        if hwnd == 0:
            print("Window not found")
            tries = 9
            
        
        # Bring the window to the foreground
        # Restore window if minimized
        tries = 0
        while not success:
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                time.sleep(0.1)
                win32gui.SetForegroundWindow(hwnd)
                success = True
            except:
                tries += 1
                time.sleep(2)
            if tries >= 2:
                print("Could not set window to foreground after 2 attempts")
                break
    except:
        True
    return success


def fo76running():
    running = False
    process_name = "Fallout76.exe"
    for process in psutil.process_iter(['pid', 'name']):
        if process.info['name'] == process_name:
            running = True
    return running


def find_icon_positions(icon_image):
    icon_locations = pyautogui.locateAllOnScreen(icon_image, confidence=0.9)
    if icon_locations:
        # List to store center coordinates of all matches
        icon_positions = []
        for icon_location in icon_locations:
            icon_x, icon_y = pyautogui.center(icon_location)
            icon_positions.append((icon_x, icon_y))
        return icon_positions
    else:
        return False


def press_left_mouse():
    pyautogui.mouseDown()
    time.sleep(0.1)  # Adjust this delay if needed
    pyautogui.mouseUp()

def debugscreenshot():
    screenshot_path = ""
    global lastss
    try:
        if not fo76running():
            raise
        current_datetime = datetime.datetime.now()
        if abs(current_datetime - lastss).total_seconds() <= 180:
            send_email("[Fo76 Bot] Screenshots taken less then 3 mins apart", "logic error maybe?")
        print(f"Screenshot at: {current_datetime}.")
        directory = 'debug'
        if not os.path.exists(directory):
            os.makedirs(directory)
        # Take a screenshot
        # screenshot = pyautogui.screenshot()
        # Save the screenshot in the specified directory
        # screenshot_path = os.path.join(directory, f'screenshot, {current_datetime.strftime("%Y-%m-%d_%H-%M-%S")}.png')
        # screenshot.save(screenshot_path)
        # lastss = current_datetime
    except:
        print("Failed to take a screenshot")
        send_email("[Fo76 Bot] Debug screen shot failure", "Fatal error likely, storage space limited maybe?")
    return ""


def closemap():
    success = False
    switch_to_application("Fallout76")
    time.sleep(0.3)
    scoreicon = 'scoreicon.png'
    dailyops = 'tester.png'
    try:
        scorepos = find_icon_positions(scoreicon)[0]
        opspos = find_icon_positions(dailyops)[0]
        print("Map identified, Close")
        tries = 0
        while opspos and scorepos:
            inputs.press("m", 0.1)
            time.sleep(0.7)
            success = True
            scorepos = find_icon_positions(scoreicon)[0]
            opspos = find_icon_positions(dailyops)[0]
            if tries >= 3:
                print("Couldnt close map with 5 tries")
                success = False
                break
            tries += 1
        success = True
    except:
        try:
            scorepos = find_icon_positions(scorepos)[0]
            success = False
            dead()
        except:
            success = True
    return success

def premainmenu():
    found = 2
    switch_to_application("Fallout76") 
    success = False
    while found > 0 and not success:
        uitext = readui(False, 1).lower()
        print(uitext)
        for word in ["press", "any", "button", "start", "enter)", "tab)"]:
            if word in uitext:
                found += 1
                success = True
        time.sleep(1)
        found -= 1
        if ismainmenu():
            break
        if success:
            print("Found pre main menu")
            inputs.press("tab", 0.1)
            time.sleep(6)
            success = False
    return success

def openmap():
    scoreicon = 'scoreicon.png'
    dailyops = 'tester.png'
    failcount = 0
    success = False
    while failcount < 5:
        try:
            scorepos = find_icon_positions(scoreicon)[0]
            opspos = find_icon_positions(dailyops)[0]
            if opspos and scorepos:
                print("Map already Open")
                success = True
                failcount = 0
                break
        except:
            inputs.press("m", 0.1)
            time.sleep(0.7)
            try:
                scorepos = find_icon_positions(scoreicon)[0]
                try:
                    opspos = find_icon_positions(dailyops)[0]
                    if opspos and scorepos:
                        print("Map identified, Open")
                        success = True
                        okcheck()
                        failcount = 0
                        break
                except:
                    if scorepos:
                        print("Likely player dead")
                        dead()
                        failcount -= 1
                        break
                print("Post break")
            except:
                failcount += 1
                if failcount >= 5:
                    print("Map wasnt identified 5 times, Open")
                    break
                if ismainmenu():
                    break
                if "respawn" in readui(False, 1):
                    inputs.press("space", 0.1)
                time.sleep(5)
        if failcount == 0 or failcount >= 5:
            break
    return success

def isplayer():
    success = False
    if openmap():
        time.sleep(0.5)
        if closemap():
            success = True
    return success

def findevent():
    global numofevents
    success = False
    icon_path = 'lowresicon.png'
    if openmap():
        try:
            iconpos = find_icon_positions(icon_path)[0]
            icons = find_icon_positions(icon_path)
            numofevents = len(icons)
            iconpos = icons[0]
            if numofevents > 1:
                if numofevents > 1:
                    print(f"found: {numofevents}")
                else:
                    print("Event icon found")
                pyautogui.moveTo(iconpos[0], iconpos[1], 0.4)
                inputs.click_mouse("LEFT")
                pyautogui.click()
                inputs.press("ENTER", 0.1)
                tries = 0
                while tries <= 5:
                    try:
                        iconspos = find_icon_positions(icon_path)[0]
                        if iconpos:
                            time.sleep(0.1)
                            pyautogui.moveTo(iconpos[0], iconpos[1], 0.4)
                            time.sleep(0.2)
                            inputs.click_mouse("LEFT")
                            time.sleep(0.1)
                            pyautogui.click(iconpos[0], iconpos[1])
                            time.sleep(0.1)
                            inputs.press("ENTER", 0.1)
                            pyautogui.click()
                            print("Event identified, joining...")
                    except:
                        time.sleep(0.4)
                        inputs.press("ENTER", 0.1)
                    time.sleep(0.4)
                    inputs.press("ENTER", 0.1)
                    time.sleep(0.4)
                    inputs.press("ENTER", 0.1)
                    tries += 1
                    if tries >= 2:
                        try:
                            locpos = find_icon_positions("overweight.png")[0]
                            if locpos:
                                print("Player overweight, exiting...")
                                send_email("[FO76 Bot] Player overweight, action needed",
                                           f"Bot failed to fast travel due to weight, please fix")
                                success = False
                                break
                        except:
                            success = True
        except:
            print("Event icon not found")
    return success

def okcheck():
    limit = 0
    okcheck = False
    while 3 >= limit:
        try:
            okicon = find_icon_positions("ok.png")[0]
            time.sleep(0.1)
            pyautogui.moveTo(okicon[0], okicon[1])
            time.sleep(0.2)
            inputs.press("enter", 0.1)
            time.sleep(0.2)
            okcheck = True
        except:
            limit += 1
            time.sleep(0.1)
    return okcheck

def whenplayerload():
    scoreicon = 'scoreicon.png'
    print("checking if player loaded in")
    success = True
    tries = 0
    isplay = isplayer()
    while (not isplay) and tries <= 5:
        if not fo76running():
                break
        time.sleep(10)
        isplay = isplayer()
        tries += 1
        limit = 3
        if tries >= limit:
            if okcheck():
                limit += 3
            else:
                try:
                    scorepos = find_icon_positions(scoreicon)[0]
                    if scorepos:
                        print("Likely player dead")
                        dead()
                        break
                except:
                    True
    if tries >= 12:
        print("Load time took 2 mins, fatal error assumed, screenshot")
        send_email("[Fo76 Bot] Load time took 3 mins", "Fatal error likely")
        debugscreenshot()
        success = False
    if success:
        print("Player loaded in")
    return success

def leave():
    global leavefail
    dailyops = 'tester.png'
    print("Leaving")
    if openmap():
        mainmenu = ismainmenu()
        tries1 = 0
        tries2 = 0
        while tries2 <= 20 and not mainmenu:
            if not fo76running():
                break
            time.sleep(0.1)
            inputs.press("c", 0.1)
            time.sleep(0.35)
            pyautogui.moveTo(1200, 100, 0.5)
            time.sleep(0.5)
            inputs.press("enter", 0.1)
            time.sleep(0.25)
            inputs.press("enter", 0.1)
            inputs.press("c", 0.25)
            time.sleep(0.3)
            pyautogui.moveTo(1200, 100, 0.5)
            pyautogui.click(1200, 100)
            time.sleep(0.3)
            inputs.press("enter", 0.1)
            pyautogui.click(900, 160)
            time.sleep(0.3)
            inputs.press("enter", 0.1)
            time.sleep(0.7)
            inputs.press("tab", 0.1)
            time.sleep(0.5)
            try:
                if openmap():
                    opspos = find_icon_positions(dailyops)[0]
                    if opspos:
                        pyautogui.click(1200, 100)
                        time.sleep(0.3)
                        inputs.press("enter", 0.1)
                        time.sleep(0.2)
                        pyautogui.click(900, 240)
                        time.sleep(0.2)
                        inputs.press("enter", 0.1)
            except:
                True
            mainmenu = ismainmenu()
            while tries1 <= 10 and not mainmenu:
                tries1 += 1
                time.sleep(0.5)
                mainmenu = ismainmenu()
            if mainmenu:
                break
            tries2 += 1
            time.sleep(0.3)
    try:
        pos = find_icon_positions("menuicon.png")[0]
        if leavefail >= 10:
            send_email("[FO76 Bot] Bot left game successfully, disregard last",
                        f"Bot failed to leave game 10 times in a row but then succeeded again")
        leavefail = 0
        print("Leave succeeded")
        succeeded = True
    except:
        print("Leaving failed")
        if leavefail == 10:
            send_email("[FO76 Bot] Failed to leave game 10 times",
                       f"Bot failed to leave game 10 times in a row, unknown error likely")
        leavefail += 1
        succeeded = False
    return succeeded


def join():
    time.sleep(0.1)
    pyautogui.click(175, 260)
    time.sleep(0.4)
    inputs.press("enter", 0.1)
    time.sleep(0.4)
    inputs.press("enter", 0.1)
    time.sleep(2)
    for i in range(3):
        inputs.press("tab", 0.1)
        time.sleep(0.5)
        try:
            pos = find_icon_positions("menuicon.png")[0]
            succeeded = False
            i = 3
        except:
            succeeded = True
            print("Joining")
            break
    return succeeded


def checkevent(badeventcheck=False):
    global numofevents
    print("Checking event")
    icon_path = 'lowresicon.png'
    dailyops = 'tester.png'
    scoreicon = "scoreicon.png"
    event = False
    tries = 0 
    if openmap() and not badeventcheck:
        while tries <= 3 and not event:
            try:
                icons = find_icon_positions(icon_path)
                if len(icons) < numofevents:
                    print("Less events then before")
                    event = findevent()
                else:
                    print("Event found")
                    event = True
            except:
                event = False
                tries += 1
                time.sleep(1)
        if tries >= 3:
            print("Event not found")
            time.sleep(1)
    else:
        okcheck()
        try:
            scorepos = find_icon_positions(scoreicon)
            try:
                opspos = find_icon_positions(dailyops)
            except:
                dead()
                event = False
        except:
            inputs.press("space", 0.1)
            time.sleep(1)
    closemap()
    if badeventcheck or not event:
        uitext = readui(True, 0)
        print(uitext)
        eventwords = ["event", "event:"]
        # eventwords = ["the mothman", "mothman equinox", "scorched earth",  "event: scorched", "earth", "a colossal", "colossal problem", "encryptid", "project", "paradise", "test your", "your metal", "eviction", "notice", "one violent", "violent night"]
        badevents = ["feed the people", "feed", "people", "beasts of burden", "beasts", "burden", "distinguished guests", "distinguished", "jail break", "jail"]
        notfound = 0
        while notfound < 1 and tries <= 2: # Detects event by trying to read ui
            uitext = readui(True, 0)
            for word in eventwords:
                if word in uitext:
                    for word1 in badevents:
                        if word1 in uitext:
                            notfound += 1
                            print("Bad event detected")
                            if notfound > 2:
                                break
                    event = True
                else:
                    if not badeventcheck: break
                    notfound += 1
                    print("Event quest not found")
            tries += 1
            if not badeventcheck: break
            if notfound > 2:
                break
            time.sleep(2)
        if notfound >= 1:
            event = False
    return event

def mapclick(x, y):
    scoreicon = "scoreicon.png"
    time.sleep(0.05)
    pyautogui.click(x, y)
    time.sleep(0.2)
    inputs.press("enter", 0.05)
    time.sleep(0.2)
    inputs.press("enter", 0.05)
    time.sleep(0.3)
    try:
        scorepos = find_icon_positions(scoreicon)[0]
        success = True
    except:
        success = False
    return success


def pipboyeventcheck():
    switch_to_application("Fallout76")
    datatab = "datatab.png"
    eventtab = "eventtab.png"
    scoreicon = "scoreicon.png"
    while True:
        try:
            scorepos = find_icon_positions(scoreicon)[0]
            if scorepos:
                inputs.press("m", 0.05)
        except:
            inputs.press("tab", 0.05)
            time.sleep(1)
            try:
                tries = 0
                while tries < 30:
                    try:
                        datapos = find_icon_positions(datatab)[0]
                        print(tries + " " + datapos)
                        if datapos:
                            break
                    except:
                        datapos = False
                        tries += 1
                    if tries >= 30:
                        print("Failed to find data tab")
                        raise
                print("Found data tab " + datapos)
                pyautogui.click(datapos[0], datapos[1])
                inputs.click_mouse("LEFT", 0.05)
                tries = 0
                while tries < 5:
                    print("e " + tries)
                    time.sleep(0.3)
                    try:
                        eventpos = find_icon_positions(eventtab)[0]
                        pyautogui.click(eventpos[0], eventpos[1])
                        inputs.click_mouse("LEFT", 0.05)
                        break
                    except:
                        inputs.arrow("right")
                        tries += 1
                        if tries > 5:
                            print("Failed to identify event tab")

                break
            except:
                print("Failed to identify data tab or pipboy")


def dead():
    dead = True
    dailyops = 'tester.png'
    print("Player is dead, looking for respawn")
    mult = 1
    stage = 1
    meta = 2
    x, y = 640, 400
    mapclick(x, y)
    loop = True
    try:
        while loop:
            match stage:
                case 1:
                    if mult == 1:
                        for i in range(mult):
                            y -= int(round(10, 0))
                            loop = mapclick(x, y)
                case 2:
                    for i in range(mult):
                        x -= int(round(10, 0))
                        loop = mapclick(x, y)
                case 3:
                    for i in range(2*mult):
                        y += int(round(10, 0))
                        loop = mapclick(x, y)
                case 4:
                    for i in range(2*mult):
                        x += int(round(10, 0))
                        loop = mapclick(x, y)
                case 5:
                    for i in range(2*mult):
                        y -= int(round(10, 0))
                        loop = mapclick(x, y)
                case 6:
                    for i in range(mult):
                        x -= int(round(10, 0))
                        loop = mapclick(x, y)
                    for i in range(mult):
                        y -= int(round(10, 0))
                        loop = mapclick(x, y)
                case 7:
                    mult += 1
                    stage = 1
            stage += 1
            if mult >= 5 + meta:
                stage = 1
                mult = mult / meta
                meta += 1 
            if meta >= 5:
                raise
    except Exception as e:
        print(f"Failed to find respawn, e:{e}")

def perkselect():
    """
    Assuming slugger build
    Perks to get:
    Traveling Pharmacy, lvl 3
    Pack Rat, lvl 7
    Sturdy Frame, lvl 13
    Strong Back, lvl 26
    Arms Keeper, lvl 28
    """
    switch_to_application("Fallout76")
    time.sleep(0.3)
    inputs.press("tab", 0.1)
    time.sleep(0.3)
    pyautogui.click(650, 460)
    inputs.press("enter", 0.1)
    
    inputs.press("q", 0.1)


def ismainmenu():
    try:
        pos = find_icon_positions("menuicon.png")[0]
        if pos:
            print("Menu identified")
            success = True
    except:
        success = False
    return success


def main(tesseract_path='C:\Program Files\Tesseract-OCR\tesseract.exe', fallout_path='F:\SteamLibrary\steamapps\common\Fallout76\Fallout76.exe'):
    global falloutpath
    falloutpath = fallout_path
    tesseract_path = tesseract_path
    tesseract_path_init(tesseract_path)
    send_email("[FO76 Bot] Starting bot...",
                   f"Starting bot...")
    print("Starting bot...")
    if not switch_to_application("Fallout76"):
        fail = False
        if fo76running():
            print("Closing fallout 76...")
            send_email("[FO76 Bot] Restarting fallout 76",
                       f"Unexpected game behaviour occurred, restarting fallout 76.")
            close_exe()
        if open_exe():
            time.sleep(5)
            if switch_to_application("Fallout76"):
                print("Game launch successful")
            else:
                fail = True
        else:
            fail = True
        if fail:
            print("Couldnt switch to fallout 76")
            send_email("[FO76 Bot] Couldnt open or interact with game",
                   f"Unexpected behaviour occurred.")
            debugscreenshot()
            exit()
        
    #try:
    failcount = 0
    pos = True
    tries = 0
    triesmain = 0
    while fo76running() and triesmain < 7:
        if not switch_to_application("Fallout76"):
            break
        triesmain += 1
        found = 0
        okcheck()
        if premainmenu():
            print("Pre-main menu identified and navigated")
        if ismainmenu():
            joined = False
            while not joined:
                joined = join()
                if not fo76running():
                    break
            if not fo76running():
                break
        if whenplayerload():
            if findevent(): # If event is found
                if whenplayerload():
                    time.sleep(1)
                    chkevent = checkevent()
                    tries1 = 0
                    while not chkevent and tries1 < 5:
                        if not fo76running():
                            break
                        if findevent():
                            if whenplayerload():
                                chkevent = checkevent()
                        tries1 += 1
                        time.sleep(5)
                    if chkevent:
                        inputs.press("LEFT_CTRL", 0.1)
                        send_email("[FO76 Bot] Event joined.", f"Event joined.")
                        time.sleep(15)
                        tries = 0
                        while checkevent(False) and tries < 51: # Detects event by trying to read map
                            inputs.press("a", 0.2)
                            tries += 1
                            time.sleep(20)
                            inputs.press("d", 0.2)
                            if not fo76running():
                                break
                        if tries >= 51:
                            print("Event took longer then expected, screenshot")
                            send_email("[Fo76 Bot] Event took longer then expected", "Unexpected behaviour likely, screenshot taken")
                            debugscreenshot()
                        else:
                            send_email("[Fo76 Bot] Event complete", "Event complete.")
                            debugscreenshot()
                            print("Event complete")
                    else:
                        print("Unknown error occurred, couldnt identify event after trying to join 5 times")
                        send_email("[Fo76 Bot] Unknown event error", "Unknown behaviour, couldnt identify event after trying to join 5 times")
                        debugscreenshot()
            else: # if event not found
                if leave():
                    triesmain = 0
                    inputs.press("tab", 0.1)
                
        else:
            print("Could not identify player, screenshot")
            send_email("[Fo76 Bot] Could not identify player", "Could not identify player after loading in")
            debugscreenshot()
            time.sleep(2)
            close_exe()
            time.sleep(20)
            break
    if triesmain >= 5:
        print("Unexpected behaviour, restarting")
        state = "has unexpected behaviour"
        close_exe()
    elif not fo76running():
        state = "instance not found"
        print("Fallout 76 instance not found")
        debugscreenshot()
    print("Restarting bot")
    send_email("[Fo76 Bot] Restarting bot...", f"Game {state}, restarting bot...")
    main()

if __name__ == "__main__":  
    main()

"""
    except Exception as e:
        send_email("[FO76 Bot] Fatal Error",
                   f"Error: {e}")
        debugscreenshot()
        if open_exe():
            print("Opening fallout 76 and restarting bot")
            send_email("[Fo76 Bot] Fallout 76 being reopened", "Game found to be closed, restarting bot and game")
            main()
            exit
        else:
            print("Failed to open fallout 76")
            send_email("[Fo76 Bot] Fallout 76 failed to reopen, game found to be closed, restarting game failed") 
    """
