@echo off
setlocal
cd /d "%~dp0"
chcp 65001 > nul
title Taiwan Stock Technical Analysis - TW Stock Pro

echo ========================================================
echo   [TW Stock Pro] Taiwan Stock Technical Analysis System
echo   Checking environment and starting local server...
echo ========================================================
echo.

:: 1. Detect Python Executable
set PYTHON_EXEC=

if exist ".venv\Scripts\python.exe" (
    set PYTHON_EXEC=.venv\Scripts\python.exe
    goto FOUND_PYTHON
)
if exist "venv\Scripts\python.exe" (
    set PYTHON_EXEC=venv\Scripts\python.exe
    goto FOUND_PYTHON
)

python -c "import sys" >nul 2>&1
if not errorlevel 1 (
    set PYTHON_EXEC=python
    goto FOUND_PYTHON
)

py -c "import sys" >nul 2>&1
if not errorlevel 1 (
    set PYTHON_EXEC=py
    goto FOUND_PYTHON
)

if exist "C:\Python314\python.exe" (
    set PYTHON_EXEC=C:\Python314\python.exe
    goto FOUND_PYTHON
)
if exist "C:\Python313\python.exe" (
    set PYTHON_EXEC=C:\Python313\python.exe
    goto FOUND_PYTHON
)
if exist "C:\Python312\python.exe" (
    set PYTHON_EXEC=C:\Python312\python.exe
    goto FOUND_PYTHON
)
if exist "C:\Python311\python.exe" (
    set PYTHON_EXEC=C:\Python311\python.exe
    goto FOUND_PYTHON
)

echo [ERROR] Python environment not found!
echo Please ensure Python 3.9+ is installed and "Add Python to PATH" is checked.
echo Download URL: https://www.python.org/downloads/
echo.
pause
exit /b 1

:FOUND_PYTHON
echo [OK] Using Python: %PYTHON_EXEC%
echo.

:: 2. Check dependencies
echo [*] Checking dependencies (FastAPI, Uvicorn, Pandas, Requests)...
%PYTHON_EXEC% -c "import fastapi, uvicorn, pandas, requests" >nul 2>&1
if errorlevel 1 (
    echo [!] Installing missing dependencies from requirements.txt...
    echo Please wait, this only happens on initial launch...
    echo.
    %PYTHON_EXEC% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [ERROR] Failed to install packages! Please check your internet connection.
        echo.
        pause
        exit /b 1
    )
    echo [OK] Dependencies installed successfully!
    echo.
)

:: 3. Launch main server
echo [OK] Launching application server...
echo.

%PYTHON_EXEC% main.py

if errorlevel 1 (
    echo.
    echo [!] Server exited with error. If port 8000 is occupied, please check running processes.
    echo.
    pause
)
