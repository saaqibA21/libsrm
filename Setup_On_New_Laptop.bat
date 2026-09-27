@echo off
title SRM EEE Library System - First Time Setup
color 0A
echo =======================================================
echo     SRM EEE Library Management System - Setup
echo =======================================================
echo.
echo Step 1: Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] Python is not installed or not in your PATH!
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo ** IMPORTANT: Check the box "Add python.exe to PATH" during installation! **
    echo.
    pause
    exit /b
)

echo Python is found!
python --version
echo.

echo Step 2: Installing required packages...
pip install -r "%~dp0requirements.txt"
if errorlevel 1 (
    echo.
    echo [WARNING] Encountered an issue installing packages. Retrying with python -m pip...
    python -m pip install flask openpyxl python-barcode Pillow reportlab xlrd
)

echo.
echo =======================================================
echo  Setup Completed Successfully!
echo  Starting the Library Website now...
echo =======================================================
echo.
timeout /t 3 >nul
start "" "%~dp0Start Library Website.bat"
