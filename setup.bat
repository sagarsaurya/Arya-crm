@echo off
echo.
echo ====================================
echo   ARYA Setup — Installing packages
echo ====================================
echo.

if not exist arya-env (
    python -m venv arya-env
)

call arya-env\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt

echo.
echo ====================================
echo   Setup complete!
echo   Run: python main.py to start ARYA
echo ====================================
echo.
pause
