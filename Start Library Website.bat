@echo off
title SRM EEE Library System
echo.
echo  =========================================
echo   SRM EEE Library Management System
echo   Starting web server...
echo  =========================================
echo.
echo  Open your browser and go to:
echo  http://localhost:5000
echo.
echo  Press Ctrl+C to stop the server.
echo.

REM Automatically open browser after 1 second
start "" http://localhost:5000

REM 1. Try system python in PATH
where python >nul 2>&1
if not errorlevel 1 (
    python "%~dp0webapp\app.py"
    goto :end
)

REM 2. Try py launcher
where py >nul 2>&1
if not errorlevel 1 (
    py "%~dp0webapp\app.py"
    goto :end
)

REM 3. Try standard local AppData installation paths
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" "%~dp0webapp\app.py"
    goto :end
)
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" "%~dp0webapp\app.py"
    goto :end
)
if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" "%~dp0webapp\app.py"
    goto :end
)

echo.
echo [ERROR] Python was not found on this computer!
echo Please run 'Setup_On_New_Laptop.bat' first, or install Python from python.org
echo.
pause

:end
