# How to Run the Integrated Tamil Writing Evaluation System

## Prerequisites

1. **Python 3.7+** installed on your system
2. **Ollama** installed and running (for content relevance checking)
   - Download from: https://ollama.ai
   - Pull the required model: `ollama pull llama3.2`
3. **Required files:**
   - `cleaned_tamil_lexicon.txt` (Tamil dictionary file)
   - `tamil_spell_checker.py`
   - `tamil_vocabulary_detector.py`
   - `app.py`
   - `templates/` folder with HTML templates

## Step 1: Install Dependencies

Open terminal/command prompt in the project directory and run:

```bash
pip install -r requirements.txt
```

Or install manually:

```bash
pip install Flask==3.0.0 Werkzeug==3.0.1 requests==2.31.0
```

## Step 2: Start Ollama (for Content Relevance Checking)

Make sure Ollama is running:

```bash
# On Windows (if installed as service, it should auto-start)
# Or start manually:
ollama serve

# Verify Ollama is running:
ollama list
```

Pull the required model if not already done:

```bash
ollama pull llama3.2
```

## Step 3: Run the Flask Application

Navigate to the project directory and run:

```bash
python app.py
```

Or:

```bash
python -m flask run
```

## Step 4: Access the Application

Open your web browser and go to:

```
http://localhost:5000
```

Or:

```
http://127.0.0.1:5000
```

## Expected Output

When you run `python app.py`, you should see:

```
INFO:__main__:Checking Ollama connection at http://localhost:11434...
INFO:__main__:Ollama is available and connected!
INFO:__main__:Spell checker and vocabulary detector initialized successfully
INFO:__main__:All evaluators initialized successfully!
 * Running on http://0.0.0.0:5000
 * Running on http://127.0.0.1:5000
```

## Troubleshooting

### If Ollama is not running:
- The app will still work but content relevance checking will fail
- You'll see: `WARNING: Ollama initialization failed. Relevance checking will not work.`

### If dictionary file is missing:
- Make sure `cleaned_tamil_lexicon.txt` is in the same directory as `app.py`
- The spell checker will fail to initialize

### If port 5000 is already in use:
- Change the port in `app.py` (line 646): `app.run(debug=True, host='0.0.0.0', port=5001)`

## API Endpoint

You can also test the evaluation via API:

```bash
curl -X POST http://localhost:5000/api/evaluate \
  -H "Content-Type: application/json" \
  -d '{"answer": "நான் தினமும் காலை நேரத்தில் நடைபயிற்சி செய்கிறேன்", "level": 1}'
```

## Environment Variables (Optional)

You can set custom Ollama configuration:

```bash
# Windows PowerShell
$env:OLLAMA_BASE_URL="http://localhost:11434"
$env:OLLAMA_MODEL="llama3.2"

# Windows CMD
set OLLAMA_BASE_URL=http://localhost:11434
set OLLAMA_MODEL=llama3.2

# Linux/Mac
export OLLAMA_BASE_URL=http://localhost:11434
export OLLAMA_MODEL=llama3.2
```

## Quick Start Command

```bash
# 1. Install dependencies
pip install Flask Werkzeug requests

# 2. Start Ollama (in separate terminal)
ollama serve

# 3. Run the app
python app.py
```

Then open: **http://localhost:5000**

