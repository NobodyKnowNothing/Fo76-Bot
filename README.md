# Fo76Bot

A Python-based event automation bot for Fallout 76.

## Features

-   **Automated Event Farming**: Detects and joins public events.
-   **Game Management**: Can close and relaunch the game on a crash.

## Disclaimer

This bot interacts with the game client and will violate the terms of service of Fallout 76. Use at your own risk. I am not responsible for any consequences that may arise from using this bot. 

## Developer Disclaimer

The bot is spaghetti code. I am a student, and this was my first large project. I am also a chronic contrarian and hate best practices. 

It does work. If you want new features, fork and make them yourself, I will merge if I approve. I will not be adding new features. 

I hate this project now and fuck Bethesda for taking down my patreon and not making better games so this project is one giant middle finger to Bethesda.

## Requirements

-   Windows 10/11
-   Python 3.x
-   Tesseract OCR (Installed and added to PATH or configured in UI)
-   Fallout 76 (Steam or Game Pass)

## Installation

1.  Clone this repository.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Ensure Tesseract OCR is installed.

## Usage

1.  Run the control panel:
    ```bash
    python src/ui.py
    ```
2.  **Configuration**:
    -   Select your `Fallout76.exe` path.
    -   Select your `tesseract.exe` path.
    -   Select your `Fallout76Prefs.ini` file.
3.  Click **Start Bot**.
4.  Press **F5** to stop the bot.

## Project Structure

-   `src/ui.py`: Main entry point and configuration UI. The most readable code because AI wrote most of it.
-   `src/testmain.py`: Core bot logic, its highly redundant and unoptimized.
-   `src/press.py`, `input.py`: Input simulation helpers that do the same thing lol you refactor it.
-   `src/readtext.py`: OCR helpers.

