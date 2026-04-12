@echo off
REM Hypercorn is a Windows-compatible ASGI server with worker support
REM Install with: pip install hypercorn
cd backend
hypercorn main:app --bind 0.0.0.0:8001 --workers 4 --read-timeout 120
pause
