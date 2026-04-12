# Tamil Speaking Assessment - Setup & Run Guide

## Prerequisites

1. **Python 3.8+** installed
2. **FFmpeg** installed (or `imageio-ffmpeg` will use bundled version)
3. **Web browser** (Chrome/Edge recommended for speech recognition)

## Quick Start

### Step 1: Install Python Dependencies

Open terminal/command prompt and navigate to the project directory:

```bash
cd backend
pip install -r requirements.txt
```

This will install:
- FastAPI (web framework)
- Uvicorn (ASGI server)
- OpenAI Whisper (speech-to-text)
- PyTorch (for Whisper)
- Other required packages

### Step 2: (Optional) Configure Environment Variables

Create a `.env` file in the `backend` folder (copy from `env.example`):

```bash
cd backend
copy env.example .env
```

Edit `.env` if needed:
- `WHISPER_MODEL=base` (default, can be: tiny, base, small, medium, large)
- `OLLAMA_BASE_URL=http://localhost:11434` (if using Ollama for relevance checking)
- `OLLAMA_MODEL=mistral` (if using Ollama)

**For Better Tamil Voice (Optional):**
- **Option 1 (Free)**: gTTS is installed by default - works automatically, requires internet
- **Option 2 (Premium)**: Add `GOOGLE_TTS_API_KEY=your_key` for Google Cloud TTS (best quality)
- **Option 3 (Premium)**: Add `AZURE_TTS_KEY=your_key` and `AZURE_TTS_REGION=your_region` for Azure TTS

**Note:** The project will work with default values (gTTS for TTS), so this step is optional.

### Step 3: Start the Backend Server

**Important:** You must be in the `backend` directory when running this command!

```bash
cd backend
python -m uvicorn main:app --reload --port 8001
```

**OR** use the batch file (Windows):
- Double-click `START_BACKEND.bat` in the project root

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8001
INFO:     Application startup complete.
```

**Keep this terminal window open** - the server must be running.

### Step 4: Open the Frontend

You have two options:

#### Option A: Open HTML file directly
Simply double-click `index.html` or open it in your browser:
```
file:///C:/Users/Saravanan/Desktop/multiple/speaking%20tamil/index.html
```

#### Option B: Use a simple HTTP server (recommended)
In a **new terminal window**, navigate to the project root and run:

```bash
# Python 3
python -m http.server 8080

# Or using Node.js (if installed)
npx http-server -p 8080
```

Then open in browser: **http://localhost:8080**

## Running the Test

1. **Backend must be running** on port 8001
2. **Open `index.html`** in your browser
3. The test will start automatically (no rules page)
4. You have **10 minutes** total for all 3 levels
5. Complete or skip each level sequentially
6. View results after all 3 levels are done

## Troubleshooting

### Backend won't start
- **Error: "Module not found"** → Run `pip install -r requirements.txt` in the `backend` folder
- **Error: "Port 8001 already in use"** → Change port: `--port 8002` (and update `API_BASE_URL` in `app.js`)
- **Error: "Whisper model not found"** → First run will download the model automatically (may take time)

### Frontend can't connect to backend
- Make sure backend is running on port 8001
- Check browser console for errors (F12)
- Verify `API_BASE_URL` in `app.js` matches backend port

### Microphone not working
- Allow microphone permission when prompted
- Use Chrome or Edge browser (best support for speech recognition)
- Check browser settings → Privacy → Microphone permissions

### Audio processing errors
- Ensure FFmpeg is installed OR `imageio-ffmpeg` is installed
- Check backend terminal for error messages

### Tamil Voice Quality
- **Default**: Uses gTTS (free, requires internet) - good quality Tamil voice
- **Better Quality**: Configure Google Cloud TTS or Azure TTS in `.env` file for premium native Tamil voices
- **Browser TTS**: Falls back to browser's built-in Tamil voice if TTS API is not available
- **Install gTTS**: If you get TTS errors, run `pip install gtts` in the backend folder

## Project Structure

```
speaking tamil/
├── index.html          # Frontend HTML
├── style.css           # Frontend styles
├── app.js             # Frontend JavaScript
├── backend/
│   ├── main.py        # FastAPI server (port 8001)
│   ├── requirements.txt
│   ├── aggregate.py   # Final score calculation
│   ├── fluency.py     # Fluency analysis
│   ├── pronunciation.py
│   ├── confidence.py
│   ├── lexical.py
│   ├── coherence.py
│   └── utils.py
└── README_SETUP.md    # This file
```

## API Endpoints

- `POST /api/assess-answer` - Evaluate speaking answer
- `GET /api/health` - Check server status
- `GET /api/ffmpeg-info` - Check FFmpeg availability

## Notes

- **First run**: Whisper model will be downloaded automatically (can be large, ~150MB for "base" model)
- **Processing time**: Each answer evaluation takes 10-30 seconds (depends on audio length and CPU)
- **Browser**: Chrome/Edge recommended for best speech recognition support
- **Time limit**: 10 minutes total for all 3 levels

## Quick Commands Summary

```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Start backend (keep running)
python -m uvicorn main:app --reload --port 8001

# Open frontend (in new terminal or just open index.html)
# Option 1: Double-click index.html
# Option 2: python -m http.server 8080 (then open http://localhost:8080)
```

