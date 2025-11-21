import subprocess
import os
import shutil
import sys

# --- Configuration ---
# Names of your original script files
ORIGINAL_BOT_SCRIPT_NAME = "testmain.py"
ORIGINAL_GUI_SCRIPT_NAME = "ui.py"

# Names for the scripts within the build process
BOT_MODULE_NAME_IN_BUILD = "fo76_bot_module.py"
GUI_APP_NAME_IN_BUILD = "main_gui_app.py" # This will be the entry point for PyInstaller

OUTPUT_EXE_NAME = "Fo76Bot" # PyInstaller will create a folder with this name (in --onedir mode)

# Custom modules used by fo76_bot.py (must be in the same dir as this compiler script)
CUSTOM_MODULE_FILES = ["press.py", "input.py", "readtext.py"]

# Data folders/files to bundle (relative to this compiler script's directory)
DATA_TO_BUNDLE = [
    ("icons", "icons")  # (source_on_disk, destination_in_bundle)
]

# --- Paths ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BUILD_DIR = os.path.join("D:\\", "Fo76Bot_Build", "build_temp") # Use D: drive for temp build
DIST_DIR = os.path.join("D:\\", "Fo76Bot_Build", "dist\\Fo76-Event-Bot")    # Use D: drive for output
PYINSTALLER_WORK_DIR = os.path.join(BUILD_DIR, "pyinstaller_work")
PYINSTALLER_SPEC_DIR = BUILD_DIR

# --- Helper Functions ---

def check_pyinstaller():
    """Checks if PyInstaller is available."""
    pyinstaller_exe_name = "pyinstaller.exe"
    pyinstaller_path = None

    # 1. Try shutil.which directly with .exe
    pyinstaller_path = shutil.which(pyinstaller_exe_name)

    # 2. If not found or it's a directory, try to find it relative to Python's Scripts directory
    if not pyinstaller_path or os.path.isdir(pyinstaller_path):
        python_exe_path = sys.executable
        python_dir = os.path.dirname(python_exe_path)
        
        # Common locations for Scripts directory relative to python.exe
        # For standard installs: <python_dir>\Scripts\pyinstaller.exe
        # For venvs: <python_dir>\pyinstaller.exe (if Scripts is the venv's bin)
        # or <venv_dir>\Scripts\pyinstaller.exe
        
        potential_paths = [
            os.path.join(python_dir, "Scripts", pyinstaller_exe_name), # Standard install
            os.path.join(python_dir, pyinstaller_exe_name),            # Some venv structures
            os.path.join(os.path.dirname(python_dir), "Scripts", pyinstaller_exe_name) # Venv (..\Scripts)
        ]
        
        for P_path in potential_paths:
            if os.path.isfile(P_path):
                pyinstaller_path = P_path
                break
        else: # If loop completes without break
            # If still not found, and shutil.which gave a directory, check inside that
            if pyinstaller_path and os.path.isdir(pyinstaller_path): # pyinstaller_path here is from initial shutil.which
                check_in_dir = os.path.join(pyinstaller_path, pyinstaller_exe_name)
                if os.path.isfile(check_in_dir):
                    pyinstaller_path = check_in_dir


    if not pyinstaller_path or not os.path.isfile(pyinstaller_path):
        print(f"ERROR: PyInstaller executable ('{pyinstaller_exe_name}') not found.")
        print("Please ensure PyInstaller is installed ('pip install pyinstaller') and your Python environment is correctly configured.")
        print(f"Python executable being used: {sys.executable}")
        sys.exit(1)
            
    print(f"PyInstaller found at: {pyinstaller_path}")
    return pyinstaller_path

def prepare_build_directory():
    """Creates or cleans the build directory."""
    print(f"Preparing build directory: {BUILD_DIR}")
    if os.path.exists(BUILD_DIR):
        print("Build directory exists, cleaning it...")
        try:
            shutil.rmtree(BUILD_DIR)
        except PermissionError:
            print(f"ERROR: Permission denied to remove {BUILD_DIR}. Please close any programs using it and try again.")
            sys.exit(1)
    os.makedirs(BUILD_DIR, exist_ok=True)
    os.makedirs(PYINSTALLER_WORK_DIR, exist_ok=True)
    print("Build directory prepared.")

def copy_and_prepare_sources():
    """Copies source files to build directory and renames/patches them."""
    print("Copying and preparing source files...")

    # 1. Copy bot script
    src_bot_path = os.path.join(SCRIPT_DIR, ORIGINAL_BOT_SCRIPT_NAME)
    dest_bot_path = os.path.join(BUILD_DIR, BOT_MODULE_NAME_IN_BUILD)
    if not os.path.exists(src_bot_path):
        print(f"ERROR: Bot script '{ORIGINAL_BOT_SCRIPT_NAME}' not found in '{SCRIPT_DIR}'.")
        sys.exit(1)
    shutil.copy2(src_bot_path, dest_bot_path)
    print(f"Copied '{ORIGINAL_BOT_SCRIPT_NAME}' to '{dest_bot_path}'")

    # 2. Copy and patch GUI script
    src_gui_path = os.path.join(SCRIPT_DIR, ORIGINAL_GUI_SCRIPT_NAME)
    dest_gui_path = os.path.join(BUILD_DIR, GUI_APP_NAME_IN_BUILD)
    if not os.path.exists(src_gui_path):
        print(f"ERROR: GUI script '{ORIGINAL_GUI_SCRIPT_NAME}' not found in '{SCRIPT_DIR}'.")
        sys.exit(1)
    
    with open(src_gui_path, 'r', encoding='utf-8') as f_in:
        content = f_in.read()
    
    # Patch the import statement
    # Original: from testmain import main
    # Patched:  from fo76_bot_module import main (using BOT_MODULE_NAME_IN_BUILD without .py)
    module_to_import_from = BOT_MODULE_NAME_IN_BUILD.replace(".py", "")
    patched_content = content.replace("from testmain import main", f"from {module_to_import_from} import main")
    
    if patched_content == content:
        print(f"WARNING: Could not find 'from testmain import main' in '{ORIGINAL_GUI_SCRIPT_NAME}'. "
              f"The import might already be correct or the pattern changed.")

    with open(dest_gui_path, 'w', encoding='utf-8') as f_out:
        f_out.write(patched_content)
    print(f"Copied and patched '{ORIGINAL_GUI_SCRIPT_NAME}' to '{dest_gui_path}'")

    # 3. Copy custom modules
    for module_file in CUSTOM_MODULE_FILES:
        src_module_path = os.path.join(SCRIPT_DIR, module_file)
        dest_module_path = os.path.join(BUILD_DIR, module_file)
        if not os.path.exists(src_module_path):
            print(f"ERROR: Custom module '{module_file}' not found in '{SCRIPT_DIR}'.")
            sys.exit(1)
        shutil.copy2(src_module_path, dest_module_path)
        print(f"Copied custom module '{module_file}' to '{dest_module_path}'")
    
    print("Source files copied and prepared.")

def run_pyinstaller(pyinstaller_path):
    """Constructs and runs the PyInstaller command."""
    print("Running PyInstaller...")
    
    entry_script_path = os.path.join(BUILD_DIR, GUI_APP_NAME_IN_BUILD)

    # PyInstaller command arguments
    # Using --onedir for better compatibility with data files and multiprocessing
    # Use --windowed to prevent console from showing for the GUI app
    cmd = [
        pyinstaller_path,
        "--noconfirm",      # Overwrite output directory without asking
        "--onedir",         # Create a directory bundle (recommended)
        # "--onefile",      # Alternative: create a single executable file
        "--windowed",       # For GUI applications, no console window
        "--name", OUTPUT_EXE_NAME,
        "--distpath", DIST_DIR,
        "--workpath", PYINSTALLER_WORK_DIR,
        "--specpath", PYINSTALLER_SPEC_DIR,
        "--log-level=WARN", # Reduce console output
    ]

    # Add data files (e.g., icons folder)
    for src_name, dest_name_in_bundle in DATA_TO_BUNDLE:
        src_path_on_disk = os.path.join(os.path.dirname(SCRIPT_DIR), src_name)
        if not os.path.exists(src_path_on_disk):
            print(f"ERROR: Data item '{src_name}' not found at '{src_path_on_disk}'.")
            sys.exit(1)
        cmd.append(f"--add-data={src_path_on_disk}{os.pathsep}{dest_name_in_bundle}")
        print(f"Adding data: '{src_path_on_disk}' as '{dest_name_in_bundle}' in bundle.")

    # Add hidden imports if necessary (pynput sometimes needs this)
    # Common ones for pynput, though often auto-detected. Add if you get import errors.
    # cmd.append("--hidden-import=pynput.keyboard._win32")
    # cmd.append("--hidden-import=pynput.mouse._win32")
    # cmd.append("--hidden-import=pynput.keyboard") # If using older pynput
    
    # Exclude heavy unnecessary modules - only include what's actually needed:
    # Required: pytesseract, cv2, numpy, PIL, pyautogui, pynput, psutil, requests, cryptography, win32 libs
    unnecessary_modules = [
        "torch", "tensorflow", "matplotlib", "pandas", "scipy", "IPython", 
        "notebook", "sklearn", "xformers", "triton", "sympy", "numba",
        "jax", "jaxlib", "keras", "seaborn", "plotly", "bokeh", "dash",
        "statsmodels", "networkx", "nltk", "spacy", "gensim",
        "jupyter", "ipykernel", "ipywidgets", "pytest", "sphinx",
        "black", "pylint", "mypy", "flake8", "coverage"
    ]
    for module in unnecessary_modules:
        cmd.append(f"--exclude-module={module}")

    cmd.append(entry_script_path) # The main script for PyInstaller to process

    print("\nPyInstaller command to be executed:")
    print(" ".join(f'"{arg}"' if " " in arg else arg for arg in cmd)) # Print user-friendly command
    
    try:
        # It's often better to run PyInstaller from the directory containing the .spec file
        # or the main script, but with full paths, it should be fine.
        # For simplicity, run from SCRIPT_DIR.
        # Use subprocess.run instead of Popen to show real-time output
        result = subprocess.run(cmd, cwd=SCRIPT_DIR)

        if result.returncode == 0:
            print("\nPyInstaller completed successfully!")
            print(f"Output executable and associated files are in: {os.path.join(DIST_DIR, OUTPUT_EXE_NAME)}")
        else:
            print("\nERROR: PyInstaller failed.")
            sys.exit(1)
            
    except FileNotFoundError:
        print(f"ERROR: PyInstaller command '{pyinstaller_path}' not found. Is it in your PATH?")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred while running PyInstaller: {e}")
        sys.exit(1)

def cleanup_build_files(full_cleanup=False):
    """Cleans up temporary build files."""
    print("Cleaning up build files...")
    if os.path.exists(PYINSTALLER_WORK_DIR):
        shutil.rmtree(PYINSTALLER_WORK_DIR)
        print(f"Removed PyInstaller work directory: {PYINSTALLER_WORK_DIR}")
    
    spec_file = os.path.join(PYINSTALLER_SPEC_DIR, f"{OUTPUT_EXE_NAME}.spec")
    if os.path.exists(spec_file):
        os.remove(spec_file)
        print(f"Removed .spec file: {spec_file}")

    if full_cleanup and os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)
        print(f"Removed main build directory: {BUILD_DIR}")
    elif not full_cleanup:
        print(f"Build directory '{BUILD_DIR}' (containing prepared sources) was not removed. "
              "Delete it manually if not needed.")

# --- Main Compilation Script ---
if __name__ == "__main__":
    print("--- Fallout 76 Bot Compiler Script ---")
    
    pyinstaller_exe_path = check_pyinstaller() # Call the function to get the path
    prepare_build_directory()
    copy_and_prepare_sources()
    run_pyinstaller(pyinstaller_exe_path)    # Use the path returned by the function
    
    # Set full_cleanup=True if you want to remove the entire BUILD_DIR
    # Keeping it (full_cleanup=False) can be useful for debugging .spec files or prepared sources.
    cleanup_build_files(full_cleanup=True) 
    
    print("\n--- Compilation process finished. ---")
    print(f"The bundled application should be in: {os.path.join(DIST_DIR, OUTPUT_EXE_NAME)}")
    print("Remember: Tesseract OCR must be installed separately on the target machine.")