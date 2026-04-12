@echo off
echo Starting Tamil Reading Assessment Website...
echo.
echo Installing dependencies (if needed)...
pip install -r requirements.txt
echo.
echo Starting Flask server...
echo Open your browser and go to: http://localhost:5000
echo.
python app.py
pause
