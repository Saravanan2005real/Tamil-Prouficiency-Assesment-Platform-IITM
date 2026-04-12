@echo off
REM Gunicorn doesn't work on Windows (requires fcntl module)
REM Use this only in WSL (Windows Subsystem for Linux) or Linux
REM For Windows, use START_WAITRESS.bat instead
echo.
echo WARNING: Gunicorn doesn't work on Windows!
echo Use START_WAITRESS.bat for Windows, or use WSL for Gunicorn
echo.
echo If you're in WSL/Linux, run:
echo   gunicorn app:app -w 4 --bind 0.0.0.0:5000 --timeout 120
echo.
pause
