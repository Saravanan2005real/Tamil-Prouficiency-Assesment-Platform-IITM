# How to Run the Hindi Speaking Skill Assessment Project

This guide will help you run both the backend and frontend of the project.

---

## 📋 Prerequisites

Before running the project, make sure you have:

1. **Python 3.8+** installed
2. **Node.js** (optional, only if using a local server for frontend)
3. **FFmpeg** (for audio processing) - Usually installed automatically via `imageio-ffmpeg`
4. **Ollama** (for relevance checking) - Download from https://ollama.ai

---

## 🔧 Step 1: Install Backend Dependencies

1. Open a terminal/command prompt
2. Navigate to the backend directory:
   ```bash
   cd "C:\Users\Saravanan\Desktop\speaking skill\backend"
   ```

3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

   This will install:
   - FastAPI
   - Uvicorn
   - Whisper (OpenAI)
   - NumPy
   - And other required packages

---

## 🤖 Step 2: Set Up Ollama (for Relevance Checking)

1. **Download and Install Ollama:**
   - Visit: https://ollama.ai
   - Download and install Ollama for Windows

2. **Pull the required model:**
   ```bash
   ollama pull mistral
   ```
   (or use any other model you prefer)

3. **Start Ollama:**
   - Ollama should start automatically after installation
   - Or run: `ollama serve`
   - Default URL: http://localhost:11434

4. **Verify Ollama is running:**
   ```bash
   curl http://localhost:11434/api/tags
   ```

---

## ⚙️ Step 3: Configure Backend (Optional)

1. **Create `.env` file** (if needed):
   ```bash
   cd backend
   copy env.example .env
   ```

2. **Edit `.env`** (if you want to change defaults):
   ```
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=mistral
   WHISPER_MODEL=base
   ```

---

## 🚀 Step 4: Start the Backend Server

1. **Open a terminal/command prompt**

2. **Navigate to backend directory:**
   ```bash
   cd "C:\Users\Saravanan\Desktop\speaking skill\backend"
   ```

3. **Start the FastAPI server:**
   ```bash
   python -m uvicorn main:app --reload --port 8000 --host 127.0.0.1
   ```

   **Alternative (PowerShell):**
   ```powershell
   cd "C:\Users\Saravanan\Desktop\speaking skill\backend"
   python -m uvicorn main:app --reload --port 8000 --host 127.0.0.1
   ```

4. **Verify backend is running:**
   - You should see: `Uvicorn running on http://127.0.0.1:8000`
   - Open browser: http://127.0.0.1:8000/health
   - Should return: `{"status":"ok"}`

5. **API Documentation:**
   - Visit: http://127.0.0.1:8000/docs
   - This shows all available API endpoints

---

## 🌐 Step 5: Open the Frontend

You have **two options** to run the frontend:

### **Option A: Direct File Opening (Simplest)**

1. **Navigate to project folder:**
   ```
   C:\Users\Saravanan\Desktop\speaking skill\
   ```

2. **Open `index.html`** in your browser:
   - Right-click `index.html`
   - Select "Open with" → Choose your browser (Chrome, Edge, Firefox)

### **Option B: Local HTTP Server (Recommended)**

1. **Open a NEW terminal/command prompt** (keep backend running in the first one)

2. **Navigate to project root:**
   ```bash
   cd "C:\Users\Saravanan\Desktop\speaking skill"
   ```

3. **Start a simple HTTP server:**
   
   **Using Python:**
   ```bash
   python -m http.server 8080
   ```
   
   **Or using Node.js (if installed):**
   ```bash
   npx http-server -p 8080
   ```

4. **Open in browser:**
   - Visit: http://localhost:8080
   - Or: http://127.0.0.1:8080

---

## ✅ Step 6: Test the Application

1. **Frontend should load:**
   - You'll see the Rules/Instructions page
   - Click "Start Test" button

2. **Test Flow:**
   - Question 1 will be spoken by the avatar
   - Click "Start Mic" to record your answer
   - Speak in Hindi
   - Click "Stop Mic" when done
   - Wait for processing (backend evaluation)
   - See results with all factor percentages
   - Click "Next Question" to continue

3. **Complete all 3 questions:**
   - After Question 3, you'll see the final results page

---

## 🔍 Troubleshooting

### **Backend Issues:**

**Problem: Port 8000 already in use**
```bash
# Use a different port
python -m uvicorn main:app --reload --port 8001 --host 127.0.0.1
```

**Problem: FFmpeg not found**
```bash
# Install imageio-ffmpeg
pip install imageio-ffmpeg
```

**Problem: Whisper model not found**
```bash
# Whisper will download models automatically on first use
# Make sure you have internet connection
```

**Problem: Ollama connection error**
- Make sure Ollama is running: `ollama serve`
- Check if model is pulled: `ollama list`
- If Ollama fails, the system will use fallback relevance checking

### **Frontend Issues:**

**Problem: CORS errors**
- Make sure backend is running on http://127.0.0.1:8000
- Check `app.js` has correct `API_BASE_URL`

**Problem: Microphone not working**
- Allow microphone permissions in browser
- Check browser console for errors
- Try a different browser (Chrome recommended)

**Problem: Audio recording fails**
- Make sure you're using HTTPS or localhost (not file://)
- Use Option B (HTTP server) instead of direct file opening

---

## 📊 Project Structure

```
speaking skill/
├── backend/
│   ├── main.py              # FastAPI server
│   ├── audio_utils.py       # Audio feature extraction
│   ├── evaluators/          # Evaluation modules
│   │   ├── fluency.py
│   │   ├── pronunciation.py
│   │   ├── confidence.py
│   │   ├── lexical.py
│   │   └── coherence.py
│   ├── relevance.py         # Relevance checking
│   ├── aggregate.py         # Score aggregation
│   ├── hi_config.json       # Hindi phrases config
│   └── requirements.txt     # Python dependencies
├── index.html               # Frontend HTML
├── app.js                   # Frontend JavaScript
├── style.css                # Frontend CSS
└── HOW_TO_RUN.md           # This file
```

---

## 🎯 Quick Start Commands

**Terminal 1 (Backend):**
```bash
cd "C:\Users\Saravanan\Desktop\speaking skill\backend"
python -m uvicorn main:app --reload --port 8000 --host 127.0.0.1
```

**Terminal 2 (Frontend Server - Optional):**
```bash
cd "C:\Users\Saravanan\Desktop\speaking skill"
python -m http.server 8080
```

**Then open:** http://localhost:8080 (or just open `index.html` directly)

---

## 📝 Notes

- **Backend must be running** before using the frontend
- **Ollama is optional** - system will use fallback if unavailable
- **First Whisper run** may take time to download the model
- **Microphone permissions** are required for recording
- **Use Chrome/Edge** for best compatibility

---

## 🆘 Need Help?

- Check backend logs in the terminal running uvicorn
- Check browser console (F12) for frontend errors
- Verify all services are running:
  - Backend: http://127.0.0.1:8000/health
  - Ollama: http://localhost:11434/api/tags

---

**Happy Testing! 🎤**

