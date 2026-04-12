# Project Working Flow - Hindi Speaking Skill Assessment

This document explains the complete working flow of the Hindi Speaking Skill Assessment system, from when a user starts the test to when they receive their final results.

---

## 🎯 **Overview**

The system evaluates a user's Hindi speaking skills through 3 questions. Each answer is assessed for:
1. **Content Relevance** (must pass first)
2. **Speaking Skills** (5 factors: Fluency, Pronunciation, Confidence, Lexical, Coherence)

---

## 📋 **Complete Flow Diagram**

```
User Starts Test
    ↓
[FRONTEND] Display Rules Page
    ↓
User Clicks "Start Test"
    ↓
[FRONTEND] Question 1 Displayed
    ↓
[FRONTEND] Avatar Speaks Question (TTS)
    ↓
[FRONTEND] User Records Answer (Microphone)
    ↓
[FRONTEND] Audio Recording Stops
    ↓
[FRONTEND] Send Audio to Backend (/api/assess-answer)
    ↓
[BACKEND] STEP 1: Speech-to-Text (Whisper)
    ↓
[BACKEND] STEP 2: Basic Validation (STT Quality, Sufficiency)
    ↓
[BACKEND] STEP 3: Relevance Check (Ollama LLM)
    ↓
    ├─→ If NOT Relevant → Return "FAIL" (Stop Here)
    │
    └─→ If Relevant → Continue to Speaking Skills Evaluation
        ↓
    [BACKEND] STEP 4: Extract Audio Features (RMS, Pitch, Duration)
        ↓
    [BACKEND] STEP 5: Evaluate 5 Speaking Skills
        ├─→ Fluency (WPM + Pauses)
        ├─→ Pronunciation (Whisper Confidence + RMS Stability)
        ├─→ Confidence (Volume Stability + Pitch + Fillers)
        ├─→ Lexical (Type-Token Ratio)
        └─→ Coherence (Intro + Connectors + Conclusion)
        ↓
    [BACKEND] STEP 6: Aggregate Scores (Weighted Average)
        ↓
    [BACKEND] Return Results to Frontend
        ↓
[FRONTEND] Display Results (Overall % or FAIL)
    ↓
Repeat for Questions 2 & 3
    ↓
[FRONTEND] Show Final Results Page (All 3 Questions)
```

---

## 🔄 **Detailed Step-by-Step Flow**

### **PHASE 1: Frontend Initialization**

#### **Step 1: User Opens Website**
- Frontend loads `index.html`
- User sees rules/instructions page
- User clicks "Start Test" button

#### **Step 2: Frontend State Management**
- `conversationState` initialized with:
  - 3 Hindi questions (stored in `app.js`)
  - Current question index: 0
  - State: `INIT` → `AVATAR_SPEAKING` → `USER_SPEAKING` → `PROCESSING` → `END`

---

### **PHASE 2: Question Presentation**

#### **Step 3: Avatar Speaks Question**
- Frontend uses browser TTS (`speechSynthesis`)
- Avatar "speaks" the question text in Hindi
- Timer starts (75s for Q1, 90s for Q2, 120s for Q3)
- State changes to `USER_SPEAKING`

#### **Step 4: User Recording**
- User clicks "Start Recording" button
- Frontend requests microphone permission
- `MediaRecorder` API captures audio (WebM format)
- Live transcription shown (browser STT - for UI only)
- User speaks their answer
- User clicks "Stop Recording" or timer expires

---

### **PHASE 3: Backend Processing**

#### **Step 5: Audio Upload to Backend**
- Frontend creates `FormData` with:
  - `questionIndex`: 0, 1, or 2
  - `questionText`: The question in Hindi
  - `duration`: Recording duration in seconds
  - `audio`: WebM audio blob
- POST request to `/api/assess-answer`
- Frontend state changes to `PROCESSING`

---

### **PHASE 4: Backend Assessment Pipeline**

#### **STEP 1: Speech-to-Text (Whisper)**
**File:** `backend/main.py` → `assess_answer()` function

**What happens:**
1. Audio file saved to temporary location
2. Audio decoded using `ffmpeg` → 16kHz mono waveform
3. **Whisper model** transcribes audio:
   - Language: `"hi"` (Hindi)
   - Returns: `transcript` (raw text) + `segments` (with timestamps)
4. Text normalized: `normalize_hindi_text()` removes filler words

**Output:**
- `transcript`: Raw Hindi text
- `norm`: Normalized Hindi text
- `segments`: List with `start`, `end`, `avg_logprob` for each segment
- `avg_logprob`: Average confidence from Whisper

---

#### **STEP 2: Basic Validation Gates**
**File:** `backend/main.py` → `assess_answer()` function

**Checks performed:**

**A. STT Quality Check:**
- `avg_logprob > -1.0` AND `word_count >= 5`
- If FAIL → Return immediately with error message

**B. Sufficiency Check:**
- `word_count >= 20`
- `unique_words >= 10`
- `duration >= 8 seconds`
- If FAIL → Return immediately with "Answer too short" message

**If both pass → Continue to Relevance Check**

---

#### **STEP 3: Relevance Gate (Critical)**
**File:** `backend/main.py` → `relevance_gate_70()` → `ollama_relevance_gate()`

**What happens:**
1. **Primary Method: Ollama LLM** (local LLM)
   - Sends question + answer to Ollama
   - Prompt asks: "Is the answer topic matching the question topic?"
   - Returns: `relevance_percent` (0-100%)

2. **Threshold:** `relevance_percent >= 30%` → Relevant

3. **Fallback (if Ollama unavailable):**
   - Uses `simple_relevance_ratio()` from `relevance.py`
   - Computes keyword overlap between question and answer
   - Rule: `overlap_count >= 2` OR `overlap_ratio >= 0.2`

**Decision:**
- **If NOT Relevant (< 30%):**
  - Return immediately with `step5 = None`
  - Message: "Answer context does not match the question"
  - Frontend shows: **"FAIL"**

- **If Relevant (≥ 30%):**
  - Continue to Speaking Skills Evaluation

---

#### **STEP 4: Audio Feature Extraction**
**File:** `backend/audio_utils.py`

**What happens:**
1. **Load Audio:**
   - `load_audio()` → 16kHz mono waveform array

2. **Compute RMS Frames:**
   - `compute_rms_frames()` → Split audio into 25ms frames
   - Calculate RMS energy per frame
   - Used for: Volume stability, pronunciation clarity

3. **Compute Pitch Frames:**
   - `compute_pitch_frames()` → Extract pitch (F0) over time
   - Uses autocorrelation method
   - Filters out unvoiced frames
   - Used for: Confidence evaluation

4. **Get Duration:**
   - `get_duration()` → Total audio duration in seconds
   - Used for: WPM calculation

**Output:**
- `rms_frames`: Array of RMS values
- `pitch_frames`: Array of pitch values (Hz)
- `duration`: Duration in seconds

---

#### **STEP 5: Speaking Skills Evaluation**

**File:** `backend/aggregate.py` → `compute_step5()`

This calls 5 evaluation modules:

---

##### **5A. Fluency Evaluation**
**File:** `backend/evaluators/fluency.py` → `evaluate_fluency()`

**Inputs:**
- `transcript`: Hindi text
- `segments`: Whisper segments with timestamps
- `duration`: Audio duration

**Process:**
1. **Count words:** Clean transcript, split, count total words
2. **Compute WPM:** `WPM = total_words / (duration / 60)`
3. **Detect pauses:** Find gaps > 0.8s between segments
4. **Score mapping:**
   - WPM 90-130 → Good (no penalty)
   - WPM 70-90 or 130-160 → Acceptable (-1.5)
   - WPM < 70 or > 160 → Poor (-3.0)
   - Pauses 0-2 → Good, 3-5 → Ok (-1.0), >5 → Poor (-2.5)

**Output:** Score 0-10

---

##### **5B. Pronunciation Evaluation**
**File:** `backend/evaluators/pronunciation.py` → `evaluate_pronunciation()`

**Inputs:**
- `avg_logprob`: Whisper confidence
- `rms_frames`: RMS energy frames

**Process:**
1. **Primary: Whisper Confidence**
   - `avg_logprob > -0.3` → Very good (10.0)
   - `-0.6 to -0.3` → Average (5-7)
   - `< -0.6` → Poor (2-4)

2. **Adjustment: RMS Stability**
   - Low mean RMS → Penalty (mumbling)
   - High CV → Penalty (unstable)
   - Low CV → Bonus (stable)

**Output:** Score 0-10

---

##### **5C. Confidence Evaluation**
**File:** `backend/evaluators/confidence.py` → `evaluate_confidence()`

**Inputs:**
- `rms_frames`: RMS energy frames
- `pitch_frames`: Pitch values
- `transcript`: Hindi text

**Process:**
1. **Volume Stability:**
   - Low mean RMS → Penalty (weak voice)
   - CV < 0.4 → Good, CV > 0.6 → Poor

2. **Pitch Variation:**
   - Std 15-50 Hz → Good (confident)
   - Std < 8 Hz → Monotone (penalty)
   - Std > 70 Hz → Nervous (penalty)

3. **Filler Words:**
   - Count Hindi fillers: "उह", "अ", "हम्म", etc.
   - 0-1 → Good, 2-4 → Ok, >4 → Poor

4. **Combine:** Average of 3 sub-scores

**Output:** Score 0-10

---

##### **5D. Lexical Evaluation**
**File:** `backend/evaluators/lexical.py` → `evaluate_lexical()`

**Inputs:**
- `transcript`: Hindi text

**Process:**
1. **Clean & tokenize:** Remove punctuation, normalize
2. **Count:** `total_words`, `unique_words`
3. **Compute TTR:** `TTR = unique_words / total_words`
4. **Score mapping:**
   - TTR > 0.50 → Rich (8-10)
   - TTR 0.35-0.50 → Average (5-7)
   - TTR < 0.35 → Poor (2-4)

**Output:** Score 0-10

---

##### **5E. Coherence Evaluation**
**File:** `backend/evaluators/coherence.py` → `evaluate_coherence()`

**Inputs:**
- `transcript`: Hindi text
- `config`: Loaded from `hi_config.json`

**Process:**
1. **Load phrases** from `hi_config.json`:
   - Intro phrases: "मेरे विचार से", "मैं सोचता हूं", etc.
   - Connectors: "क्योंकि", "लेकिन", "इसलिए", etc.
   - Conclusion: "अंत में", "निष्कर्ष में", etc.

2. **Check structure:**
   - Intro present? → +1 point
   - Connectors count: 3+ → +1.5, 2 → +1.0, 1 → +0.5
   - Conclusion present? → +1 point

3. **Score mapping:**
   - ≥ 3.0 points → High (8-10)
   - 1.5-3.0 points → Medium (5-7)
   - < 1.5 points → Low (2-4)

**Output:** Score 0-10

---

#### **STEP 6: Score Aggregation**
**File:** `backend/aggregate.py` → `compute_step5()`

**Weighted Average:**
```
Overall = (0.25 × Fluency) + 
          (0.20 × Pronunciation) + 
          (0.20 × Confidence) + 
          (0.20 × Coherence) + 
          (0.15 × Lexical)
```

**Convert to Percentages:**
- Each score (0-10) → Percentage (0-100%)
- Formula: `percentage = score × 10`

**Output:**
- `Step5Scores` object with:
  - Individual scores (0-10) and percentages (0-100%)
  - Overall score and percentage
  - Detailed breakdown for each factor

---

### **PHASE 5: Results Return**

#### **Step 7: Backend Response**
**File:** `backend/main.py` → `assess_answer()` return

**Response Structure:**
```json
{
  "questionIndex": 0,
  "transcript": "मेरे विचार से...",
  "normalizedTranscript": "...",
  "wordCount": 45,
  "duration": 12.5,
  "sttOk": true,
  "relevanceOk": true,
  "relevancePercent": 85.5,
  "relevanceStatus": "Relevant",
  "step5": {
    "fluencyPercent": 85.0,
    "pronunciationPercent": 78.5,
    "confidencePercent": 82.0,
    "coherencePercent": 75.0,
    "lexicalPercent": 70.0,
    "overallPercent": 79.2
  }
}
```

---

### **PHASE 6: Frontend Display**

#### **Step 8: Process Results**
**File:** `app.js` → `assessLatestRecordingAndContinue()`

**What happens:**
1. Frontend receives response
2. Stores in `conversationState.assessments[questionIndex]`
3. Updates UI:
   - If `step5` exists → Show overall percentage
   - If `step5` is null → Show "FAIL" (relevance failed)

#### **Step 9: Move to Next Question**
- If not last question → Move to next question
- Repeat Steps 3-8 for Questions 2 and 3

#### **Step 10: Final Results Page**
**File:** `app.js` → `showResultsPage()`

**Display:**
- For each question:
  - If relevance failed → Show "FAIL"
  - If relevance passed → Show overall percentage only
- Summary of all 3 questions

---

## 🔑 **Key Components**

### **Frontend Files:**
- `index.html`: UI structure
- `style.css`: Styling
- `app.js`: State management, audio recording, API calls

### **Backend Files:**
- `main.py`: FastAPI server, endpoints, Whisper STT, relevance check
- `audio_utils.py`: Audio feature extraction (RMS, pitch, duration)
- `evaluators/fluency.py`: WPM and pause analysis
- `evaluators/pronunciation.py`: Whisper confidence + RMS stability
- `evaluators/confidence.py`: Volume, pitch, filler word analysis
- `evaluators/lexical.py`: Type-Token Ratio calculation
- `evaluators/coherence.py`: Structural pattern matching
- `relevance.py`: Keyword overlap check (fallback)
- `aggregate.py`: Score aggregation and weighting
- `hi_config.json`: Hindi phrases for coherence evaluation

---

## ⚙️ **Technologies Used**

1. **Frontend:**
   - HTML5, CSS3, JavaScript
   - MediaRecorder API (audio recording)
   - SpeechSynthesis API (TTS for avatar)
   - Fetch API (HTTP requests)

2. **Backend:**
   - FastAPI (Python web framework)
   - Whisper (OpenAI speech-to-text)
   - Ollama (Local LLM for relevance)
   - NumPy (Audio processing)
   - FFmpeg (Audio decoding)

---

## 🎯 **Decision Points**

1. **STT Quality:** If `avg_logprob <= -1.0` → Stop
2. **Sufficiency:** If `words < 20` OR `duration < 8s` → Stop
3. **Relevance:** If `relevance_percent < 30%` → Return "FAIL", Stop
4. **If all pass:** Continue to full speaking skills evaluation

---

## 📊 **Scoring Summary**

- **Relevance:** Must be ≥ 30% to proceed
- **Fluency:** 25% weight (WPM + pauses)
- **Pronunciation:** 20% weight (Whisper + RMS)
- **Confidence:** 20% weight (Volume + pitch + fillers)
- **Coherence:** 20% weight (Structure)
- **Lexical:** 15% weight (Vocabulary diversity)

**Final Overall Score:** Weighted average of all 5 factors (0-100%)

---

This workflow ensures that only relevant, sufficient answers are evaluated for speaking skills, making the system fair and efficient.

