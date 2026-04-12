@echo off
REM Gunicorn doesn't work on Windows (requires fcntl module)
REM Using Uvicorn with production settings instead
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --timeout-keep-alive 120
pause
