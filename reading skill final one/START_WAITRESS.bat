@echo off
REM Waitress is a Windows-compatible WSGI server for Flask
REM Install with: pip install waitress
echo Starting Tamil Reading Assessment Website with Waitress...
echo.
echo Installing dependencies (if needed)...
pip install -r requirements.txt
pip install waitress
echo.
echo Starting Waitress server...
echo Open your browser and go to: http://localhost:5000
echo.
cd /d "%~dp0"
waitress-serve --host=0.0.0.0 --port=5000 --threads=4 app:app
pause
