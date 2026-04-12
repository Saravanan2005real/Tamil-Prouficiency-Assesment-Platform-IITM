@echo off
echo Starting Tamil Listening Frontend Server...
echo.
echo Frontend will be available at: http://localhost:8000
echo Make sure backend is running on http://127.0.0.1:5000
echo.
cd /d "%~dp0"
python -m http.server 8000
pause
