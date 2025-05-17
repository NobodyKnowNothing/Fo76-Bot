import tkinter as tk
from tkinter import messagebox, filedialog
from testmain import main # Assuming this is the main bot logic
import multiprocessing # Changed from threading
import requests
import json # For handling potential JSONDecodeError explicitly
# import threading # No longer needed

# --- Global variables for process management and UI elements ---
bot_process = None
status_label_main = None # Will be assigned in setup_main_app_window
root_tk_instance = None # To store the root Tk instance for closing and bindings

# --- Functions ---

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
    terminate_bot_process()
    if root_tk_instance:
        root_tk_instance.destroy()

def kill_bot_on_f5(event=None):
    """Handles F5 key press to kill the bot."""
    global status_label_main
    print("F5 pressed.")
    if bot_process and bot_process.is_alive():
        pid = bot_process.pid # Store before termination attempt
        if terminate_bot_process():
            if status_label_main:
                status_label_main.config(text=f"Status: Bot process (PID: {pid}) terminated by F5.")
        else:
            if status_label_main:
                status_label_main.config(text=f"Status: Failed to terminate bot (PID: {pid}) on F5.")
    else:
        if status_label_main:
            status_label_main.config(text="Status: No bot process running to terminate.")
        print("No bot process running to terminate via F5.")


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
    root_window.geometry("550x250")

    # --- Status Label for main window ---
    status_bar = tk.Frame(root_window, relief=tk.SUNKEN, bd=1)
    status_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=(5,0))
    status_label_main = tk.Label(status_bar, text="Status: Ready", anchor='w') # Assign to global
    status_label_main.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
    tk.Button(status_bar, text="Exit", command=on_app_closing).pack(side=tk.RIGHT, padx=5, pady=2)

    # --- Load cache for filepaths and patron ID ---
    cache = read_file("cache.txt")
    patron_id_from_cache = "UNKNOWN_PATRON" # Default
    if cache and len(cache) > 0 and cache[0] and cache[0].strip():
        patron_id_from_cache = cache[0].strip()
    else:
        messagebox.showwarning("Cache Error", "Patron ID not found in cache. This might cause issues if cache is re-written.")
        # Consider forcing re-login if patron_id is critical for operation beyond just cache writing
        # clear_window()
        # setup_login_window(root_tk_instance)
        # return


    default_fp1 = "C:\\Program Files\\Fallout76\\Fallout76.exe"
    default_fp2 = "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"

    fp1_value = default_fp1
    if cache and len(cache) > 1 and cache[1] and cache[1].strip() != "None":
        fp1_value = cache[1].strip()

    fp2_value = default_fp2
    if cache and len(cache) > 2 and cache[2] and cache[2].strip() != "None":
        fp2_value = cache[2].strip()

    filepath1_var = tk.StringVar(value=fp1_value)
    filepath2_var = tk.StringVar(value=fp2_value)


    # --- Action Functions ---
    def start_bot_action():
        global bot_process # Use the global bot_process variable
        fp1 = filepath1_var.get()
        fp2 = filepath2_var.get()

        if not fp1 or not fp2 or fp1 == "None" or fp2 == "None":
            messagebox.showwarning("Input Missing", "Please provide both filepaths.")
            if status_label_main: status_label_main.config(text="Status: Error - Missing filepaths")
            return

        if status_label_main: status_label_main.config(text=f"Status: Starting with {fp1}, {fp2}")
        print(f"Starting bot with Filepath 1: {fp1}")
        print(f"Starting bot with Filepath 2: {fp2}")
            
        # Terminate existing process if any before starting a new one
        if bot_process and bot_process.is_alive():
            print("Terminating existing bot process before starting a new one...")
            terminate_bot_process()
            if status_label_main: status_label_main.config(text="Status: Terminated old bot, starting new.")

        # Save current filepaths to cache using the patron_id loaded earlier
        write_file("cache.txt", f"{patron_id_from_cache}\n{fp1}\n{fp2}", mode='w')
        try:
            # Run the 'main' function from 'testmain' in a new process
            bot_process = multiprocessing.Process(target=main, args=(fp2, fp1))
            bot_process.start()
            print(f"Bot process started with PID: {bot_process.pid}.")
            if status_label_main: status_label_main.config(text=f"Status: Bot process initiated (PID: {bot_process.pid})")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to run main process: {e}")
            if status_label_main: status_label_main.config(text=f"Status: Error starting process - {e}")
            bot_process = None # Ensure it's None on failure

    def browse_file_action(entry_var, title="Select File"):
        filename = filedialog.askopenfilename(
            title=title,
            filetypes=(("Executable files", "*.exe"),("All files", "*.*"), ("Text files", "*.txt")) # Added .exe
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

    # Stop button and its action are removed.

    # --- Filepath Input Sections ---
    filepaths_group = tk.LabelFrame(content_frame, text="Configuration Filepaths", padx=10, pady=10)
    filepaths_group.pack(fill=tk.X, expand=True)

    # Filepath 1
    fp1_frame = tk.Frame(filepaths_group)
    fp1_frame.pack(fill=tk.X, pady=5)
    tk.Label(fp1_frame, text="Fallout76.exe:", width=12, anchor='w').pack(side=tk.LEFT, padx=(0,5)) # Adjusted width
    entry1 = tk.Entry(fp1_frame, textvariable=filepath1_var)
    entry1.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
    CreateToolTip(entry1, "Enter the path for Fallout76.exe.")
    browse1_button = tk.Button(fp1_frame, text="Browse...", command=lambda: browse_file_action(filepath1_var, "Select Filepath To Fallout76.exe"))
    browse1_button.pack(side=tk.LEFT)

    # Filepath 2
    fp2_frame = tk.Frame(filepaths_group)
    fp2_frame.pack(fill=tk.X, pady=5)
    tk.Label(fp2_frame, text="tesseract.exe:", width=12, anchor='w').pack(side=tk.LEFT, padx=(0,5)) # Adjusted width
    entry2 = tk.Entry(fp2_frame, textvariable=filepath2_var)
    entry2.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
    CreateToolTip(entry2, "Enter the path for tesseract.exe.")
    browse2_button = tk.Button(fp2_frame, text="Browse...", command=lambda: browse_file_action(filepath2_var, "Select Filepath To tesseract.exe"))
    browse2_button.pack(side=tk.LEFT)
    
    # Bind F5 key to kill_bot_on_f5 for the main application window
    root_window.bind('<F5>', kill_bot_on_f5)
    # Set the protocol for the window close button (the 'X')
    root_window.protocol("WM_DELETE_WINDOW", on_app_closing)


# --- Main Execution ---
if __name__ == "__main__":
    # Required for multiprocessing on Windows when freezing app (e.g. PyInstaller)
    multiprocessing.freeze_support() 
    
    root = tk.Tk()
    root_tk_instance = root # Initialize global reference
    setup_login_window(root)
    root.mainloop()