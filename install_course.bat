@echo off
chcp 65001 >nul

echo.
echo ============================================
echo   Python Course -- Environment Setup
echo   (Voila)
echo ============================================
echo.

:: --------------------------------------------
:: 1) Check Python
:: --------------------------------------------

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo Install Python 3.10+ and check "Add to PATH"
    pause
    exit /b 1
)

echo [1/5] Python found:
python --version
echo.

:: --------------------------------------------
:: 2) Create virtual environment
:: --------------------------------------------

if exist .venv (
    echo [2/5] .venv already exists, skipping...
) else (
    echo [2/5] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Could not create .venv
        pause
        exit /b 1
    )
    echo        OK
)
echo.

:: --------------------------------------------
:: 3) Upgrade pip
:: --------------------------------------------

echo [3/5] Upgrading pip...
.venv\Scripts\python.exe -m pip install --upgrade pip >nul
echo        OK
echo.

:: --------------------------------------------
:: 4) Install packages
:: --------------------------------------------

echo [4/5] Installing requirements (1-2 min)...
.venv\Scripts\pip.exe install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Package installation failed
    pause
    exit /b 1
)
echo        OK
echo.

:: --------------------------------------------
:: 5) Register kernel
:: --------------------------------------------

echo [5/5] Registering kernel...
.venv\Scripts\python.exe -m ipykernel install --user --name python-course --display-name "Python Course"
echo        OK
echo.

echo ============================================
echo   Setup complete!
echo   Now run: start_course.bat
echo ============================================
echo.
pause
