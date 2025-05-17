# setup.py
from distutils.core import setup
import py2exe
import glob
import os

# --- Configuration ---
APP_NAME = "FalloutBotGUI"
MAIN_SCRIPT_FILE = 'ui.py'  # Your main Tkinter GUI script

# Optional: If you have an .ico file for your application
# ICON_FILE = 'app_icon.ico'

# --- py2exe Options ---
# For more details on options: http://www.py2exe.org/index.cgi/ListOfOptions
py2exe_options = {
    "bundle_files": 3,  # 1: bundle everything into a single EXE (can be large, sometimes problematic)
                        # 2: bundle everything but the Python interpreter
                        # 3: don't bundle (creates library.zip and DLLs, often most compatible)
    "compressed": True,
    "optimize": 2,      # Create .pyo files
    "packages": [
        "tkinter",
        "requests",
        "psutil",
        "pyautogui",
        "certifi",      # requests dependency for SSL certificates
        # "win32com",   # If you were using win32com, uncomment
    ],
    "includes": [
        "json",
        "multiprocessing", # Ensure multiprocessing is included
        "logging",
        "logging.handlers", # For RotatingFileHandler
        "win32gui",     # For win32gui functions
        "win32con",     # For win32con constants
        # Your custom modules (py2exe should find them if imported, but explicit is safer)
        "emailapi",
        "press",
        "readtext",
        "testmain",     # The bot logic script imported by gui.py
    ],
    # "dll_excludes": ["MSVCP90.dll", "w9xpopen.exe"], # Usually not needed for modern Python/py2exe
    "excludes": [
        # Exclude modules you're sure you don't need to reduce size
        "doctest", "pdb", "unittest", "difflib", "inspect",
        "_gtkagg", "_tkagg", "bsddb", "curses", "email.test",
        "pywin.debugger", "pywin.debugger.dbgcon", "pywin.dialogs", "tcl",
        # "Tkconstants", "Tkinter", "ttk" # If using Python 3, tkinter is the package
    ],
    # "dist_dir": "dist_custom_name", # If you want a custom output directory name
}

# --- Data Files ---
# (destination_folder_in_dist, [list_of_source_files_or_glob_patterns])
data_files = []

# Add all PNG files from the 'icons' directory
icon_files = glob.glob('icons/*.png')
if icon_files:
    data_files.append(('icons', icon_files))
else:
    print("Warning: No icon files found in 'icons/' directory. Ensure it exists and contains your .png files.")

# If you have issues with Tkinter/TCL files not being found by the bundled app,
# you might need to explicitly copy them. This is a common workaround.
# Note: Adjust paths and versions (e.g., tcl8.6, tk8.6) as per your Python's Tkinter.
# import tkinter
# TCL_ROOT = os.path.dirname(os.path.dirname(tkinter.__file__)) # Try to find TCL/TK root
# tcl_dll_path = os.path.join(TCL_ROOT, 'tcl', 'tcl8.6') # Example path
# tk_dll_path = os.path.join(TCL_ROOT, 'tcl', 'tk8.6')   # Example path

# if os.path.exists(tcl_dll_path) and os.path.exists(tk_dll_path):
#     data_files.extend([
#         ('tcl/tcl8.6', glob.glob(os.path.join(tcl_dll_path, '*.*'))),
#         ('tcl/tk8.6', glob.glob(os.path.join(tk_dll_path, '*.*')))
#     ])
#     # Also copy DLLs if needed
#     # python_dll_dir = os.path.dirname(sys.executable)
#     # data_files.append(('.', [os.path.join(python_dll_dir, 'tcl86t.dll'), os.path.join(python_dll_dir, 'tk86t.dll')]))
# else:
#     print(f"Warning: Could not find TCL/TK directories at expected paths ({tcl_dll_path}, {tk_dll_path}). Tkinter might not work in the .exe.")


# --- Setup Configuration ---
setup_dict = {
    "options": {"py2exe": py2exe_options},
    "data_files": data_files,
    "zipfile": "library.zip",  # Name of the shared archive where Python modules are stored
}

# For GUI applications, use 'windows'. For console, use 'console'.
# 'dest_base' determines the name of the .exe without the extension.
windows_entry_point = {
    "script": MAIN_SCRIPT_FILE,
    "dest_base": APP_NAME
}
# if 'ICON_FILE' in globals() and os.path.exists(ICON_FILE):
#     windows_entry_point["icon_resources"] = [(1, ICON_FILE)]

setup_dict["windows"] = [windows_entry_point]

# --- Run Setup ---
setup(**setup_dict)

print("\nPy2exe build process finished.")
print(f"Look for the executable and associated files in the 'dist/{APP_NAME}.exe' directory.")
print("Important considerations:")
print("1. Test the application thoroughly from the 'dist' directory.")
print("2. The 'cache.txt' and 'fo76_bot.log' files will be created in the same directory as the .exe when run.")
print("3. Tesseract-OCR and Fallout76.exe are NOT bundled. The user must have them installed, and the paths must be correctly set in your application's GUI, as you've designed.")
print("4. If you encounter 'DLL load failed' or similar errors, especially for tkinter, you might need to adjust 'data_files' to include specific TCL/TK DLLs or directories (see commented-out section).")
print("5. Ensure `multiprocessing.freeze_support()` is called in your `gui.py`'s `if __name__ == '__main__':` block, which you already have.")