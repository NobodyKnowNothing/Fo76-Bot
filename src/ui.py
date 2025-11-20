import tkinter as tk
from tkinter import messagebox, filedialog
import multiprocessing
import requests
import json
import webbrowser
import http.server
import socketserver
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

# --- PATREON CONFIGURATION ---
PATREON_CLIENT_ID = "4ll9uHw4PikXcPodKO7RbEUtu3D3s4JDgwPKGdwYnh8dM8EB51Ynsg1YHja_goc8"
PATREON_CLIENT_SECRET = "MT2kVn_mCbhHw8pDZo_-MyqUPVbWyZ8dG_dFzGilC-JkcLHFhOPooMjmF8nO4Wcd"
PATREON_CAMPAIGN_ID = "2272743"
REDIRECT_URI = "http://localhost:5000/callback"
PORT = 5000
CACHE_FILE = "cache.txt"

# --- Global variables ---
bot_process = None
status_label_main = None 
status_label_login = None
root_tk_instance = None 
keyboard_listener = None 
auth_server = None 
auth_code = None 

# --- Helper Functions ---

def call_url(
    url: str,
    method: str = "GET",
    params: dict = None,
    data: dict = None,
    json_payload: dict = None,
    headers: dict = None,
    timeout: int = 15,
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
        
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError:
             result["error_message"] = f"HTTP {response.status_code}: {response.text}"
        
        # Try to parse JSON regardless of content type if it looks like it might be JSON, 
        # or if the content type suggests it.
        # Patreon returns application/vnd.api+json which failed the previous strict check.
        json_parsed = False
        try:
            result["data"] = response.json()
            json_parsed = True
            if not result["error_message"]: result["success"] = True
        except json.JSONDecodeError:
            pass
            
        if not json_parsed:
            if "text/" in result["content_type"]:
                result["data"] = response.text
                if not result["error_message"]: result["success"] = True
            else:
                result["data"] = response.content
                if not result["error_message"]: result["success"] = True
            
    except Exception as e:
        result["error_message"] = f"An unexpected error occurred: {e}"
    return result

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
    """Reads cache.txt and returns (refresh_token, fp1, fp2, fp3, ini_settings_list, fp1_secondary, use_secondary)."""
    if not os.path.exists(CACHE_FILE):
        return None, "", "", "", [], "", False
    
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            lines = f.read().splitlines()
        
        # Pad lines if missing
        while len(lines) < 12:
            lines.append("")

        r_token = lines[0].strip()
        fp1 = lines[1].strip()
        fp2 = lines[2].strip()
        fp3 = lines[3].strip()
        ini_settings = lines[4:10] # List of 6 strings
        fp1_sec = lines[10].strip()
        use_sec = lines[11].strip().lower() == 'true'
        
        return r_token, fp1, fp2, fp3, ini_settings, fp1_sec, use_sec
    except Exception:
        return None, "", "", "", [], "", False

def save_cached_data(refresh_token, fp1, fp2, fp3, ini_settings, fp1_sec, use_sec):
    """Saves data to cache.txt."""
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            f.write(f"{refresh_token or ''}\n")
            f.write(f"{fp1 or ''}\n")
            f.write(f"{fp2 or ''}\n")
            f.write(f"{fp3 or ''}\n")
            
            # ini_settings should be a list of 6 values or a dict
            if isinstance(ini_settings, dict):
                f.write(f"{ini_settings.get('height', '')}\n")
                f.write(f"{ini_settings.get('width', '')}\n")
                f.write(f"{ini_settings.get('loc_x', '')}\n")
                f.write(f"{ini_settings.get('loc_y', '')}\n")
                f.write(f"{ini_settings.get('fullscreen', '')}\n")
                f.write(f"{ini_settings.get('borderless', '')}\n")
            elif isinstance(ini_settings, list):
                for i in range(6):
                    val = ini_settings[i] if i < len(ini_settings) else ""
                    f.write(f"{val}\n")
            else:
                # Fallback empty
                for _ in range(6): f.write("\n")
            
            f.write(f"{fp1_sec or ''}\n")
            f.write(f"{'true' if use_sec else 'false'}")
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
            lines = f.readlines()

        if len(lines) < 10:
            print(f"Error: {CACHE_FILE} is missing required configuration data.")
            return

        ini_path = lines[3].strip()

        if not os.path.exists(ini_path):
            print(f"Error: INI file not found at {ini_path}")
            return

        config = configparser.ConfigParser()
        config.read(ini_path)

        if not config.has_section('Display'):
            config.add_section('Display')

        config.set('Display', 'iSize H', lines[4].strip())
        config.set('Display', 'iSize W', lines[5].strip())
        config.set('Display', 'iLocation X', lines[6].strip())
        config.set('Display', 'iLocation Y', lines[7].strip())
        config.set('Display', 'bFull Screen', lines[8].strip())
        config.set('Display', 'bBorderless', lines[9].strip())

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
    if auth_server:
        auth_server.shutdown()
        auth_server.server_close()
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

# --- Patreon Logic ---

class OAuthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        parsed_path = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed_path.query)
        
        if 'code' in query:
            auth_code = query['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Login Successful!</h1><script>window.close();</script></body></html>")
            threading.Thread(target=self.server.shutdown).start()
        else:
            self.send_response(400)
            self.wfile.write(b"Error: No code received.")

def validate_patreon_membership(access_token):
    """Checks if user is an active patron of the campaign."""
    url = "https://www.patreon.com/api/oauth2/v2/identity"
    params = {
        "include": "memberships.campaign", 
        "fields[member]": "patron_status,lifetime_support_cents"
    }
    headers = {"Authorization": f"Bearer {access_token}"}
    
    result = call_url(url, params=params, headers=headers)
    
    if not result['success']:
        return False, f"API Error: {result.get('error_message')}"
    
    data = result['data']
    included = data.get('included', [])
    
    for item in included:
        if item.get('type') == 'member':
            relationships = item.get('relationships', {})
            campaign_data = relationships.get('campaign', {}).get('data', {})
            
            if campaign_data.get('id') == PATREON_CAMPAIGN_ID:
                status = item.get('attributes', {}).get('patron_status')
                if status == 'active_patron':
                    return True, "Active"
                else:
                    return False, f"Status is '{status}'"

    return False, "Not a member of this campaign."

def refresh_patreon_token(old_refresh_token):
    """Uses the refresh token to get a NEW access token."""
    token_url = "https://www.patreon.com/api/oauth2/token"
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": old_refresh_token,
        "client_id": PATREON_CLIENT_ID,
        "client_secret": PATREON_CLIENT_SECRET
    }
    
    result = call_url(token_url, method="POST", data=payload)
    
    if result['success']:
        new_access = result['data'].get('access_token')
        new_refresh = result['data'].get('refresh_token')
        return True, new_access, new_refresh
    else:
        return False, None, result.get('error_message')

def start_patreon_login_flow(window):
    global auth_server, auth_code
    
    if status_label_login:
        status_label_login.config(text="Waiting for browser login...", fg="blue")
    window.update()

    auth_url = (
        f"https://www.patreon.com/oauth2/authorize"
        f"?response_type=code"
        f"&client_id={PATREON_CLIENT_ID}"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
        f"&scope=identity%20identity.memberships"
    )

    auth_code = None
    try:
        auth_server = socketserver.TCPServer(("", PORT), OAuthHandler)
    except OSError:
        if status_label_login:
            status_label_login.config(text=f"Port {PORT} occupied.", fg="red")
        return

    server_thread = threading.Thread(target=auth_server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    webbrowser.open(auth_url)

    def check_for_code():
        global auth_code, auth_server
        if auth_code:
            auth_server.server_close()
            auth_server = None
            if status_label_login:
                status_label_login.config(text="Verifying token...", fg="orange")
            exchange_code_for_token(auth_code, window)
        elif server_thread.is_alive():
            window.after(1000, check_for_code)
        else:
            if status_label_login:
                status_label_login.config(text="Login timed out.", fg="red")
            if auth_server: 
                auth_server.server_close()
                auth_server = None

    window.after(1000, check_for_code)

def exchange_code_for_token(code, window):
    token_url = "https://www.patreon.com/api/oauth2/token"
    payload = {
        "code": code,
        "grant_type": "authorization_code",
        "client_id": PATREON_CLIENT_ID,
        "client_secret": PATREON_CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI
    }
    
    result = call_url(token_url, method="POST", data=payload)
    
    if not result['success']:
        if status_label_login:
            status_label_login.config(text=f"Login Failed: {result.get('error_message')}", fg="red")
        return

    access_token = result['data'].get('access_token')
    refresh_token = result['data'].get('refresh_token')

    is_valid, msg = validate_patreon_membership(access_token)
    
    if is_valid:
        # Save credentials - preserve existing paths if possible, but we are in login flow so maybe we just read what we can
        _, fp1, fp2, fp3, ini_settings, fp1_sec, use_sec = get_cached_data()
        save_cached_data(refresh_token, fp1, fp2, fp3, ini_settings, fp1_sec, use_sec)
        
        clear_window()
        setup_main_app_window(window)
    else:
        if status_label_login:
            status_label_login.config(text=f"Access Denied: {msg}", fg="red")

# --- Auto Login Logic ---

def attempt_auto_login(window):
    """Runs in a background thread to check cache validity."""
    cached_refresh, fp1, fp2, fp3, ini_settings, fp1_sec, use_sec = get_cached_data()
    
    if not cached_refresh or len(cached_refresh) < 5:
        # No valid token, stop here and wait for user input
        return

    # We have a token, update UI to show we are working
    def update_ui_checking():
        if status_label_login:
            status_label_login.config(text="Verifying saved session...", fg="blue")
    window.after(0, update_ui_checking)

    # Try to refresh the token
    success, new_access, new_refresh = refresh_patreon_token(cached_refresh)

    if success:
        # Token refreshed, now check membership
        is_member, msg = validate_patreon_membership(new_access)
        
        if is_member:
            # Success! Save new refresh token
            save_cached_data(new_refresh, fp1, fp2, fp3, ini_settings, fp1_sec, use_sec)
            
            # Switch to main window
            def switch_to_main():
                clear_window()
                setup_main_app_window(window)
            window.after(0, switch_to_main)
            return
        else:
            # Token valid, but membership expired
            def show_error():
                if status_label_login:
                    status_label_login.config(text=f"Session Expired: {msg}", fg="red")
            window.after(0, show_error)
    else:
        # Refresh failed (token revoked or expired completely)
        def show_fail():
            if status_label_login:
                status_label_login.config(text="Session expired. Please log in again.", fg="orange")
        window.after(0, show_fail)

# --- UI Setup ---

def clear_window():
    global root_tk_instance
    if root_tk_instance:
        for widget in root_tk_instance.winfo_children():
            widget.destroy()

def setup_login_window(window):
    global status_label_login, root_tk_instance
    root_tk_instance = window

    window.title("Fallout Bot Login")
    window.geometry("350x220")

    tk.Label(window, text="Authentication Required", font=("Arial", 12, "bold")).pack(pady=(20, 10))
    tk.Label(window, text="You must be an active Patron to use this bot.", font=("Arial", 9)).pack(pady=5)

    login_btn = tk.Button(window, text="Login with Patreon", bg="#f96854", fg="white", 
                          font=("Arial", 10, "bold"), height=2, width=20,
                          command=lambda: start_patreon_login_flow(window))
    login_btn.pack(pady=20)

    status_label_login = tk.Label(window, text="", fg="red", wraplength=300)
    status_label_login.pack(pady=5)
    
    # Trigger auto-login check in background
    threading.Thread(target=attempt_auto_login, args=(window,), daemon=True).start()

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
    current_refresh_token, cached_fp1, cached_fp2, cached_fp3, cached_ini, cached_fp1_sec, cached_use_sec = get_cached_data()
    
    # Defaults
    fp1_val = cached_fp1 if cached_fp1 else "C:\\Program Files\\Fallout76\\Fallout76.exe"
    fp2_val = cached_fp2 if cached_fp2 else "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
    user_docs = os.path.expanduser("~\\Documents")
    fp3_val = cached_fp3 if cached_fp3 else os.path.join(user_docs, "My Games", "Fallout 76", "Fallout76Prefs.ini")
    fp1_sec_val = cached_fp1_sec if cached_fp1_sec else ""

    filepath1_var = tk.StringVar(value=fp1_val)
    filepath2_var = tk.StringVar(value=fp2_val)
    filepath3_var = tk.StringVar(value=fp3_val)
    filepath1_sec_var = tk.StringVar(value=fp1_sec_val)
    use_secondary_var = tk.BooleanVar(value=cached_use_sec)
    show_secondary_var = tk.BooleanVar(value=False) 

    def start_bot_action():
        global bot_process
        fp1 = filepath1_var.get()
        fp2 = filepath2_var.get()
        fp3 = filepath3_var.get()
        fp1_sec = filepath1_sec_var.get()
        use_sec = use_secondary_var.get()

        # Determine which game path to use
        game_path_to_use = fp1
        if use_sec and show_secondary_var.get(): 
             game_path_to_use = fp1_sec

        if not game_path_to_use or not fp2 or not fp3:
            messagebox.showwarning("Missing Info", "Please provide all required filepaths.")
            return
            
        ini_settings = parse_ini_file(fp3)
        if ini_settings is None:
            if status_label_main: status_label_main.config(text="Status: Error - Failed to read INI file.")
            return

        if status_label_main: status_label_main.config(text=f"Status: Starting...")
        
        if bot_process and bot_process.is_alive():
            terminate_bot_process()

        # Update cache 
        curr_token, _, _, _, _, _, _ = get_cached_data()
        save_cached_data(curr_token, fp1, fp2, fp3, ini_settings, fp1_sec, use_sec)

        try:
            # Pass the selected game path as fp1 (the game executable)
            # main(fp2, fp1, fp3, h, w, x, y, fs, bl)
            bot_process = multiprocessing.Process(
                target=main, 
                args=(
                    fp2, 
                    game_path_to_use, # Use the selected path
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
    use_chk = tk.Checkbutton(row_sec_use, text="Use this version instead of primary", variable=use_secondary_var)
    use_chk.pack(side=tk.LEFT)

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
    setup_login_window(root)
    root.protocol("WM_DELETE_WINDOW", on_app_closing)
    root.mainloop()
    cleanup()
