@echo off
title SRM Library App
REM Check if server is running on 5000
netstat -ano | findstr :5000 >nul 2>&1
if errorlevel 1 (
    echo Starting SRM Library server...
    start /b "" python "%~dp0webapp\app.py"
    timeout /t 2 >nul
)

REM Open in Standalone App Window (Chrome or Edge)
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --app=http://localhost:5000 --window-size=1400,900
    exit /b
)
if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    start "" "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" --app=http://localhost:5000 --window-size=1400,900
    exit /b
)
if exist "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" (
    start "" "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --app=http://localhost:5000 --window-size=1400,900
    exit /b
)

REM Fallback
start "" http://localhost:5000
