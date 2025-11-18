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

# --- Import your bot logic ---
try:
    from testmain import main
except ImportError:
    # Fallback for testing if testmain doesn't exist in your directory
    def main(fp1, fp2):
        print(f"MOCK BOT RUNNING with {fp1} and {fp2}")
        import time
        while True:
            time.sleep(1)

# --- PATREON CONFIGURATION (YOU MUST FILL THESE IN) ---
PATREON_CLIENT_ID = "4ll9uHw4PikXcPodKO7RbEUtu3D3s4JDgwPKGdwYnh8dM8EB51Ynsg1YHja_goc8"
PATREON_CLIENT_SECRET = "MT2kVn_mCbhHw8pDZo_-MyqUPVbWyZ8dG_dFzGilC-JkcLHFhOPooMjmF8nO4Wcd"
PATREON_CAMPAIGN_ID = "2272743" # The ID of the campaign they must be a member of
REDIRECT_URI = "http://localhost:5000/callback"
PORT = 5000

# --- Global variables ---
bot_process = None
status_label_main = None 
root_tk_instance = None 
keyboard_listener = None 
auth_server = None # Reference to the local HTTP server
auth_code = None # Stores the code received from Patreon

# --- Functions ---

class CreateToolTip(object):
    """ Create a tooltip for a given widget. """
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

def call_url(url, method="GET", params=None, data=None, json_payload=None, headers=None):
    """Generic URL caller."""
    result = {"success": False, "data": None, "error_message": None}
    try:
        req_headers = headers if headers else {}
        resp = requests.request(
            method=method.upper(),
            url=url,
            params=params,
            data=data,
            json=json_payload,
            headers=req_headers,
            timeout=15
        )
        resp.raise_for_status()
        try:
            result["data"] = resp.json()
            result["success"] = True
        except json.JSONDecodeError:
            result["data"] = resp.text
            result["success"] = True
    except Exception as e:
        result["error_message"] = str(e)
        if hasattr(e, 'response') and e.response is not None:
             result["error_message"] += f" | Server said: {e.response.text}"
    return result

def write_file(filepath, content, mode='w', encoding='utf-8'):
    try:
        with open(filepath, mode, encoding=encoding) as file:
            file.write(content)
        return True
    except Exception as e:
        print(f"Write error: {e}")
        return False

def read_file(filepath, encoding='utf-8'):
    try:
        with open(filepath, 'r', encoding=encoding) as file:
            content = file.read()
        return content.splitlines() 
    except:
        return None

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
    
    # Ensure web server is shut down if it's running
    if auth_server:
        auth_server.shutdown()
        auth_server.server_close()
        
    if root_tk_instance:
        root_tk_instance.destroy()

# --- Global Hotkey Logic ---
def _kill_bot_on_f5_action():
    global status_label_main, bot_process
    print("F5 triggered.")
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

# --- Patreon OAuth Logic ---

class OAuthHandler(http.server.BaseHTTPRequestHandler):
    """Handles the redirect from Patreon."""
    def do_GET(self):
        global auth_code
        parsed_path = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed_path.query)
        
        if 'code' in query:
            auth_code = query['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"<html><head><title>Login Successful</title></head><body style='font-family:sans-serif; text-align:center; margin-top:50px;'><h1>Login Successful!</h1><p>You can close this tab and return to the bot.</p><script>window.close();</script></body></html>")
            
            # Signal the main thread that we got the code (via server shutdown)
            threading.Thread(target=self.server.shutdown).start()
        else:
            self.send_response(400)
            self.wfile.write(b"Error: No code received.")

def validate_patreon_membership(access_token):
    """
    Fetches user identity and memberships, checks if they are an active patron 
    of the configured CAMPAIGN_ID.
    """
    # 1. Get Identity + Memberships
    # We request the 'memberships' relation, and specifically the 'campaign' relation within that
    url = "https://www.patreon.com/api/oauth2/v2/identity"
    params = {
        "include": "memberships.campaign", 
        "fields[member]": "patron_status,lifetime_support_cents"
    }
    headers = {"Authorization": f"Bearer {access_token}"}
    
    result = call_url(url, params=params, headers=headers)
    
    if not result['success']:
        return False, f"API Call Failed: {result.get('error_message')}"
    
    data = result['data']
    
    # 2. Parse JSON:API response
    # 'included' contains the member objects (the link between user and campaign)
    included = data.get('included', [])
    user_id = data.get('data', {}).get('id')
    
    is_active = False
    found_campaign = False
    
    for item in included:
        if item.get('type') == 'member':
            # Check if this membership belongs to the target campaign
            # In V2, relationships.campaign.data.id holds the campaign ID
            relationships = item.get('relationships', {})
            campaign_data = relationships.get('campaign', {}).get('data', {})
            
            if campaign_data.get('id') == PATREON_CAMPAIGN_ID:
                found_campaign = True
                # Check status
                attributes = item.get('attributes', {})
                status = attributes.get('patron_status')
                
                if status == 'active_patron':
                    is_active = True
                    break
                else:
                    return False, f"Patron status is '{status}', not 'active_patron'."

    if not found_campaign:
        return False, "User is not a member of the specified Campaign."
        
    if is_active:
        return True, user_id
    
    return False, "Unknown validation error."

def start_patreon_login_flow(window):
    global auth_server, auth_code, root_tk_instance
    
    status_label.config(text="Waiting for browser login...", fg="blue")
    window.update()

    # 1. Build Auth URL
    auth_url = (
        f"https://www.patreon.com/oauth2/authorize"
        f"?response_type=code"
        f"&client_id={PATREON_CLIENT_ID}"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
        f"&scope=identity%20identity.memberships"
    )

    # 2. Start Local Server in a Thread
    auth_code = None
    try:
        auth_server = socketserver.TCPServer(("", PORT), OAuthHandler)
    except OSError as e:
        status_label.config(text=f"Port {PORT} occupied. Is app running?", fg="red")
        return

    server_thread = threading.Thread(target=auth_server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    # 3. Open Browser
    webbrowser.open(auth_url)

    # 4. Poll for the code (avoids freezing GUI entirely vs blocking wait)
    def check_for_code():
        global auth_code, auth_server
        if auth_code:
            # We got the code!
            auth_server.server_close() # Cleanup
            auth_server = None
            status_label.config(text="Verifying token...", fg="orange")
            exchange_code_for_token(auth_code, window)
        elif server_thread.is_alive():
            # Keep waiting
            window.after(1000, check_for_code)
        else:
            status_label.config(text="Login timed out or failed.", fg="red")
            if auth_server: 
                auth_server.server_close()
                auth_server = None

    window.after(1000, check_for_code)

def exchange_code_for_token(code, window):
    # 1. Exchange Code for Token
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
        error_details = result.get('data', {})
        if isinstance(error_details, dict):
            # Patreon usually sends 'error' and 'error_description'
            actual_error = error_details.get('error_description', error_details.get('error', 'Unknown Error'))
        else:
            actual_error = result.get('error_message')

        print(f"FULL ERROR DEBUG: {result}") # Look at your console/terminal too
        status_label.config(text=f"Login Failed: {actual_error}", fg="red")
        return

    access_token = result['data'].get('access_token')
    refresh_token = result['data'].get('refresh_token') # Save this if you want persistent login later

    # 2. Validate Membership
    is_valid, msg = validate_patreon_membership(access_token)
    
    if is_valid:
        # msg contains user_id here
        user_id = msg
        clear_window()
        
        # Preserve filepaths
        cache_content = read_file('cache.txt')
        fp1, fp2 = "None", "None"
        if cache_content and len(cache_content) > 1: fp1 = cache_content[1]
        if cache_content and len(cache_content) > 2: fp2 = cache_content[2]
        
        # Save success to cache (using refresh token or user ID as marker)
        write_file("cache.txt", f"{refresh_token}\n{fp1}\n{fp2}", mode='w')
        
        setup_main_app_window(window)
    else:
        status_label.config(text=f"Access Denied: {msg}", fg="red")

def auto_login_check(window):
    # Optional: Implement refresh token logic here if desired
    # For now, we just check if a token exists in cache, but ideally
    # you verify the token against the API again.
    cache = read_file("cache.txt")
    if cache and len(cache) > 0 and len(cache[0]) > 10:
        # Basic assumption: if we have a long string in line 1, it's a refresh token
        # To be robust, you should use the refresh token to get a new access token here.
        # For this example, we will force a fresh login to be safe, or skip:
        print("Found cached credentials. Skipping login (Implement refresh logic for production).")
        # To auto-login:
        # clear_window()
        # setup_main_app_window(window)
        pass

def clear_window():
    global root_tk_instance
    if root_tk_instance:
        for widget in root_tk_instance.winfo_children():
            widget.destroy()

# --- UI Setup ---

def setup_login_window(window):
    global status_label, root_tk_instance
    root_tk_instance = window

    window.title("Fallout Bot Login")
    window.geometry("350x200")

    tk.Label(window, text="Authentication Required", font=("Arial", 12, "bold")).pack(pady=(20, 10))
    tk.Label(window, text="You must be an active Patron to use this bot.", font=("Arial", 9)).pack(pady=5)

    # OAuth Button
    login_btn = tk.Button(window, text="Login with Patreon", bg="#f96854", fg="white", 
                          font=("Arial", 10, "bold"), height=2, width=20,
                          command=lambda: start_patreon_login_flow(window))
    login_btn.pack(pady=20)

    status_label = tk.Label(window, text="", fg="red", wraplength=300)
    status_label.pack(pady=5)
    
    # Check if we have a saved token (Optional)
    # auto_login_check(window) 

def setup_main_app_window(root_window):
    global status_label_main, bot_process, root_tk_instance
    root_tk_instance = root_window

    root_window.title("Fallout Bot Control Panel")
    root_window.geometry("550x300")

    # --- Status Bar ---
    status_bar = tk.Frame(root_window, relief=tk.SUNKEN, bd=1)
    status_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=(5,0))
    
    exit_button = tk.Button(status_bar, text="Exit", command=on_app_closing)
    exit_button.pack(side=tk.RIGHT, padx=5, pady=2)

    status_label_main = tk.Label(status_bar, text="Status: Ready", anchor='w')
    status_label_main.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

    # --- Load cache ---
    cache = read_file("cache.txt")
    # Line 0 is now the refresh token/ID, ignore for display
    
    default_fp1 = "C:\\Program Files\\Fallout76\\Fallout76.exe"
    default_fp2 = "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
    
    fp1_value = cache[1].strip() if cache and len(cache) > 1 and cache[1] != "None" else default_fp1
    fp2_value = cache[2].strip() if cache and len(cache) > 2 and cache[2] != "None" else default_fp2

    filepath1_var = tk.StringVar(value=fp1_value)
    filepath2_var = tk.StringVar(value=fp2_value)

    def start_bot_action():
        global bot_process
        fp1 = filepath1_var.get()
        fp2 = filepath2_var.get()

        if not fp1 or not fp2:
            messagebox.showwarning("Missing Info", "Please provide filepaths.")
            return

        if status_label_main: status_label_main.config(text=f"Status: Starting...")
        
        if bot_process and bot_process.is_alive():
            terminate_bot_process()

        # Save cache (Token, FP1, FP2)
        token = cache[0] if cache else "UNKNOWN"
        write_file("cache.txt", f"{token}\n{fp1}\n{fp2}", mode='w')

        try:
            bot_process = multiprocessing.Process(target=main, args=(fp2, fp1))
            bot_process.start()
            if status_label_main: status_label_main.config(text=f"Status: Bot running (PID: {bot_process.pid})")
        except Exception as e:
            status_label_main.config(text=f"Status: Error {e}")

    def browse(var):
        f = filedialog.askopenfilename(filetypes=(("Exe", "*.exe"),("All", "*.*")))
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

    # File inputs
    group = tk.LabelFrame(content, text="Configuration", padx=10, pady=10)
    group.pack(fill=tk.X, expand=True)

    for txt, var in [("Fallout76.exe:", filepath1_var), ("tesseract.exe:", filepath2_var)]:
        row = tk.Frame(group)
        row.pack(fill=tk.X, pady=5)
        tk.Label(row, text=txt, width=15, anchor='w').pack(side=tk.LEFT)
        tk.Entry(row, textvariable=var).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        tk.Button(row, text="...", command=lambda v=var: browse(v)).pack(side=tk.LEFT)

    start_global_f5_listener()
    root_window.protocol("WM_DELETE_WINDOW", on_app_closing)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    root = tk.Tk()
    setup_login_window(root)
    root.mainloop()
    stop_global_f5_listener()