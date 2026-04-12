# Quick Start Guide

## Common Issue: "Failed to fetch" Error

If you see "Failed to fetch" or "Error: Failed to connect to server", it means the Flask backend server is not running.

## Solution:

1. **Open a terminal/command prompt** in the project directory

2. **Install dependencies** (if not already installed):
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the Flask server**:
   ```bash
   python app.py
   ```

   You should see output like:
   ```
   * Running on http://127.0.0.1:5000
   * Running on http://0.0.0.0:5000
   ```

4. **Keep the terminal open** - the server must keep running!

5. **Open your browser** and go to:
   ```
   http://localhost:5000
   ```

6. **If you still get errors**, check:
   - Is the server running? (Check the terminal)
   - Are you accessing the correct URL? (http://localhost:5000)
   - Are there any error messages in the terminal?

## Windows Users:

You can also double-click `run.bat` to start the server automatically.

## Troubleshooting:

- **Port 5000 already in use?** 
  - Change the port in `app.py` (last line): `app.run(debug=True, host='0.0.0.0', port=5001)`
  - Then access: `http://localhost:5001`

- **Module not found errors?**
  - Make sure all dependencies are installed: `pip install -r requirements.txt`

- **Model loading takes time?**
  - First evaluation may take 1-2 minutes to download the AI model
  - This is normal and only happens once

