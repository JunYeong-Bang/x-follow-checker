@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [INFO] .venv not found. creating virtual environment...
  py -m venv .venv
)

echo [INFO] Installing/updating build dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
".venv\Scripts\python.exe" -m pip install -r requirements.txt pyinstaller

echo [INFO] Building XFollowChecker.exe ...
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed --name XFollowChecker gui_app.py

echo.
echo [DONE] Build complete.
echo [DONE] Executable: dist\XFollowChecker.exe
echo.
pause
