@echo off
REM Anime Collection Build Script
REM Universal build command for the application

setlocal enabledelayedexpansion

echo.
echo ========================================
echo   Anime Collection Build System
echo ========================================
echo.

REM Get current directory
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Check for Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python disnot found! Please install Python and add it to PATH
    pause
    exit /b 1
)

echo [OK] Python found
echo.

REM Check for PyInstaller installation
python -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing PyInstaller...
    python -m pip install pyinstaller -q
    if errorlevel 1 (
        echo [ERROR] Error installing PyInstaller
        pause
        exit /b 1
    )
    echo [OK] PyInstaller installed successfully
) else (
    echo [OK] PyInstaller already installed
)

echo.
echo [INFO] Cleaning previous builds...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del AnimeCollection.spec 2>nul
echo [OK] Cleaning completed

echo.
echo [INFO] Launching build...
echo.

REM Build with PyInstaller
pyinstaller ^
    --onefile ^
    --windowed ^
    --name=AnimeCollection ^
    --add-data="anime.kv:." ^
    --add-data="icons:icons" ^
    --hidden-import=kivy ^
    --hidden-import=pillow ^
    --hidden-import=tinydb ^
    main.py

if errorlevel 1 (
    echo.
    echo [ERROR] Error during build process!
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Build completed successfully!
echo ========================================
echo.
echo [OK] Executable : dist\AnimeCollection.exe
echo [INFO] Path: %SCRIPT_DIR%dist\AnimeCollection.exe
echo.
echo You can run the application by double-clicking on AnimeCollection.exe
echo.
pause
