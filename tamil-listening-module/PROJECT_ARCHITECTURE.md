# Tamil Listening Test Module - Complete Architecture & Technical Documentation

## 📋 Table of Contents
1. [Project Overview](#project-overview)
2. [System Architecture](#system-architecture)
3. [Frontend Components](#frontend-components)
4. [Backend Components](#backend-components)
5. [Machine Learning Models](#machine-learning-models)
6. [Evaluation System](#evaluation-system)
7. [Data Flow](#data-flow)
8. [Key Features](#key-features)

---

## 🎯 Project Overview

**Tamil Listening Test Module** is an intelligent, multi-level assessment system for evaluating Tamil language listening comprehension skills. The system uses a combination of rule-based evaluation and machine learning to assess student answers across three difficulty levels.

### Core Purpose
- Assess Tamil listening comprehension through audio-based questions
- Provide intelligent evaluation using semantic similarity and logical content checking
- Support multiple question types (MCQ, short answer, long answer, ordering, matching)
- Enable speech-to-text input for natural language responses

---

## 🏗️ System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (Browser)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  HTML/UI     │  │  JavaScript  │  │  Audio Player│     │
│  │  (index.html)│  │  (script.js) │  │  (Media API) │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ HTTP/REST API
                            │ JSON Data
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              BACKEND (Flask Server)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Flask API  │  │  Evaluator   │  │  Whisper STT │     │
│  │   (app.py)   │  │ (evaluator.py)│  │  (speech-to-│     │
│  │              │  │              │  │    text)     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│         │                  │                  │              │
│         └──────────────────┼──────────────────┘            │
│                            │                               │
│         ┌──────────────────▼──────────────────┐           │
│         │   ML Models (Sentence Transformers)  │           │
│         │   - Level 2: multilingual-MiniLM      │           │
│         │   - Level 3: multilingual-MiniLM     │           │
│         └─────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ File System
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    DATA STORAGE                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Questions   │  │    Audio      │  │  Transcripts  │     │
│  │   (JSON)     │  │   (MP3/WebM)  │  │    (JSON)     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

---

## 🖥️ Frontend Components

### 1. **HTML Structure** (`index.html`)
- **Purpose**: Main UI layout and structure
- **Key Sections**:
  - Header with timer and level navigation
  - Audio player section (left side)
  - Questions section (right side)
  - Results display area

### 2. **JavaScript Logic** (`script.js`)
- **Purpose**: Handles all frontend interactions and API communication
- **Key Functions**:

#### **Audio Management**
```javascript
- loadAudioForLevel(level)      // Loads audio file for current level
- setupAudioPlayer(audioUrl)     // Configures HTML5 audio player
```

#### **Question Rendering**
```javascript
- renderQuestions(questions)       // Dynamically creates question UI
- renderLevel1Question()          // Level 1 specific rendering
- renderLevel2Question()          // Level 2 specific rendering
- renderLevel3Question()          // Level 3 specific rendering
```

#### **Answer Collection**
```javascript
- collectAnswers()                // Gathers all user answers
- validateLevel1Answers()         // Validates Level 1 completeness
- validateLevel2Answers()         // Validates Level 2 completeness
- validateLevel3Answers()         // Validates Level 3 completeness
```

#### **Speech-to-Text (Microphone Feature)**
```javascript
- addMicrophoneButton()           // Adds mic button to textareas
- startRecording()                 // Initiates audio recording
- stopRecording()                  // Stops recording and processes
- sendAudioToWhisper()            // Sends audio to backend for transcription
```

**Recording Flow**:
1. User clicks microphone button
2. Browser requests microphone permission
3. `MediaRecorder` API captures audio
4. Audio chunks collected in `audioChunks` array
5. On stop: Creates `Blob` from chunks
6. Converts to base64 and sends to `/api/speech-to-text`
7. Receives transcribed text and inserts into textarea

#### **API Communication**
```javascript
- API_BASE_URL = "http://127.0.0.1:5000"
- fetchQuestions(level)            // GET /api/start-test/<level>
- submitAnswers(level, answers)   // POST /evaluate
```

### 3. **Styling** (`style.css`)
- Responsive design
- Tamil font support
- Level-specific styling
- Result display formatting

---

## ⚙️ Backend Components

### 1. **Flask Application** (`Backend/app.py`)

#### **Main Server Setup**
```python
app = Flask(__name__, static_folder='..', static_url_path='')
CORS(app)  # Enable Cross-Origin Resource Sharing
```

#### **Key Endpoints**

##### **`GET /api/start-test/<level>`**
- **Purpose**: Loads questions and audio info for a level
- **Returns**: JSON with questions array and audio metadata
- **Process**:
  1. Loads question JSON file (`level{level}_*.json`)
  2. Extracts audio information
  3. Returns formatted response

##### **`POST /evaluate`**
- **Purpose**: Evaluates user answers for a level
- **Request Body**:
  ```json
  {
    "level": 1|2|3,
    "responses": { ... },
    "trigger_final_evaluation": false
  }
  ```
- **Process**:
  1. Validates all questions are attempted
  2. Normalizes answers (converts to standard format)
  3. Stores raw answers in memory
  4. Calls appropriate evaluator (`evaluate_level1/2/3`)
  5. Returns evaluation results

##### **`POST /api/speech-to-text`**
- **Purpose**: Converts Tamil speech to text using Whisper
- **Request**: Base64 encoded audio or multipart form data
- **Process**:
  1. Receives audio data
  2. Decodes base64 if needed
  3. Saves to temporary file
  4. Loads Whisper model (`whisper.load_model("base")`)
  5. Transcribes with `language="ta"` (Tamil)
  6. Returns transcribed text
  7. Cleans up temporary file

##### **`GET /api/test-whisper`**
- **Purpose**: Health check for Whisper installation
- **Returns**: Status of Whisper model

#### **Answer Storage**
```python
raw_answers_store = {
    "level_1": None,
    "level_2": None,
    "level_3": None
}
```
- Currently in-memory (can be replaced with database)
- Stores normalized answers before evaluation

---

## 🤖 Machine Learning Models

### 1. **Sentence Transformers** (Semantic Similarity)

#### **Model Used**
- **Name**: `paraphrase-multilingual-MiniLM-L12-v2`
- **Provider**: Sentence Transformers (Hugging Face)
- **Purpose**: Compute semantic similarity between Tamil texts
- **Size**: ~420MB (downloads on first use)
- **Language Support**: Multilingual (includes Tamil)

#### **How It Works**
```python
# Model Loading (Lazy Loading)
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

# Text Embedding
embeddings = model.encode([text1, text2], convert_to_numpy=True)
# Returns: 384-dimensional vectors for each text

# Cosine Similarity Calculation
dot_product = np.dot(embeddings[0], embeddings[1])
norm1 = np.linalg.norm(embeddings[0])
norm2 = np.linalg.norm(embeddings[1])
similarity = dot_product / (norm1 * norm2)
# Returns: Score between -1 and 1 (typically 0 to 1 for similar texts)
```

#### **Usage in Project**
- **Level 2**: Separate model instance for Level 2 questions
- **Level 3**: Separate model instance for Level 3 questions
- **Why Separate?**: Allows different evaluation strategies per level

### 2. **OpenAI Whisper** (Speech-to-Text)

#### **Model Used**
- **Name**: `whisper-base`
- **Provider**: OpenAI
- **Purpose**: Transcribe Tamil speech to text
- **Size**: ~150MB (downloads on first use)
- **Language**: Tamil (`language="ta"`)

#### **How It Works**
```python
# Model Loading
model = whisper.load_model("base")

# Transcription
result = model.transcribe(
    audio_path,
    language="ta",        # Force Tamil language
    task="transcribe",
    verbose=False,
    fp16=False           # Use fp32 for compatibility
)

transcribed_text = result["text"].strip()
```

#### **Features**
- Automatic language detection (with Tamil override)
- Handles various audio formats (WebM, MP3, WAV, M4A)
- Returns confidence scores and timestamps
- Supports punctuation and capitalization

---

## 📊 Evaluation System

### Evaluation Architecture

```
User Answer
    │
    ▼
┌─────────────────────────────────────┐
│  1. Normalization                   │
│     - Text cleaning                  │
│     - Case normalization             │
│     - Whitespace handling           │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  2. Logical Content Checking        │
│     - Negation detection             │
│     - Hope vs Doubt detection        │
│     - Achievement vs Failure         │
│     - Semantic opposition           │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  3. Rule-Based Evaluation           │
│     - Exact match                   │
│     - Alternative matching         │
│     - Keyword matching             │
│     - Sequence matching            │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  4. ML-Based Evaluation             │
│     - Semantic similarity          │
│     - Key idea matching            │
│     - Confidence scoring           │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  5. Final Decision                  │
│     - Logical opposition override  │
│     - Score calculation             │
│     - Method tracking              │
└─────────────────────────────────────┘
```

### Level-Specific Evaluation

#### **Level 1: Beginner** (`evaluate_level1`)
- **Strategy**: Rule-based, lenient
- **Question Types**:
  - Fill-in-the-blank: Exact match (normalized)
  - MCQ: Exact match
  - Short answer: Keyword matching
- **No ML**: Pure rule-based for simplicity

#### **Level 2: Intermediate** (`evaluate_level2`)
- **Strategy**: Rule-based + Light ML
- **Question Types**:
  - MCQ (identify speaker): Exact match
  - Dialogue ordering: Sequence matching
  - Main problem (Q3): **ML semantic similarity** (threshold: 0.80)
  - Match speaker role: Pairwise matching
- **ML Usage**: Only for Q3 (main problem) with strict threshold

#### **Level 3: Advanced** (`evaluate_level3`)
- **Strategy**: Rule-based + Advanced ML + Logical Checking
- **Question Types**:
  - Short answer (Q1): **Logical checking** + ML semantic similarity
  - Fill missing phrase (Q2): Exact match (numeric)
  - Long answer (Q3): **Logical checking** + Key ideas + ML semantic similarity
  - Long answer (Q4): **Logical checking** + Key ideas + ML semantic similarity

### Logical Content Checking (New Feature)

#### **Purpose**
Detect semantically opposite answers even when word similarity is high.

#### **Detection Rules**

1. **Negation vs Positive Action**
   ```python
   Negation words: ['மாட்டார்கள்', 'இல்லை', 'செய்யாது', ...]
   Positive words: ['செய்வார்', 'செய்வார்கள்', 'முன்னேற்றம்', ...]
   
   If user_has_negation AND correct_has_positive → OPPOSITE
   ```

2. **Hope vs Doubt**
   ```python
   Hope words: ['நம்பிக்கை', 'நம்புகிறார்கள்', ...]
   Doubt words: ['நினைத்தார்கள்', 'ஏமாற்றம்', ...]
   
   If user_has_doubt AND correct_has_hope → OPPOSITE
   ```

3. **Achievement vs Failure** (Q4 specific)
   ```python
   Achievement: ['முன்னேற்றம்', 'உயர்ந்தது', 'சாதித்தார்', ...]
   Failure: ['தோல்வி', 'வீழ்ச்சி', 'இழந்தார்கள்', ...]
   
   If user_has_failure AND correct_has_achievement → OPPOSITE
   ```

#### **Priority**
Logical opposition detection **always overrides** semantic similarity:
- Even if similarity = 0.95, if logical opposition detected → **WRONG**
- Prevents false positives from ML models

### Evaluation Metrics

#### **Score Calculation**
```python
score = number of correct answers
total = total number of questions
accuracy = (score / total) * 100
```

#### **Semantic Similarity Thresholds**
- **Level 2 Q3**: ≥ 0.80 (strict)
- **Level 3 Short Answer**: ≥ 0.75-0.78 (with key concepts)
- **Level 3 Long Answer**: ≥ 0.65-0.80 (with key ideas)

#### **Key Idea Matching** (Long Answers)
- Counts exact keyword matches
- Counts semantic matches (similarity ≥ 0.7)
- Requires 2+ key ideas for Q4, 3+ for Q3

---

## 🔄 Data Flow

### Complete User Journey

```
1. USER OPENS PAGE
   └─> index.html loads
   └─> script.js initializes
   └─> Default: Level 1 selected

2. USER SELECTS LEVEL
   └─> Frontend: loadLevel(level)
   └─> GET /api/start-test/<level>
   └─> Backend: Loads questions JSON
   └─> Returns: { questions: [...], audio: {...} }
   └─> Frontend: renderQuestions(questions)
   └─> Frontend: loadAudioForLevel(level)

3. USER LISTENS TO AUDIO
   └─> HTML5 Audio Player plays MP3
   └─> User can replay as needed

4. USER ANSWERS QUESTIONS
   └─> Type text → Stored in answer state
   └─> OR Click mic → Record → Transcribe → Insert text
   └─> Drag & drop → Stored as array
   └─> Select MCQ → Stored as string

5. USER CLICKS SUBMIT
   └─> Frontend: validateAnswers()
   └─> Frontend: collectAnswers()
   └─> POST /evaluate { level, responses }
   └─> Backend: validate_level_attempts()
   └─> Backend: normalize_responses()
   └─> Backend: evaluate_level{1/2/3}()
   └─> Backend: Returns { score, total, details, ... }
   └─> Frontend: showResult(result)
   └─> User sees: Score, Correct/Wrong per question, Feedback

6. SPEECH-TO-TEXT FLOW (if mic used)
   └─> User clicks mic button
   └─> Browser: Request microphone permission
   └─> MediaRecorder: Start recording
   └─> Audio chunks collected every 1 second
   └─> User clicks mic again → Stop recording
   └─> Create Blob from chunks
   └─> Convert to base64
   └─> POST /api/speech-to-text { audio: base64 }
   └─> Backend: Save to temp file
   └─> Whisper: Transcribe (language="ta")
   └─> Backend: Return { text: "transcribed..." }
   └─> Frontend: Insert text into textarea
```

### Answer Normalization Flow

```
Frontend Format (Level 3 Example)
{
  "level3Answers": {
    "next_action": "user answer text",
    "fill_missing_phrase": "62.5",
    "long_answers": {
      "3": "long answer text",
      "4": "long answer text"
    }
  }
}
         │
         ▼
Backend Normalization
{
  "1": "user answer text",    // Q1: short answer
  "2": "62.5",                // Q2: fill missing
  "3": "long answer text",    // Q3: long answer
  "4": "long answer text"     // Q4: long answer
}
         │
         ▼
Evaluation
- Q1: Logical check → Semantic similarity → Decision
- Q2: Exact match → Numeric comparison
- Q3: Logical check → Key ideas → Semantic similarity → Decision
- Q4: Logical check → Key ideas → Semantic similarity → Decision
```

---

## ✨ Key Features

### 1. **Multi-Level Assessment**
- **Level 1**: Beginner (4 questions, rule-based)
- **Level 2**: Intermediate (4 questions, light ML)
- **Level 3**: Advanced (4 questions, advanced ML + logical checking)

### 2. **Multiple Question Types**
- **MCQ**: Multiple choice (exact match)
- **Fill-in-the-blank**: Text or numeric input
- **Short answer**: 1-2 sentences (semantic + logical)
- **Long answer**: 40-80 words (key ideas + semantic + logical)
- **Ordering**: Drag-and-drop sequence
- **Matching**: Pairwise matching

### 3. **Speech-to-Text Input**
- Microphone button on textareas
- Real-time recording with visual feedback
- Whisper model for Tamil transcription
- Automatic text insertion

### 4. **Intelligent Evaluation**
- **Rule-based**: Exact matching, keyword matching
- **ML-based**: Semantic similarity using sentence transformers
- **Logical checking**: Detects semantic opposition
- **Hybrid approach**: Combines all methods

### 5. **Tamil Language Support**
- Full Unicode support
- Tamil fonts in UI
- Tamil audio transcription
- Tamil semantic similarity

### 6. **Error Handling**
- Validation before submission
- Graceful ML model fallback
- Clear error messages
- Debug logging

---

## 📁 File Structure

```
tamil-listening-module/
├── index.html                 # Main UI
├── script.js                  # Frontend logic (4500+ lines)
├── style.css                  # Styling
├── Backend/
│   ├── app.py                 # Flask server (1200+ lines)
│   ├── evaluator.py           # Evaluation logic (2000+ lines)
│   ├── data/
│   │   └── questions/
│   │       ├── level1_classroom_tamil.json
│   │       ├── level2_dialogue_tamil.json
│   │       └── level3_scene_tamil.json
│   └── uploads/audio/         # Audio files
├── requirements.txt           # Python dependencies
└── PROJECT_ARCHITECTURE.md    # This file
```

---

## 🔧 Dependencies

### Python Backend
```txt
Flask==2.3.3              # Web framework
flask-cors==4.0.0         # CORS support
sentence-transformers==2.2.2  # ML models
scikit-learn==1.3.2       # ML utilities
numpy==1.24.3             # Numerical operations
Werkzeug==2.3.7           # WSGI utilities
openai-whisper            # Speech-to-text (install separately)
```

### Frontend
- Vanilla JavaScript (no frameworks)
- HTML5 Audio API
- MediaRecorder API
- Fetch API for HTTP requests

---

## 🚀 Running the Project

### Backend
```bash
cd Backend
python app.py
# Server runs on http://127.0.0.1:5000
```

### Frontend
```bash
# Open index.html in browser
# Or use a local server:
python -m http.server 8000
# Then open http://localhost:8000
```

### First-Time Setup
1. Install Python dependencies: `pip install -r requirements.txt`
2. Install Whisper: `pip install openai-whisper`
3. Models download automatically on first use:
   - Sentence Transformer: ~420MB
   - Whisper Base: ~150MB

---

## 🎓 Evaluation Examples

### Example 1: Logical Opposition Detection
```
User Answer: "அவர்கள் ஏதாவது நல்லது செய்ய மாட்டார்கள் என்று நினைத்தார்கள்"
           (They thought they wouldn't do anything good)

Correct Answer: "மக்கள் நல்லது செய்வார் என்ற நம்பிக்கையால் ஓட்டு போடுகிறார்கள்"
              (People vote with hope that they will do good)

Detection:
- User has: "மாட்டார்கள்" (negation) + "நினைத்தார்கள்" (doubt)
- Correct has: "செய்வார்" (positive) + "நம்பிக்கையால்" (hope)
- Result: LOGICAL OPPOSITION → WRONG (even if similarity = 0.85)
```

### Example 2: Semantic Similarity Success
```
User Answer: "பணக்காரர்கள் மேலும் பணக்காரர்கள் ஆகிறார்கள்"
           (Rich people become richer)

Correct Answer: "பணக்காரர்கள் மேலும்மேலும் பணக்காரர்"
              (Rich people keep getting richer)

Similarity: 0.92
Key Ideas Matched: 1/4
Result: CORRECT (high similarity + key idea match)
```

---

## 🔍 Debugging & Logging

### Backend Logging
- Question loading: `📝 Loaded X questions for Level Y`
- Evaluation: `[DEBUG Q{id}] Evaluating {type}`
- Logical opposition: `[OPPOSITION] LOGICAL OPPOSITION DETECTED!`
- Final result: `[Q{id}] Final result: CORRECT/WRONG`

### Frontend Console
- API calls: `📤 Sending to: /api/...`
- Recording: `🎤 Recording started`, `🛑 Recording stopped`
- Transcription: `✅ Transcription received: ...`

---

## 🎯 Future Enhancements

1. **Database Integration**: Replace in-memory storage with SQLite/PostgreSQL
2. **User Authentication**: Add login system
3. **Progress Tracking**: Store user progress across sessions
4. **Advanced Analytics**: Detailed performance metrics
5. **More Question Types**: Add more interactive question formats
6. **Offline Support**: Service workers for offline functionality

---

## 📝 Summary

This Tamil Listening Test Module is a sophisticated, ML-powered assessment system that:

1. **Uses advanced NLP**: Sentence transformers for semantic understanding
2. **Detects logical errors**: Prevents false positives from ML models
3. **Supports natural input**: Speech-to-text for Tamil language
4. **Provides intelligent evaluation**: Combines rule-based and ML approaches
5. **Offers multi-level assessment**: Progressive difficulty from beginner to advanced

The system is designed to be accurate, fair, and user-friendly while leveraging modern AI technologies for intelligent answer evaluation.

