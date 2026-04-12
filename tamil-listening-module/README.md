# Tamil Listening Proficiency Test

A comprehensive web application for testing Tamil listening proficiency across 3 levels with AI-powered evaluation.

## Features

### Level 1 - Beginner (Primary classes Audio)
- **Fill the missing word** (1 word)
- **Identify main topic** (1-2 words)
- **Word/number spotting**
- **Order 2 events**

### Level 2 - Intermediate (3-4 person interaction)
- **Identify the speaker** (1-2 words)
- **Dialogue ordering** (3 lines)
- **Identify main action** (1-3 words)
- **Find WHO decided something**
- **Match sentence to speaker**

**Note:** The evaluation module implements logic for 6 question types. The current prototype displays 4 question types in the UI (identify speaker, dialogue ordering, main action, and match speaker role). The remaining evaluation strategies (who decided, match sentence to speaker, and generic short answer) are designed for future use.

### Level 3 - Advanced (Movie scenes, YouTube vlog clips)
- **Emotion MCQ**
- **Identify conversation topic** (2-3 words)
- **Dialogue ending identification**
- **Order events** (3-4 actions)
- **Fill missing phrase** (1-2 words)

## Evaluation Methods

### Rule-Based NLP
- Text preprocessing (lowercasing, punctuation removal)
- Exact matching (for numbers, missing words)
- Keyword matching (for main topics)
- Sequence matching (for ordering events)

### ML/DL Components
- **Sentence Embedding Model (MiniLM)**: Used for semantic similarity when meaning matters
- **ML Answer Correctness Classifier**: Uses similarity + features to predict correct/incorrect answers

## How to Run

### Quick Start (Using Batch Files)

1. **Start Backend Server:**
   - Double-click `START_BACKEND.bat`
   - Or run: `cd Backend && python app.py`
   - Backend runs on: `http://127.0.0.1:5000`

2. **Start Frontend Server:**
   - Double-click `START_FRONTEND.bat`
   - Or run: `python -m http.server 8000`
   - Frontend runs on: `http://localhost:8000`

3. **Open in Browser:**
   ```
   http://localhost:8000
   ```
   ⚠️ **IMPORTANT:** Always use `http://localhost:8000` (not file://)

4. **Verify Connection:**
   - Check "Backend Status" section at bottom of page
   - Should show: `✅ API working` (green)

5. **Start Test:**
   - Click "Start Test" button for Level 1
   - Audio and questions will load automatically
   - Answer questions and submit

### Manual Setup

1. **Start Backend:**
   ```bash
   cd Backend
   python app.py
   ```

2. **Start Frontend (in new terminal):**
   ```bash
   python -m http.server 8000
   ```

3. **Open:** `http://localhost:8000`

## Requirements

- Python 3.x (for local server)
- Modern web browser (Chrome, Firefox, Edge)
- Internet connection (for loading MiniLM model from CDN)

## Notes

- The MiniLM model loads from CDN for semantic similarity evaluation
- If the model fails to load, the system falls back to rule-based evaluation only
- Audio files are processed locally in the browser (no server upload required)
- Each level has specific question types as outlined above

## Prototype Status

This is a prototype version where:
- Each level has 1 audio file
- One question of each type is included per level
- Evaluation uses both rule-based and ML methods