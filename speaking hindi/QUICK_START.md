# 🚀 Quick Start Guide - Hindi Speaking Skill Assessment

## Prerequisites
- Python 3.9+ installed
- All dependencies installed (`pip install -r backend/requirements.txt`)
- Ollama installed and running (for relevance checking)

---

## Step-by-Step Instructions

### Step 1: Start the Backend Server

1. **Open PowerShell or Command Prompt**

2. **Navigate to the backend directory:**
   ```powershell
   cd "C:\Users\Saravanan\Desktop\speaking skill\backend"
   ```

3. **Start the FastAPI server:**
   ```powershell
   python -m uvicorn main:app --reload --port 8000 --host 127.0.0.1
   ```

4. **Wait for the server to start** - You should see:
   ```
   INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
   INFO:     Started reloader process
   INFO:     Started server process
   INFO:     Waiting for application startup.
   INFO:     Application startup complete.
   ```

5. **Verify the server is running:**
   - Open browser and go to: http://127.0.0.1:8000/health
   - You should see: `{"status":"ok"}`
   - Or check API docs: http://127.0.0.1:8000/docs

### Step 2: Open the Frontend

**Option A: Direct File Opening (Easiest)**
1. Navigate to: `C:\Users\Saravanan\Desktop\speaking skill\`
2. Double-click `index.html`
3. It will open in your default browser

**Option B: Using VS Code Live Server**
1. Install "Live Server" extension in VS Code
2. Right-click on `index.html`
3. Select "Open with Live Server"

**Option C: Using Python HTTP Server**
1. Open a new PowerShell/Command Prompt window
2. Navigate to project root:
   ```powershell
   cd "C:\Users\Saravanan\Desktop\speaking skill"
   ```
3. Run:
   ```powershell
   python -m http.server 8080
   ```
4. Open browser: http://localhost:8080

### Step 3: Use the Application

1. **Click "Start Assessment"** button
2. **Read the question** (in Hindi)
3. **Click "Start Recording"** when ready
4. **Speak your answer in Hindi:**
   - Minimum 10 words
   - Minimum 20 seconds duration
   - Answer should be relevant to the question (>= 30% relevance)
5. **Click "Stop Recording"** when done
6. **Wait for processing** - Results will show automatically
7. **View results:**
   - If relevance < 30%: Shows "FAIL" message
   - If relevance >= 30%: Shows percentages for:
     - Fluency
     - Pronunciation
     - Confidence
     - Coherence
     - Lexical Richness
     - Overall Score
8. **Click "Next Question"** to continue (if not the last question)

---

## Troubleshooting

### ❌ Error: "Could not import module 'main'"
**Solution:** Make sure you're in the `backend` directory:
```powershell
cd backend
python -m uvicorn main:app --reload --port 8000 --host 127.0.0.1
```

### ❌ Error: "ModuleNotFoundError"
**Solution:** Install dependencies:
```powershell
cd backend
pip install -r requirements.txt
```

### ❌ Error: "Ollama server not reachable"
**Solution:** 
1. Install Ollama from https://ollama.ai
2. Start Ollama service
3. Pull the model: `ollama pull llama3.2` (or your preferred model)

### ❌ Error: "ffmpeg not found"
**Solution:**
```powershell
pip install imageio-ffmpeg
```

### ❌ Backend not responding
**Solution:**
1. Check if port 8000 is already in use
2. Kill the process using port 8000:
   ```powershell
   netstat -ano | findstr :8000
   taskkill /PID <PID> /F
   ```
3. Restart the server

---

## Project Structure

```
speaking skill/
├── backend/              # Backend API (FastAPI)
│   ├── main.py          # Main application file
│   ├── requirements.txt # Python dependencies
│   └── evaluators/      # Evaluation modules
├── index.html           # Frontend HTML
├── app.js              # Frontend JavaScript
└── style.css           # Frontend styles
```

---

## Important Notes

✅ **Minimum Requirements:**
- 10 words minimum
- 20 seconds duration minimum

✅ **FAIL Condition:**
- Only if relevance < 30%
- Other factors (fluency, pronunciation, etc.) only affect percentages, not pass/fail

✅ **Language:**
- Hindi for questions and answers
- English for reading rules only

---

## Quick Commands Reference

### Start Backend:
```powershell
cd backend
python -m uvicorn main:app --reload --port 8000 --host 127.0.0.1
```

### Check Backend Health:
```powershell
curl http://127.0.0.1:8000/health
```

### View API Documentation:
Open in browser: http://127.0.0.1:8000/docs

---

## Need Help?

- Check `HOW_TO_RUN.md` for detailed instructions
- Check `PROJECT_WORKFLOW.md` for technical details
- Check API docs at http://127.0.0.1:8000/docs

