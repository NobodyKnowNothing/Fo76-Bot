import tkinter as tk
from tkinter import messagebox, filedialog
import multiprocessing
import requests
import json
import webbrowser
import threading
import urllib.parse
import os
import configparser

# Try importing pynput, handle if missing
try:
    from pynput import keyboard as pynput_keyboard
except ImportError:
    print("Warning: 'pynput' library not found. Global hotkeys (F5) will not work.")
    pynput_keyboard = None

# --- Import your bot logic ---
try:
    from testmain import main
except ImportError:
    # Fallback for testing if testmain is missing
    def main(fp2, fp1, fp3=None, h=None, w=None, x=None, y=None, fs=None, bl=None):
        print(f"MOCK BOT RUNNING with {fp1} and {fp2}")
        import time
        while True:
            time.sleep(1)

CACHE_FILE = "config.json"

# --- Global variables ---
bot_process = None
status_label_main = None 
root_tk_instance = None 
keyboard_listener = None 

# --- Helper Functions ---


def parse_ini_file(ini_path):
    """Parses the Fallout76Prefs.ini file to extract specific display settings."""
    config = configparser.ConfigParser()
    if not os.path.exists(ini_path):
        print(f"Error: INI file not found at '{ini_path}'")
        messagebox.showerror("INI File Error", f"The specified INI file could not be found:\n{ini_path}")
        return None
        
    config.read(ini_path)

    try:
        settings = {
            'height': config.getint('Display', 'iSize H'),
            'width': config.getint('Display', 'iSize W'),
            'loc_x': config.getint('Display', 'iLocation X'),
            'loc_y': config.getint('Display', 'iLocation Y'),
            'fullscreen': config.getint('Display', 'bFull Screen'),
            'borderless': config.getint('Display', 'bBorderless')
        }
        return settings
    except (configparser.NoSectionError, configparser.NoOptionError) as e:
        print(f"Error parsing INI file: {e}")
        messagebox.showerror("INI Parse Error", f"Could not find a required setting in '{ini_path}'.\nDetails: {e}")
        return None
    except ValueError as e:
        print(f"Error converting INI value: {e}")
        messagebox.showerror("INI Value Error", f"A setting in '{ini_path}' has an invalid value.\nDetails: {e}")
        return None

def get_cached_data():
    """Reads config.json and returns settings."""
    defaults = ("", "", "", [], "", False, "")
    if not os.path.exists(CACHE_FILE):
        return defaults
    
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        fp1 = data.get("game_path", "")
        fp2 = data.get("tesseract_path", "")
        fp3 = data.get("ini_path", "")
        ini_settings = data.get("ini_settings", [])
        fp1_sec = data.get("alt_game_path", "")
        use_sec = data.get("use_alt_config", False)
        fp3_sec = data.get("alt_ini_path", "")
        
        return fp1, fp2, fp3, ini_settings, fp1_sec, use_sec, fp3_sec
    except Exception as e:
        print(f"Error reading cache: {e}")
        return defaults

def save_cached_data(fp1, fp2, fp3, ini_settings, fp1_sec, use_sec, fp3_sec):
    """Saves data to config.json."""
    data = {
        "game_path": fp1,
        "tesseract_path": fp2,
        "ini_path": fp3,
        "ini_settings": ini_settings,
        "alt_game_path": fp1_sec,
        "use_alt_config": use_sec,
        "alt_ini_path": fp3_sec
    }
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Failed to save cache: {e}")

def reset_ini():
    """
    Reads display settings from cache.txt and writes them back to the INI file.
    """
    try:
        if not os.path.exists(CACHE_FILE):
            print(f"Error: {CACHE_FILE} not found.")
            return

        with open(CACHE_FILE, 'r') as f:
            data = json.load(f)
            
        ini_path = data.get("ini_path", "")
        settings = data.get("ini_settings", [])
        
        if not ini_path or not settings or len(settings) < 6:
            print(f"Error: {CACHE_FILE} is missing required configuration data.")
            return

        if not os.path.exists(ini_path):
            print(f"Error: INI file not found at {ini_path}")
            return

        config = configparser.ConfigParser()
        config.read(ini_path)

        if not config.has_section('Display'):
            config.add_section('Display')

        config.set('Display', 'iSize H', str(settings[0]))
        config.set('Display', 'iSize W', str(settings[1]))
        config.set('Display', 'iLocation X', str(settings[2]))
        config.set('Display', 'iLocation Y', str(settings[3]))
        config.set('Display', 'bFull Screen', str(settings[4]))
        config.set('Display', 'bBorderless', str(settings[5]))

        with open(ini_path, 'w') as configfile:
            config.write(configfile)
        print(f"Settings in [Display] section of {ini_path} have been updated from {CACHE_FILE}")

    except Exception as e:
        print(f"An unexpected error occurred during INI reset: {e}")

def cleanup():
    """Cleans up resources on application exit."""
    reset_ini()
    terminate_bot_process()
    stop_global_f5_listener()

# --- ToolTip Class ---
class CreateToolTip(object):
    def __init__(self, widget, text='widget info'):
        self.waittime = 500     
        self.wraplength = 180   
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter) 
        self.widget.bind("<Leave>", self.leave) 
        self.widget.bind("<ButtonPress>", self.leave) 
        self.id = None
        self.tw = None 

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.waittime, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showtip(self, event=None):
        x = y = 0
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        self.tw = tk.Toplevel(self.widget)
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self.tw, text=self.text, justify='left',
                         background="#ffffe0", relief='solid', borderwidth=1,
                         wraplength = self.wraplength)
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tw
        self.tw = None
        if tw:
            tw.destroy()

# --- App Lifecycle ---

def terminate_bot_process():
    global bot_process
    if bot_process and bot_process.is_alive():
        bot_process.terminate()
        bot_process.join(timeout=1)
        if bot_process.is_alive():
            bot_process.kill()
        bot_process = None
        return True
    return False

def on_app_closing():
    global root_tk_instance, auth_server
    print("Closing app...")
    stop_global_f5_listener()
    terminate_bot_process()
    if root_tk_instance:
        root_tk_instance.destroy()

def check_bot_status():
    global bot_process, status_label_main, root_tk_instance
    if not root_tk_instance or not root_tk_instance.winfo_exists(): return
    if not status_label_main or not status_label_main.winfo_exists():
        root_tk_instance.after(2000, check_bot_status)
        return

    is_running = bot_process and bot_process.is_alive()
    current_status_text = status_label_main.cget("text")

    if is_running:
        pid = bot_process.pid
        running_message = f"Status: Bot is running (PID: {pid})"
        if current_status_text != running_message:
            status_label_main.config(text=running_message)
    else:
        if "running" in current_status_text.lower():
            status_label_main.config(text="Status: Bot is not running.")

    root_tk_instance.after(2000, check_bot_status)

# --- Global Hotkey Logic ---
def _kill_bot_on_f5_action():
    global status_label_main, bot_process
    msg = ""
    if bot_process and bot_process.is_alive():
        terminate_bot_process()
        msg = "Status: Bot process terminated by F5."
    else:
        msg = "Status: No bot running to stop."
    
    if status_label_main:
        status_label_main.config(text=msg)

def on_global_f5_press():
    global root_tk_instance
    if root_tk_instance:
        root_tk_instance.after_idle(_kill_bot_on_f5_action)

def start_global_f5_listener():
    global keyboard_listener
    if not pynput_keyboard: return

    def on_press(key):
        try:
            if key == pynput_keyboard.Key.f5:
                on_global_f5_press()
        except: pass

    if keyboard_listener is None:
        keyboard_listener = pynput_keyboard.Listener(on_press=on_press)
        keyboard_listener.start()

def stop_global_f5_listener():
    global keyboard_listener
    if keyboard_listener:
        keyboard_listener.stop()
        keyboard_listener = None


# --- UI Setup ---

def clear_window():
    global root_tk_instance
    if root_tk_instance:
        for widget in root_tk_instance.winfo_children():
            widget.destroy()


def setup_main_app_window(root_window):
    global status_label_main, bot_process, root_tk_instance
    root_tk_instance = root_window

    root_window.title("Fallout Bot Control Panel")
    root_window.geometry("550x450") # Increased height for extra fields

    # --- Status Bar ---
    status_bar = tk.Frame(root_window, relief=tk.SUNKEN, bd=1)
    status_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=(5,0))
    
    exit_button = tk.Button(status_bar, text="Exit", command=on_app_closing)
    exit_button.pack(side=tk.RIGHT, padx=5, pady=2)

    status_label_main = tk.Label(status_bar, text="Status: Ready", anchor='w')
    status_label_main.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

    # --- Load cache for FilePaths ---
    cached_fp1, cached_fp2, cached_fp3, cached_ini, cached_fp1_sec, cached_use_sec, cached_fp3_sec = get_cached_data()
    
    # Defaults
    fp1_val = cached_fp1 if cached_fp1 else "C:\\Program Files\\Fallout76\\Fallout76.exe"
    fp2_val = cached_fp2 if cached_fp2 else "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
    user_docs = os.path.expanduser("~\\Documents")
    fp3_val = cached_fp3 if cached_fp3 else os.path.join(user_docs, "My Games", "Fallout 76", "Fallout76Prefs.ini")
    fp1_sec_val = cached_fp1_sec if cached_fp1_sec else ""
    fp3_sec_val = cached_fp3_sec if cached_fp3_sec else ""

    filepath1_var = tk.StringVar(value=fp1_val)
    filepath2_var = tk.StringVar(value=fp2_val)
    filepath3_var = tk.StringVar(value=fp3_val)
    filepath1_sec_var = tk.StringVar(value=fp1_sec_val)
    use_secondary_var = tk.BooleanVar(value=cached_use_sec)
    filepath3_sec_var = tk.StringVar(value=fp3_sec_val)
    show_secondary_var = tk.BooleanVar(value=False) 

    def start_bot_action():
        global bot_process
        fp1 = filepath1_var.get()
        fp2 = filepath2_var.get()
        fp3 = filepath3_var.get()
        fp1_sec = filepath1_sec_var.get()
        use_sec = use_secondary_var.get()
        fp3_sec = filepath3_sec_var.get()

        # Determine which game path to use
        game_path_to_use = fp1
        if use_sec and show_secondary_var.get(): 
             game_path_to_use = fp1_sec
        
        # Determine which INI path to use
        ini_path_to_use = fp3
        if use_sec and show_secondary_var.get():
            ini_path_to_use = fp3_sec

        if not game_path_to_use or not fp2 or not ini_path_to_use:
            messagebox.showwarning("Missing Info", "Please provide all required filepaths.")
            return

        if not os.path.exists(game_path_to_use):
            messagebox.showerror("File Not Found", f"Game executable not found:\n{game_path_to_use}")
            return
            
        if not os.path.exists(fp2):
            messagebox.showerror("File Not Found", f"Tesseract executable not found:\n{fp2}")
            return
            
        ini_settings = parse_ini_file(ini_path_to_use)
        if ini_settings is None:
            if status_label_main: status_label_main.config(text="Status: Error - Failed to read INI file.")
            return

        if status_label_main: status_label_main.config(text=f"Status: Starting...")
        
        if bot_process and bot_process.is_alive():
            terminate_bot_process()

        # Update cache 
        _, _, _, cached_ini, _, _, _ = get_cached_data()
        
        settings_to_save = ini_settings
        # If the new settings are 1280x800, and we have valid cached settings, preserve the cached settings
        if ini_settings.get('width') == 1280 and ini_settings.get('height') == 800:
            # Check if cached_ini has valid data (it's a list of strings: [height, width, ...])
            if cached_ini and len(cached_ini) >= 2 and cached_ini[0] and cached_ini[1]:
                 settings_to_save = cached_ini

        save_cached_data(fp1, fp2, fp3, settings_to_save, fp1_sec, use_sec, fp3_sec)

        try:
            # Pass the selected game path as fp1 (the game executable)
            # main(fp2, fp1, fp3, h, w, x, y, fs, bl)
            bot_process = multiprocessing.Process(
                target=main, 
                args=(
                    fp2, 
                    game_path_to_use, # Use the selected path
                    ini_path_to_use, # Use the selected INI path 
                    ini_settings['height'],
                    ini_settings['width'],
                    ini_settings['loc_x'],
                    ini_settings['loc_y'],
                    ini_settings['fullscreen'],
                    ini_settings['borderless']
                )
            )
            bot_process.start()
            if status_label_main: status_label_main.config(text=f"Status: Bot running (PID: {bot_process.pid}) using {os.path.basename(game_path_to_use)}")
        except Exception as e:
            status_label_main.config(text=f"Status: Error {e}")

    def browse(var, filetypes=(("Exe", "*.exe"),("All", "*.*"))):
        f = filedialog.askopenfilename(filetypes=filetypes)
        if f: var.set(f)

    # --- Layout ---
    content = tk.Frame(root_window, padx=10, pady=10)
    content.pack(fill=tk.BOTH, expand=True)

    btns = tk.Frame(content)
    btns.pack(pady=(0, 15), fill=tk.X)
    
    b_start = tk.Button(btns, text="Start Bot", command=start_bot_action, width=15, height=2, bg="#DDDDDD")
    b_start.pack(side=tk.LEFT, padx=(0,10))
    CreateToolTip(b_start, "Run the bot.")
    
    tk.Label(btns, text="Press F5 to Stop", fg="red").pack(side=tk.LEFT)

    group = tk.LabelFrame(content, text="Configuration", padx=10, pady=10)
    group.pack(fill=tk.X, expand=True)

    # Primary Fallout 76 Path
    row1 = tk.Frame(group)
    row1.pack(fill=tk.X, pady=5)
    tk.Label(row1, text="Fallout76.exe:", width=15, anchor='w').pack(side=tk.LEFT)
    tk.Entry(row1, textvariable=filepath1_var).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
    tk.Button(row1, text="...", command=lambda: browse(filepath1_var)).pack(side=tk.LEFT)

    # Secondary Path Container (Hidden by default)
    secondary_frame = tk.Frame(group)
    
    def toggle_secondary_view():
        if show_secondary_var.get():
            secondary_frame.pack(fill=tk.X, pady=5, after=row_toggle)
        else:
            secondary_frame.pack_forget()

    # Toggle Button for Secondary
    row_toggle = tk.Frame(group)
    row_toggle.pack(fill=tk.X, pady=2)
    toggle_btn = tk.Checkbutton(row_toggle, text="Configure Alternate Version", variable=show_secondary_var, command=toggle_secondary_view)
    toggle_btn.pack(side=tk.LEFT)
    CreateToolTip(toggle_btn, "Enable this to configure a second Fallout 76 executable (e.g., for running Steam and Game Pass versions).")

    # Secondary Fields inside the frame
    row_sec_path = tk.Frame(secondary_frame)
    row_sec_path.pack(fill=tk.X, pady=2)
    tk.Label(row_sec_path, text="Alt Fallout76.exe:", width=15, anchor='w').pack(side=tk.LEFT)
    tk.Entry(row_sec_path, textvariable=filepath1_sec_var).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
    tk.Button(row_sec_path, text="...", command=lambda: browse(filepath1_sec_var)).pack(side=tk.LEFT)

    row_sec_use = tk.Frame(secondary_frame)
    row_sec_use.pack(fill=tk.X, pady=2)
    tk.Label(row_sec_use, width=15).pack(side=tk.LEFT) 
    use_chk = tk.Checkbutton(row_sec_use, text="Use this configuration instead of primary", variable=use_secondary_var)
    use_chk.pack(side=tk.LEFT)

    # Secondary INI Fields
    row_sec_ini = tk.Frame(secondary_frame)
    row_sec_ini.pack(fill=tk.X, pady=2)
    tk.Label(row_sec_ini, text="Alt Fallout76Prefs.ini:", width=18, anchor='w').pack(side=tk.LEFT) # Slightly wider label
    tk.Entry(row_sec_ini, textvariable=filepath3_sec_var).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
    tk.Button(row_sec_ini, text="...", command=lambda: browse(filepath3_sec_var, filetypes=(("INI", "*.ini"),("All", "*.*")))).pack(side=tk.LEFT)

    # Tesseract Path
    row2 = tk.Frame(group)
    row2.pack(fill=tk.X, pady=5)
    tk.Label(row2, text="tesseract.exe:", width=15, anchor='w').pack(side=tk.LEFT)
    tk.Entry(row2, textvariable=filepath2_var).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
    tk.Button(row2, text="...", command=lambda: browse(filepath2_var)).pack(side=tk.LEFT)

    # INI Path
    row3 = tk.Frame(group)
    row3.pack(fill=tk.X, pady=5)
    tk.Label(row3, text="Fallout76Prefs.ini:", width=15, anchor='w').pack(side=tk.LEFT)
    tk.Entry(row3, textvariable=filepath3_var).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
    tk.Button(row3, text="...", command=lambda: browse(filepath3_var, filetypes=(("INI", "*.ini"),("All", "*.*")))).pack(side=tk.LEFT)

    start_global_f5_listener()
    root_window.after(2000, check_bot_status)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    root = tk.Tk()
    setup_main_app_window(root)
    root.protocol("WM_DELETE_WINDOW", on_app_closing)
    root.mainloop()
    cleanup()
