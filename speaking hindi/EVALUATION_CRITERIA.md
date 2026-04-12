# Speaking Skill Evaluation Criteria

This document explains the basis on which each speaking skill factor is evaluated.

## Overall Aggregation

**Formula:**
```
Overall Score = (0.25 × Fluency) + (0.20 × Pronunciation) + (0.20 × Confidence) + (0.20 × Coherence) + (0.15 × Lexical)
```

**Weights:**
- **Fluency**: 25% (most important)
- **Pronunciation**: 20%
- **Confidence**: 20%
- **Coherence**: 20%
- **Lexical**: 15% (least important)

---

## Module 1: Fluency & Pace Analyzer

**What it measures:** Smoothness and speed of speech

**Evaluation Criteria:**

1. **Words Per Minute (WPM)**
   - **Ideal Range (110-150 WPM)**: Score 9.5/10
     - Natural speaking pace for Tamil
   - **Good Range (90-110 or 150-170 WPM)**: Score 7.5/10
   - **Acceptable Range (70-90 or 170-190 WPM)**: Score 5.5/10
   - **Too Slow/Fast (<70 or >190 WPM)**: Score 3.5/10

2. **Long Pauses Detection**
   - Detects pauses > 0.6 seconds between words
   - Long pauses > 1.5 seconds are penalized
   - **Penalty**: -0.5 points per long pause (maximum -2.0 points)

**Inputs:**
- Transcript text
- Audio duration
- Word timestamps from Whisper (if available)

**Output:**
- Fluency score (0-10)
- WPM value
- Long pauses count
- Total pause count

---

## Module 2: Pronunciation Clarity Analyzer

**What it measures:** How clearly words are articulated (NOT accent)

**Evaluation Criteria:**

1. **Whisper Confidence Score**
   - Uses Whisper's `avg_logprob` to measure recognition confidence
   - Higher confidence = clearer pronunciation
   - **Scoring:**
     - **avg_conf ≥ 0.85**: Score 9.5/10 (excellent clarity)
     - **0.75 ≤ avg_conf < 0.85**: Score 7.5/10 (good clarity)
     - **0.65 ≤ avg_conf < 0.75**: Score 5.5/10 (acceptable clarity)
     - **avg_conf < 0.65**: Score 3.5/10 (poor clarity)

2. **Low Confidence Ratio**
   - Percentage of words with confidence < 0.6
   - **Penalty**: If >30% words have low confidence, reduce score by up to -2.0 points

3. **Fallback Method (if Whisper unavailable)**
   - Uses audio RMS (Root Mean Square) stability
   - Lower coefficient of variation (CV) = more stable = clearer articulation
   - Maps audio stability to confidence proxy

**Inputs:**
- Whisper segment confidence scores
- Audio file (for fallback)

**Output:**
- Pronunciation score (0-10)
- Average confidence value
- Low confidence ratio (%)

---

## Module 3: Confidence (Delivery) Analyzer

**What it measures:** Stability and assertiveness of voice

**Evaluation Criteria:**

1. **Volume Stability (RMS Coefficient of Variation)**
   - Measures how consistent the volume is throughout speech
   - Lower CV = more stable = higher confidence
   - **Scoring:**
     - **CV < 0.5**: +1.5 points (very stable)
     - **0.5 ≤ CV < 1.0**: +0.5 points (moderately stable)
     - **CV > 1.5**: -1.0 points (unstable)

2. **Volume Drop-offs (Hesitation Detection)**
   - Detects sudden volume drops (indicating hesitation)
   - **Scoring:**
     - **Drop ratio < 0.2**: +1.0 points (confident delivery)
     - **Drop ratio > 0.4**: -1.5 points (many hesitations)

3. **Pitch Variation**
   - Measures natural variation in voice pitch
   - Too monotone or too erratic = lower confidence
   - **Scoring:**
     - **15-50 Hz variation**: +0.5 points (good variation)
     - **< 8 Hz variation**: -1.0 points (too monotone)
     - **> 70 Hz variation**: -1.0 points (too erratic)

4. **Filler Words Detection**
   - Counts Tamil filler words: "அ", "ம்", "அப்படின்னா", "அதாவது", "சரி", etc.
   - **Penalty**: If >5 fillers, reduce score by up to -2.0 points

**Base Score:** 7.0/10

**Inputs:**
- Audio waveform
- Pitch contour
- RMS energy
- Transcript text

**Output:**
- Confidence score (0-10)
- Filler words count
- Volume stability (CV)
- Drop-off ratio
- Pitch variation (Hz)

---

## Module 4: Lexical Richness Analyzer

**What it measures:** Variety of words used (vocabulary diversity)

**Evaluation Criteria:**

1. **Type-Token Ratio (TTR)**
   - Formula: `TTR = Unique Words / Total Words`
   - Higher TTR = more diverse vocabulary = better lexical richness
   - **Scoring:**
     - **TTR ≥ 0.55**: Score 9.0/10 (excellent variety)
     - **0.45 ≤ TTR < 0.55**: Score 6.5/10 (good variety)
     - **0.35 ≤ TTR < 0.45**: Score 4.5/10 (acceptable variety)
     - **TTR < 0.35**: Score 2.5/10 (repetitive vocabulary)

**Inputs:**
- Normalized transcript text

**Output:**
- Lexical score (0-10)
- Unique words count
- Total words count
- Type-Token Ratio (TTR)

---

## Module 5: Structural Coherence Analyzer

**What it measures:** Whether speech has proper structure (intro, body, conclusion)

**Evaluation Criteria:**

1. **Introduction Detection**
   - Checks for opening phrases: "என்னுடைய", "நான் நினைப்பது", "நான்", "எனக்கு", "முதலில்", "தொடக்கத்தில்", "ஆரம்பத்தில்"
   - **Points**: +1 if intro found

2. **Connectors Detection**
   - Checks for connecting words: "அதனால்", "மேலும்", "எடுத்துக்காட்டாக", "முதலில்", "அடுத்து", "பிறகு", "கடைசியாக", "என்பதால்", "ஆகவே", "மற்றும்", "அல்லது", "ஆனால்", "எனவே"
   - **Points**: +1 if connectors found

3. **Conclusion Detection**
   - Checks for ending phrases: "முடிவில்", "இதனால்", "கடைசியாக", "சுருக்கமாக", "மொத்தத்தில்", "எனவே", "ஆகவே"
   - **Points**: +1 if conclusion found

4. **Final Scoring:**
   - **3 points** (all elements): Score 9.0/10 (excellent structure)
   - **2 points**: Score 6.5/10 (good structure)
   - **1 point**: Score 4.5/10 (basic structure)
   - **0 points**: Score 2.5/10 (no structure)

**Inputs:**
- Normalized transcript text

**Output:**
- Coherence score (0-10)
- Has introduction (boolean)
- Has connectors (boolean)
- Has conclusion (boolean)
- Connector count

---

## Score Conversion

All module scores are on a **0-10 scale** and converted to percentages:
- **Score 0-10** → **Percentage 0-100%**
- Formula: `Percentage = Score × 10`

**Example:**
- Fluency score: 8.5/10 → 85%
- Pronunciation score: 7.0/10 → 70%
- Overall score: 8.2/10 → 82%

---

## Notes

1. **Relevance Check (Prerequisite)**
   - Before evaluating speaking skills, the answer must pass relevance check (≥30%)
   - If relevance fails, speaking skills are NOT evaluated

2. **All scores are clamped** between 0.0 and 10.0 to ensure valid ranges

3. **Tamil-specific optimizations:**
   - WPM ranges optimized for Tamil speaking pace
   - Filler words list includes Tamil-specific fillers
   - Coherence patterns use Tamil connecting phrases

