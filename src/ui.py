import tkinter as tk
from tkinter import messagebox, filedialog
from testmain import main # Assuming this is the main bot logic
import multiprocessing # Changed from threading
import requests
import json # For handling potential JSONDecodeError explicitly
# import threading # No longer needed
from pynput import keyboard as pynput_keyboard # For global hotkey
import os
import configparser

# --- Global variables for process management and UI elements ---
bot_process = None
status_label_main = None # Will be assigned in setup_main_app_window
root_tk_instance = None # To store the root Tk instance for closing and bindings
keyboard_listener = None # For the global pynput keyboard listener

# --- Functions ---

def parse_ini_file(ini_path):
    """
    Parses the Fallout76Prefs.ini file to extract specific display settings.
    
    Args:
        ini_path (str): The full path to the Fallout76Prefs.ini file.

    Returns:
        dict: A dictionary containing the settings, or None if an error occurs.
    """
    config = configparser.ConfigParser()
    # Read the INI file. If the file doesn't exist, it will return an empty list.
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
        messagebox.showerror("INI Parse Error", 
                             f"Could not find a required setting in '{ini_path}'.\n\n"
                             f"Please ensure the [Display] section and all required keys exist.\n\n"
                             f"Details: {e}")
        return None
    except ValueError as e:
        print(f"Error converting INI value: {e}")
        messagebox.showerror("INI Value Error",
                             f"A setting in '{ini_path}' has an invalid value (e.g., not a number).\n\n"
                             f"Details: {e}")
        return None

def check_bot_status():
    """
    Periodically checks if the bot process is alive and updates the status label.
    This ensures the UI reflects the bot's state even if it stops unexpectedly.
    """
    global bot_process, status_label_main, root_tk_instance

    # Stop checking if the main window has been destroyed
    if not root_tk_instance or not root_tk_instance.winfo_exists():
        return

    # Check if the status label itself still exists
    if not status_label_main or not status_label_main.winfo_exists():
        root_tk_instance.after(2000, check_bot_status) # Keep trying in case it's redrawn
        return

    is_running = bot_process and bot_process.is_alive()
    current_status_text = status_label_main.cget("text")

    if is_running:
        # Bot is running, ensure the label reflects this.
        pid = bot_process.pid
        running_message = f"Status: Bot is running (PID: {pid})"
        if current_status_text != running_message:
            status_label_main.config(text=running_message)
    else:
        # Bot is not running. If the label incorrectly says it is, update it.
        # This allows specific messages like "Terminated by F5" to persist,
        # but corrects the status if the bot crashes while the label showed "running".
        if "running" in current_status_text.lower():
            status_label_main.config(text="Status: Bot is not running.")

    # Schedule this function to run again after 2 seconds
    root_tk_instance.after(2000, check_bot_status)

class CreateToolTip(object):
    """
    Create a tooltip for a given widget.
    """
    def __init__(self, widget, text='widget info'):
        self.waittime = 500     # Milliseconds after hover to show tooltip
        self.wraplength = 180   # Max width in pixels before wrapping text
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter) # Bind mouse entering widget
        self.widget.bind("<Leave>", self.leave) # Bind mouse leaving widget
        self.widget.bind("<ButtonPress>", self.leave) # Hide tooltip on click
        self.id = None
        self.tw = None # Tooltip window

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

def call_url(
    url: str,
    method: str = "GET",
    params: dict = None,
    data: dict = None,
    json_payload: dict = None,
    headers: dict = None,
    timeout: int = 10,
    allow_redirects: bool = True
    ) -> dict:
    result = {
        "success": False,
        "status_code": None,
        "content_type": None,
        "data": None,
        "headers": None,
        "error_message": None,
        "raw_response": None,
    }
    try:
        request_headers = headers if headers else {}
        if json_payload and 'Content-Type' not in request_headers:
            request_headers['Content-Type'] = 'application/json'
        response = requests.request(
            method=method.upper(),
            url=url,
            params=params,
            data=data if not json_payload else None,
            json=json_payload,
            headers=request_headers,
            timeout=timeout,
            allow_redirects=allow_redirects
        )
        result["raw_response"] = response
        result["status_code"] = response.status_code
        result["headers"] = dict(response.headers)
        result["content_type"] = response.headers.get("Content-Type", "").lower()
        response.raise_for_status()
        if not response.content:
            result["data"] = None
            result["success"] = True
        elif "application/json" in result["content_type"]:
            try:
                result["data"] = response.json()
                result["success"] = True
            except json.JSONDecodeError as e:
                result["error_message"] = f"Failed to decode JSON: {e}. Raw text: {response.text[:200]}..."
                result["data"] = response.text
        elif "text/" in result["content_type"]:
            result["data"] = response.text
            result["success"] = True
        else:
            result["data"] = response.content
            result["success"] = True
    except requests.exceptions.HTTPError as e:
        result["error_message"] = f"HTTP Error: {e}"
        if e.response is not None:
            result["data"] = e.response.text
    except requests.exceptions.ConnectionError as e:
        result["error_message"] = f"Connection Error: {e}"
    except requests.exceptions.Timeout as e:
        result["error_message"] = f"Timeout Error: {e}"
    except requests.exceptions.RequestException as e:
        result["error_message"] = f"Request Exception: {e}"
    except Exception as e:
        result["error_message"] = f"An unexpected error occurred: {e}"
    return result

def write_file(filepath, content, mode='w', encoding='utf-8'):
    if mode not in ['w', 'a']:
        print(f"Error: Invalid mode '{mode}'. Use 'w' (write) or 'a' (append).")
        return False
    try:
        with open(filepath, mode, encoding=encoding) as file:
            file.write(content)
        return True
    except IOError as e:
        print(f"Error writing to file '{filepath}': {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred while writing to '{filepath}': {e}")
        return False

def read_file(filepath, encoding='utf-8'):
    try:
        with open(filepath, 'r', encoding=encoding) as file:
            content = file.read()
        return content.splitlines() # Returns a list of lines
    except FileNotFoundError:
        print(f"Error: File '{filepath}' not found.")
        return None
    except IOError as e:
        print(f"Error reading file '{filepath}': {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while reading '{filepath}': {e}")
        return None

def terminate_bot_process(graceful_timeout=1, kill_timeout=1):
    """Attempts to terminate and then kill the bot process."""
    global bot_process
    terminated = False
    if bot_process and bot_process.is_alive():
        pid = bot_process.pid
        print(f"Attempting to terminate bot process (PID: {pid})...")
        bot_process.terminate()
        bot_process.join(timeout=graceful_timeout)
        if not bot_process.is_alive():
            print(f"Bot process (PID: {pid}) terminated gracefully.")
            terminated = True
        else:
            print(f"Bot process (PID: {pid}) did not terminate gracefully. Killing...")
            bot_process.kill()
            bot_process.join(timeout=kill_timeout)
            if not bot_process.is_alive():
                print(f"Bot process (PID: {pid}) killed.")
                terminated = True
            else:
                print(f"Failed to kill bot process (PID: {pid}). It might be stuck.")
        if terminated:
            bot_process = None # Clear the reference
    return terminated

def on_app_closing():
    """Handles application close events (window X or Exit button)."""
    global root_tk_instance
    print("Application closing...")
    stop_global_f5_listener() # Stop the global listener
    terminate_bot_process()
    if root_tk_instance:
        root_tk_instance.destroy()

def _kill_bot_on_f5_action(): # Renamed to avoid conflict if event is passed
    """
    Internal logic for killing the bot and updating UI.
    This should be called from the main Tkinter thread.
    """
    global status_label_main, bot_process, root_tk_instance
    print("F5 action triggered to kill bot.")

    message_to_display = ""
    console_message_on_success = ""

    if bot_process and bot_process.is_alive():
        pid = bot_process.pid # Store before termination attempt
        if terminate_bot_process():
            message_to_display = f"Status: Bot process (PID: {pid}) terminated by F5."
            console_message_on_success = message_to_display # Also print this if UI fails
        else:
            message_to_display = f"Status: Failed to terminate bot (PID: {pid}) on F5."
    else:
        message_to_display = "Status: No bot process running to terminate."
        print("No bot process running to terminate via F5.") # Console print for this case

    if root_tk_instance and status_label_main:
        try:
            # Check if the widget still exists and its master (the root window)
            if status_label_main.winfo_exists() and root_tk_instance.winfo_exists():
                 status_label_main.config(text=message_to_display)
            elif console_message_on_success: # If UI is gone but an action was taken
                print(console_message_on_success)
        except tk.TclError:
            # Widget might have been destroyed
            print(f"Error updating status label (it might be destroyed): {message_to_display}")
            if console_message_on_success:
                print(console_message_on_success)
    elif console_message_on_success: # If UI elements are not available but an action was taken
        print(console_message_on_success)


def on_global_f5_press():
    """
    Callback for the pynput listener.
    Schedules the actual bot killing logic to run in the main Tkinter thread.
    """
    global root_tk_instance
    if root_tk_instance:
        print("Global F5 detected, scheduling bot kill action.")
        # Use after_idle to ensure it runs when Tkinter is ready and in the main thread
        root_tk_instance.after_idle(_kill_bot_on_f5_action)
    else:
        # Fallback if Tkinter isn't fully up or is shutting down - attempt direct action
        # This is less safe for UI but terminate_bot_process itself is process-level
        print("Global F5 detected, root_tk_instance not available. Attempting direct bot termination.")
        _kill_bot_on_f5_action()


def start_global_f5_listener():
    global keyboard_listener
    
    def on_press(key):
        try:
            if key == pynput_keyboard.Key.f5:
                on_global_f5_press()
        except Exception as e:
            # Can log e if needed, but pynput might call this rapidly for other keys
            pass

    if keyboard_listener is None: # Start only if not already running
        # Listener runs in its own daemon thread.
        keyboard_listener = pynput_keyboard.Listener(on_press=on_press)
        keyboard_listener.start()
        print("Global F5 listener started.")
    else:
        print("Global F5 listener already running.")


def stop_global_f5_listener():
    global keyboard_listener
    if keyboard_listener:
        print("Stopping global F5 listener...")
        keyboard_listener.stop()
        # listener.join() # Optional: wait for listener thread to fully stop.
                        # Can block if listener is stuck. For quick exit, often omitted.
        keyboard_listener = None
        print("Global F5 listener stopped.")


def check_user():
    global password_entry, status_label # These are from setup_login_window
    entered_password = str(password_entry.get())
    if not entered_password: # Basic validation
        status_label.config(text="User ID cannot be empty!", fg="red")
        return

    url = f"https://rust-bot-auth-744976866854.us-central1.run.app/check_patron/{entered_password}"
    result = call_url(url, method="GET")

    if result['success'] and result['data'] and result['data'].get('is_patron'):
        clear_window()
        cache_content = read_file('cache.txt')
        # Preserve existing filepaths if they exist in cache
        existing_fp1 = "None"
        existing_fp2 = "None"
        if cache_content:
            if len(cache_content) > 1 and cache_content[1]:
                existing_fp1 = cache_content[1]
            if len(cache_content) > 2 and cache_content[2]:
                existing_fp2 = cache_content[2]
        
        write_file("cache.txt", f"{entered_password}\n{existing_fp1}\n{existing_fp2}", mode='w')
        setup_main_app_window(root_tk_instance) # root_tk_instance is global
    else:
        error_msg = "Incorrect User ID!"
        if result['error_message']:
            error_msg = f"Error: {result['error_message']}"
        elif not result['success']:
             error_msg = "Failed to verify User ID. Check connection."
        status_label.config(text=error_msg, fg="red")
        password_entry.delete(0, tk.END)

def clear_window():
    global root_tk_instance
    if root_tk_instance:
        for widget in root_tk_instance.winfo_children():
            widget.destroy()

def setup_login_window(window):
    global password_entry, status_label, root_tk_instance
    root_tk_instance = window # Store the root window instance

    try:
        cache = read_file("cache.txt")
        patron_id = None
        if cache and len(cache) > 0:
            patron_id = cache[0].strip() if cache[0] else None

        if patron_id:
            url = f"https://rust-bot-auth-744976866854.us-central1.run.app/check_patron/{patron_id}"
            result = call_url(url, method="GET")
            if result['success'] and result['data'] and result['data'].get('is_patron'):
                clear_window()
                setup_main_app_window(window)
                return
    except FileNotFoundError:
        print("cache.txt not found. Proceeding to login screen.")
    except Exception as e:
        print(f"Error during auto-login attempt: {e}. Proceeding to login screen.")

    window.title("Fallout Bot Login")
    window.geometry("300x180")

    prompt_label = tk.Label(window, text="Please enter your identification code:")
    prompt_label.pack(pady=10)

    password_entry = tk.Entry(window, show="*", width=25)
    password_entry.pack(pady=5)
    password_entry.focus_set()

    login_button = tk.Button(window, text="Login", command=check_user, width=10)
    login_button.pack(pady=10)

    status_label = tk.Label(window, text="", fg="red")
    status_label.pack(pady=5)

    window.bind('<Return>', lambda event=None: login_button.invoke())

def setup_main_app_window(root_window):
    global status_label_main, bot_process, root_tk_instance
    root_tk_instance = root_window # Ensure global ref is up-to-date

    root_window.title("Fallout Bot Control Panel")
    root_window.geometry("550x270") # Slightly increased height for status bar if needed

    # --- Status Bar ---
    status_bar = tk.Frame(root_window, relief=tk.SUNKEN, bd=1)
    status_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=(5,0))

    # Exit Button (packed first from the right)
    exit_button = tk.Button(status_bar, text="Exit", command=on_app_closing)
    exit_button.pack(side=tk.RIGHT, padx=5, pady=2)

    

    # Main Status Label (packed from the left, fills remaining space)
    status_label_main = tk.Label(status_bar, text="Status: Ready", anchor='w') # Assign to global
    status_label_main.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)


    # --- Load cache for filepaths and patron ID ---
    cache = read_file("cache.txt")
    patron_id_from_cache = "UNKNOWN_PATRON" # Default
    if cache and len(cache) > 0 and cache[0] and cache[0].strip():
        patron_id_from_cache = cache[0].strip()
    else:
        messagebox.showwarning("Cache Error", "Patron ID not found in cache. This might cause issues if cache is re-written.")

    default_fp1 = "C:\\Program Files\\Fallout76\\Fallout76.exe"
    default_fp2 = "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
    user_docs = os.path.expanduser("~\\Documents") # Finds user's Documents folder
    default_fp3 = os.path.join(user_docs, "My Games", "Fallout 76", "Fallout76Prefs.ini")

    fp1_value = default_fp1
    if cache and len(cache) > 1 and cache[1] and cache[1].strip() != "None":
        fp1_value = cache[1].strip()

    fp2_value = default_fp2
    if cache and len(cache) > 2 and cache[2] and cache[2].strip() != "None":
        fp2_value = cache[2].strip()

    fp3_value = default_fp3
    if cache and len(cache) > 3 and cache[3] and cache[3].strip() != "None":
        fp3_value = cache[3].strip()
    
    cache_ini_vals = []
    for i in range(4, 9):
        if cache and len(cache) > i and cache[i] and cache[i].strip() != "None":
            cache_ini_vals.append(cache[i].strip())
    
    filepath1_var = tk.StringVar(value=fp1_value)
    filepath2_var = tk.StringVar(value=fp2_value)
    filepath3_var = tk.StringVar(value=fp3_value)
    cache_ini_vals_var = tk.StringVar(value=", ".join(cache_ini_vals))


    # --- Action Functions ---
    def start_bot_action():
        global bot_process
        fp1 = filepath1_var.get()
        fp2 = filepath2_var.get()
        fp3 = filepath3_var.get()
        cache_ini_vals = cache_ini_vals_var.get().split(", ")
        
        
        if not all([fp1, fp2, fp3]) or "None" in [fp1, fp2, fp3]:
            messagebox.showwarning("Input Missing", "Please provide all three filepaths.")
            if status_label_main: status_label_main.config(text="Status: Error - Missing filepaths")
            return

        ini_settings = parse_ini_file(fp3)
        if ini_settings is None:
            # The parse_ini_file function already showed an error message.
            if status_label_main: status_label_main.config(text="Status: Error - Failed to read INI file.")
            return # Stop execution if parsing failed
        
        if status_label_main: status_label_main.config(text=f"Status: Starting bot...")
        print(f"Starting bot with Filepath 1: {fp1}")
        print(f"Starting bot with Filepath 2: {fp2}")
        print(f"Starting bot with INI Filepath: {fp3}")
            
        if bot_process and bot_process.is_alive():
            print("Terminating existing bot process before starting a new one...")
            terminate_bot_process()
            if status_label_main: status_label_main.config(text="Status: Terminated old bot, starting new.")
        if ini_settings['height'] != str(800) and ini_settings['width'] != str(1280) and ini_settings['loc_x'] != str(0) and ini_settings['loc_y'] != str(0) and ini_settings['fullscreen'] != "0" and ini_settings['borderless'] != "1":
            write_file("cache.txt", f"{patron_id_from_cache}\n{fp1}\n{fp2}\n{fp3}\n{ini_settings['height']}\n{ini_settings['width']}\n{ini_settings['loc_x']}\n{ini_settings['loc_y']}\n{ini_settings['fullscreen']}\n{ini_settings['borderless']}\n", mode='w')
        try:
            bot_process = multiprocessing.Process(
                target=main, 
                args=(
                    fp2, 
                    fp1,
                    fp3, 
                    ini_settings['height'],
                    ini_settings['width'],
                    ini_settings['loc_x'],
                    ini_settings['loc_y'],
                    ini_settings['fullscreen'],
                    ini_settings['borderless']
                )
            )
            bot_process.start()
            print(f"Bot process started with PID: {bot_process.pid}.")
            if status_label_main: status_label_main.config(text=f"Status: Bot process initiated (PID: {bot_process.pid})")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to run main process: {e}")
            if status_label_main: status_label_main.config(text=f"Status: Error starting process - {e}")
            bot_process = None

    def browse_file_action(entry_var, title="Select File", executable_only=True):
        if executable_only: filetypes=(("Executable files", "*.exe"), ("All files", "*.*"), ("Text files", "*.txt"))
        else: filetypes=(("All files", "*.*"), ("Text files", "*.txt"))
        filename = filedialog.askopenfilename(
            title=title,
            filetypes=filetypes
        )
        if filename:
            entry_var.set(filename)
            if status_label_main: status_label_main.config(text=f"Status: File selected - {filename.split('/')[-1]}")

    # --- Main Content Frame ---
    content_frame = tk.Frame(root_window, padx=10, pady=10)
    content_frame.pack(fill=tk.BOTH, expand=True)

    # --- Controls Section (Start Button Only) ---
    controls_frame = tk.Frame(content_frame)
    controls_frame.pack(pady=(0, 15), fill=tk.X)

    start_button = tk.Button(controls_frame, text="Start Bot", command=start_bot_action, width=12, height=2)
    start_button.pack(side=tk.LEFT, padx=(0,10))
    CreateToolTip(start_button, "Start the bot process using the specified filepaths.")

    # F5 instruction label (packed next, from the right, so it's to the left of Exit)
    f5_info_label = tk.Label(controls_frame, text="F5 to Stop Bot", fg="red") # fg makes it less prominent
    f5_info_label.pack(side=tk.LEFT, padx=(0,10)) # padx to space it from Exit button
    
    # --- Filepath Input Sections ---
    filepaths_group = tk.LabelFrame(content_frame, text="Configuration Filepaths", padx=10, pady=10)
    filepaths_group.pack(fill=tk.X, expand=True)

    # Filepath 1
    fp1_frame = tk.Frame(filepaths_group)
    fp1_frame.pack(fill=tk.X, pady=5)
    tk.Label(fp1_frame, text="Fallout76.exe:", width=12, anchor='w').pack(side=tk.LEFT, padx=(0,5))
    entry1 = tk.Entry(fp1_frame, textvariable=filepath1_var)
    entry1.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
    CreateToolTip(entry1, "Enter the path for Fallout76.exe.")
    browse1_button = tk.Button(fp1_frame, text="Browse...", command=lambda: browse_file_action(filepath1_var, "Select Filepath To Fallout76.exe"))
    browse1_button.pack(side=tk.LEFT)

    # Filepath 2
    fp2_frame = tk.Frame(filepaths_group)
    fp2_frame.pack(fill=tk.X, pady=5)
    tk.Label(fp2_frame, text="tesseract.exe:", width=12, anchor='w').pack(side=tk.LEFT, padx=(0,5))
    entry2 = tk.Entry(fp2_frame, textvariable=filepath2_var)
    entry2.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
    CreateToolTip(entry2, "Enter the path for tesseract.exe.")
    browse2_button = tk.Button(fp2_frame, text="Browse...", command=lambda: browse_file_action(filepath2_var, "Select Filepath To tesseract.exe"))
    browse2_button.pack(side=tk.LEFT)
    
    # Filepath 3
    fp3_frame = tk.Frame(filepaths_group)
    fp3_frame.pack(fill=tk.X, pady=5)
    tk.Label(fp3_frame, text="Fallout76Prefs.ini:", width=12, anchor='w').pack(side=tk.LEFT, padx=(0,5))
    entry2 = tk.Entry(fp3_frame, textvariable=filepath3_var)
    entry2.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
    CreateToolTip(entry2, "Enter the path for Fallout76Prefs.ini file.")
    browse2_button = tk.Button(fp3_frame, text="Browse...", command=lambda: browse_file_action(filepath3_var, "Select Filepath To Fallout76Prefs.ini", executable_only=False))
    browse2_button.pack(side=tk.LEFT)
    
    start_global_f5_listener()
    
    root_window.protocol("WM_DELETE_WINDOW", on_app_closing)
    
    root_window.after(2000, check_bot_status)

def reset_ini():
    """
    Reads display settings from cache.txt and writes them back to the INI file,
    preserving other settings.
    """
    cache_filepath = "cache.txt"

    try:
        with open(cache_filepath, 'r') as f:
            lines = f.readlines()

        # Ensure the cache file has the expected number of lines
        if len(lines) < 10:
            print(f"Error: {cache_filepath} is missing required configuration data.")
            return

        # Strip newline characters from each line
        # The INI file path is on the 4th line (index 3)
        ini_path = lines[3].strip()

        if not os.path.exists(ini_path):
            print(f"Error: INI file not found at {ini_path}")
            return

        # Create the configuration object and read the existing INI file
        config = configparser.ConfigParser()
        config.read(ini_path)

        # Ensure the 'Display' section exists
        if not config.has_section('Display'):
            config.add_section('Display')

        # Update the specific values in the 'Display' section
        config.set('Display', 'iSize H', lines[4].strip())
        config.set('Display', 'iSize W', lines[5].strip())
        config.set('Display', 'iLocation X', lines[6].strip())
        config.set('Display', 'iLocation Y', lines[7].strip())
        config.set('Display', 'bFull Screen', lines[8].strip())
        config.set('Display', 'bBorderless', lines[9].strip())

        # Write the updated configuration back to the INI file
        with open(ini_path, 'w') as configfile:
            config.write(configfile)
        print(f"Settings in [Display] section of {ini_path} have been updated from {cache_filepath}")

    except FileNotFoundError:
        print(f"Error: {cache_filepath} not found.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def cleanup():
    """Cleans up resources on application exit."""
    reset_ini()
    terminate_bot_process()
    stop_global_f5_listener()

# --- Main Execution ---
if __name__ == "__main__":
    # Required for multiprocessing on Windows when freezing app (e.g. PyInstaller)
    multiprocessing.freeze_support() 
    
    # Note: On macOS, you may need to grant 'Input Monitoring' permission
    # to your terminal or Python executable in System Settings > Privacy & Security
    # for the global F5 hotkey to work.
    # On some Linux distributions (especially with Wayland), global hotkeys
    # might also have restrictions or require specific setup.

    root = tk.Tk()
    root_tk_instance = root # Initialize global reference
    setup_login_window(root)
    root.mainloop()

    # Ensure listener is stopped if mainloop somehow exits without on_app_closing
    # (e.g., if root.quit() was called elsewhere, though current code uses destroy)
    cleanup()