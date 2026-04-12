# -*- coding: utf-8 -*-
"""
Tamil Speaking Skill Assessment API
Supports Unicode Tamil text processing
"""
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import tempfile
import os
import whisper
import numpy as np
from typing import Optional, Any
from functools import lru_cache
import json
from dotenv import load_dotenv
import shutil
import sys
import traceback
import subprocess
import requests

# Import speaking skill evaluation modules
from aggregate import compute_step5
from utils import clamp


# Configure FastAPI for Unicode support and static frontend
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# Custom JSON encoder that preserves Unicode
class UnicodeJSONResponse(JSONResponse):
    def render(self, content) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,  # Preserve Unicode characters (Tamil text)
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")

app = FastAPI(
    title="Tamil Speaking Skill – STEP 4/5 API",
    default_response_class=UnicodeJSONResponse  # Use Unicode-aware JSON responses
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Config
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Frontend (index.html, app.js, style.css) lives in parent of backend
_FRONTEND_DIR = os.path.abspath(os.path.join(_BASE_DIR, ".."))
# Always load backend/.env regardless of where uvicorn is started from.
load_dotenv(dotenv_path=os.path.join(_BASE_DIR, ".env"), override=False)


def get_ollama_config() -> tuple[str, str]:
    """
    Returns (base_url, model_name) for Ollama.
    Defaults: http://localhost:11434, qwen2.5:3b
    """
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip()
    model_name = os.getenv("OLLAMA_MODEL", "qwen2.5:3b").strip()
    return base_url, model_name


WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL", "base").strip() or "base"
whisper_model = whisper.load_model(WHISPER_MODEL_NAME)


def ffmpeg_info() -> dict[str, Any]:
    ff = shutil.which("ffmpeg")
    info: dict[str, Any] = {"ffmpegPath": ff}
    try:
        import imageio_ffmpeg  # type: ignore

        info["imageioFfmpegExe"] = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:
        info["imageioFfmpegExe"] = None
        info["imageioFfmpegError"] = str(e)
    info["resolvedFfmpegExe"] = get_ffmpeg_exe_path()
    return info


def ensure_ffmpeg_available() -> None:
    """
    Whisper requires an ffmpeg executable to decode webm/ogg/mp3/etc.
    On Windows this is a very common cause of 'ASR failed'.
    We attempt to provide ffmpeg via imageio-ffmpeg automatically.
    """
    if shutil.which("ffmpeg"):
        return
    try:
        import imageio_ffmpeg  # type: ignore

        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        ffmpeg_dir = os.path.dirname(ffmpeg_exe)
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
    except Exception:
        # If this fails, Whisper will raise a clear error at transcribe time.
        return


ensure_ffmpeg_available()

def get_ffmpeg_exe_path() -> Optional[str]:
    """
    Returns absolute path to ffmpeg executable.
    Prefer system ffmpeg, else use imageio-ffmpeg bundled binary.
    """
    ff = shutil.which("ffmpeg")
    if ff:
        return ff
    try:
        import imageio_ffmpeg  # type: ignore

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def load_audio_array(audio_path: str, sr: int = 16000) -> np.ndarray:
    """
    Decode audio into float32 mono waveform using ffmpeg (absolute path if needed).
    This avoids Whisper's internal 'ffmpeg' PATH lookup on Windows.
    """
    ffmpeg_exe = get_ffmpeg_exe_path()
    if not ffmpeg_exe:
        raise FileNotFoundError("ffmpeg executable not found (install ffmpeg or imageio-ffmpeg)")

    cmd = [
        ffmpeg_exe,
        "-nostdin",
        "-threads",
        "0",
        "-i",
        audio_path,
        "-f",
        "s16le",
        "-ac",
        "1",
        "-acodec",
        "pcm_s16le",
        "-ar",
        str(sr),
        "-",
    ]
    out = subprocess.run(cmd, capture_output=True, check=True).stdout
    audio = np.frombuffer(out, np.int16).flatten().astype(np.float32) / 32768.0
    return audio


class GateResult(BaseModel):
    questionIndex: int
    transcript: str
    normalizedTranscript: str
    wordCount: int
    duration: Optional[float]
    sttOk: bool
    relevanceOk: bool
    sufficiencyOk: bool
    isValid: bool
    message: str


class Step5Scores(BaseModel):
    fluency: float  # Score 0-10
    pronunciation: float  # Score 0-10
    coherence: float  # Score 0-10
    lexical: float  # Score 0-10
    confidence: float  # Score 0-10
    overall: float  # Score 0-10
    details: dict[str, Any]
    # Percentage fields (0-100%)
    fluencyPercent: float
    pronunciationPercent: float
    coherencePercent: float
    lexicalPercent: float
    confidencePercent: float
    overallPercent: float


class AssessmentResult(BaseModel):
    questionIndex: int
    transcript: str
    normalizedTranscript: str
    wordCount: int
    duration: Optional[float]
    sttOk: bool
    relevanceOk: bool
    sufficiencyOk: bool
    isValid: bool
    message: str
    relevancePercent: float
    relevanceStatus: str  # "Relevant" or "Not Relevant" (based on 30% threshold)
    relevanceThreshold: float
    relevanceMethod: str
    relevanceReason: str
    minOverallRequired: float
    minOverallOk: bool
    finalOverall: float
    step5: Optional[Step5Scores]


def normalize_tamil_text(text: str) -> str:
    """Minimized normalization to avoid losing context."""
    return " ".join(text.strip().split())


def simple_relevance_check(question: str, transcript: str) -> bool:
    if not question or not transcript:
        return False
    import re

    def tokenize(s: str):
        s = s.lower()
        # Use full Tamil Unicode range for better character matching
        s = re.sub(r"[^\u0B80-\u0BFFa-z0-9\s]", " ", s)
        return [t for t in s.split() if t]

    q_tokens = set(tokenize(question))
    t_tokens = set(tokenize(transcript))
    if not q_tokens or not t_tokens:
        return False
    overlap = q_tokens.intersection(t_tokens)
    ratio = len(overlap) / len(q_tokens)
    return ratio >= 0.2


def simple_relevance_ratio(question: str, transcript: str) -> float:
    """Aggressive Tamil-aware relevance check with stem matching and topic keywords."""
    if not question or not transcript:
        return 0.0
    import re

    def tokenize(s: str):
        # Allow Tamil, English, and Numbers
        s = s.lower()
        s = re.sub(r"[^\u0B80-\u0BFFa-zA-Z0-9\s]", " ", s)
        return [t for t in s.split() if t]

    q_tokens = tokenize(question)
    t_text = transcript.lower()
    
    # Common Tamil particles/fillers - these should NOT be used for relevance
    fillers = {"பற்றி", "என்ன", "உங்கள்", "உள்ளது", "என்பது", "ஒரு", "அந்த", "இந்த", "அதாவது", "வந்து", "மூலியமா", "மூலம்", "அப்புறம்", "இப்போ", "இப்ப", "அதனால", "அதல", "பட்"}
    
    # Meaningful keywords from question
    meaningful_q = [q for q in q_tokens if q not in fillers and len(q) > 2]
    
    # Manual high-value keywords for common topics
    topic_map = {
        "திரைப்படம்": ["படம்", "திரை", "பார்"], # movie topic
        "பள்ளி": ["பள்ளி", "படி", "ஆசிரியர்"], # school topic
        "விளையாட்டு": ["விளையா", "ஆடு", "கிரிக்கெட்"], # sports topic
    }
    
    # Add related keywords to meaningful_q for better matching
    extra_q = []
    for mq in meaningful_q:
        for k, aliases in topic_map.items():
            if k in mq or mq in k:
                extra_q.extend(aliases)
    
    meaningful_q = list(set(meaningful_q + extra_q))
        
    if not meaningful_q:
        return 0.2 # Give some baseline if question is weird
        
    matches = 0
    t_words = t_text.split()
    
    for q in meaningful_q:
        q_stem = q[:3] if len(q) > 3 else q # Even shorter stems for Tamil
        
        # 1. Direct contains match (handles 'திரைப்படங்களை' vs 'திரைப்படம்')
        if q in t_text:
            matches += 1
        else:
            # 2. Heuristic word-by-word stem match
            for t in t_words:
                if len(t) >= 3 and (q_stem in t or t.startswith(q_stem)):
                    matches += 1
                    break
                    
    ratio = matches / len(meaningful_q)
    # Cap ratio to 1.0
    return float(min(1.0, ratio))


@lru_cache(maxsize=1)
def get_embedding_model():
    return None


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-12
    return float(np.dot(a, b) / denom)


def relevance_similarity(question: str, transcript: str) -> tuple[Optional[float], str]:
    """
    Returns (similarity, method).
    similarity is None when embeddings aren't available.
    """
    return None, "disabled"


def parse_json_from_text(text: str) -> Optional[dict[str, Any]]:
    if not text:
        return None
    text = text.strip()
    # Remove markdown code blocks if present
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
        text = text.strip()
    # Try direct JSON first
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    # Try to extract first {...} block (more robust)
    start = text.find("{")
    if start == -1:
        return None
    # Find matching closing brace
    brace_count = 0
    end = -1
    for i in range(start, len(text)):
        if text[i] == "{":
            brace_count += 1
        elif text[i] == "}":
            brace_count -= 1
            if brace_count == 0:
                end = i
                break
    if end > start:
        chunk = text[start : end + 1]
        try:
            obj = json.loads(chunk)
            if isinstance(obj, dict):
                return obj
        except Exception:
            # Try fixing common issues: unescaped quotes in strings
            try:
                # Replace problematic patterns
                fixed = chunk.replace('"reason": "', '"reason": "').replace('", "', '", "')
                obj = json.loads(fixed)
                if isinstance(obj, dict):
                    return obj
            except Exception:
                pass
    # Fallback: try to extract relevance_percent even from incomplete JSON
    import re
    # Look for "relevance_percent": number pattern
    match = re.search(r'"relevance_percent"\s*:\s*(\d+(?:\.\d+)?)', text)
    if match:
        try:
            percent = float(match.group(1))
            # Try to extract reason if possible
            reason_match = re.search(r'"reason"\s*:\s*"([^"]*)"', text)
            reason = reason_match.group(1) if reason_match else ""
            return {"relevance_percent": percent, "reason": reason}
        except Exception:
            pass
    return None


def ollama_relevance_gate(question: str, transcript: str, question_index: Optional[int] = None) -> tuple[Optional[float], str, str]:
    """
    Returns (relevance_percent, method, reason).
    Uses Ollama (local LLM) for relevance checking. No API keys needed.
    question_index: Optional question index (0-based) for question-specific leniency.
    """
    base_url, model_name = get_ollama_config()

    # LLM ONLY checks content relevance - NOT fluency, pronunciation, or speaking skills
    # Returns percentage, but we'll convert to "Relevant" (>=30%) or "Not Relevant" (<30%)
    prompt = f"""You are a professional Tamil language teacher evaluating a speaking test.
The student is answering the following question in normal, colloquial Tamil (may include some English words like 'but', 'so', 'now').

QUESTION: "{question}"
ANSWER: "{transcript}"

CRITICAL INSTRUCTIONS:
1. Does the answer discuss the core topic of the question?
2. If the user talks about the topic (e.g., movies, their quality, watching them), they MUST pass.
3. Be EXTREMELY lenient. COLLOQUIAL Tamil and casual speech are 100% acceptable.
4. Only reject if the answer is completely random gibberish or about an entirely different world (e.g., "I like idli" for a "movie" question).

Scoring Logic:
- 70-100%: On topic, even if casual or uses fillers.
- 40-69%: Touches the topic but is very brief.
- 0-39%: Completely off-topic.

Output strictly JSON:
{{
  "relevance_percent": [score],
  "reason": "[teacher explanation in tamil]"
}}""".strip()

    try:
        # Check if transcript is essentially empty or just a few characters
        if len(transcript.strip()) < 5:
             return 0.0, "too_short", "Transcript too short to be relevant"

        print(f"--- Ollama: Checking relevance for q='{question[:30]}...' ---")
        resp = requests.post(
            f"{base_url}/api/generate",
            json={
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "stop": ["}"]
                },
            },
            timeout=18,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data.get("response", "").strip()
        
        if text and not text.endswith("}"):
            text += "}"
            
        if not text:
            print("--- Ollama: Empty response ---")
            return None, "ollama_empty", "Ollama returned empty response"
            
        print(f"--- Ollama Response: {text[:100]}... ---")
        obj = parse_json_from_text(text)
        if not obj:
            return None, "ollama_parse_error", "Failed to parse JSON from Ollama"
            
        percent = obj.get("relevance_percent")
        reason = obj.get("reason", "")
        
        if percent is None:
             return None, "ollama_missing_field", "Ollama response missing relevance_percent"
             
        try:
            percent = float(percent)
        except:
            return None, "ollama_invalid_type", "relevance_percent is not a number"
            
        return clamp(percent, 0.0, 100.0), f"ollama:{model_name}", reason
    except requests.exceptions.ConnectionError:
        print("--- Ollama: Connection failed ---")
        return None, "ollama_unavailable", f"Ollama server not reachable at {base_url}"
    except requests.exceptions.Timeout:
        print("--- Ollama: Timeout ---")
        return None, "ollama_timeout", "Ollama request timed out"
    except Exception as e:
        print(f"--- Ollama: Error: {e} ---")
        return None, "ollama_error", str(e)


def relevance_gate_70(question: str, transcript: str, question_index: Optional[int] = None) -> tuple[float, float, str, str]:
    """
    Teacher-mode relevance gate.
    Threshold: 15.0% (Very lenient to allow valid but short/colloquial answers).
    """
    threshold = 15.0
    
    # 1. Primary Check: Keyword Overlap (Most reliable for short/colloquial text)
    fallback_percent = simple_relevance_ratio(question, transcript) * 100.0
    
    # 2. Secondary Check: Ollama
    percent, method, reason = ollama_relevance_gate(question, transcript, question_index)
    
    # If student used more than 20 words and has ANY keyword match, auto-boost
    word_count = len(transcript.split())
    if word_count > 25 and fallback_percent > 10.0:
        print(f"--- [DEBUG] High word count ({word_count}) + Keywords. Auto-boosting relevance. ---")
        fallback_percent = max(fallback_percent, 75.0)
        reason = reason or "Confirmed relevant long-form answer in Tamil."

    # Logic: Favor the higher score
    if percent is not None and "error" not in method and "unavailable" not in method:
         final_percent = max(percent, fallback_percent)
         print(f"--- [DEBUG] Final relevance: max({percent}, {fallback_percent}) = {final_percent}% ---")
         return final_percent, threshold, method, reason or "Teacher's balanced evaluation"

    return fallback_percent, threshold, "keyword_engine", "Manual teacher evaluation based on keywords"

def check_sufficiency(transcript: str, duration: Optional[float]) -> bool:
    words = [w for w in transcript.split() if w]
    word_count = len(words)
    unique_words = len(set(words))
    # Teacher mode: as long as there is an attempt, let's grade it
    if word_count < 2:
        return False
    if unique_words < 2:
        return False
    # Check duration if meaningful 
    if duration is not None and duration > 1.0 and duration < 2.0:
        return False
    return True


# ============================================================================
# Speaking skill evaluation modules have been moved to separate files:
# - fluency.py
# - pronunciation.py  
# - confidence.py
# - lexical.py
# - coherence.py
# - aggregate.py
# - utils.py
# ============================================================================


def weighted_overall(question_index: int, s: Step5Scores) -> float:
    # Level-based weighting (Q3 emphasizes coherence more)
    if question_index == 0:  # basic
        w = {"fluency": 0.25, "pronunciation": 0.25, "coherence": 0.15, "lexical": 0.15, "confidence": 0.20}
    elif question_index == 1:  # mid
        w = {"fluency": 0.22, "pronunciation": 0.22, "coherence": 0.20, "lexical": 0.18, "confidence": 0.18}
    else:  # final
        w = {"fluency": 0.20, "pronunciation": 0.20, "coherence": 0.25, "lexical": 0.20, "confidence": 0.15}
    overall = (
        s.fluency * w["fluency"]
        + s.pronunciation * w["pronunciation"]
        + s.coherence * w["coherence"]
        + s.lexical * w["lexical"]
        + s.confidence * w["confidence"]
    )
    return float(round(overall, 2))


@app.post("/api/gate-answer", response_model=GateResult)
async def gate_answer(
    questionIndex: int = Form(...),
    questionText: str = Form(...),
    duration: Optional[float] = Form(None),
    audio: UploadFile = File(...),
):
    if not audio.filename:
        raise HTTPException(status_code=400, detail="No audio file uploaded")

    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(audio.filename)[1]) as tmp:
        contents = await audio.read()
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        audio_arr = load_audio_array(tmp_path, sr=16000)
        result = whisper_model.transcribe(
            audio_arr,
            language="ta",
            fp16=False,
            beam_size=1,
            best_of=1,
            temperature=0,
        )
    except Exception as e:
        os.remove(tmp_path)
        raise HTTPException(status_code=500, detail=f"ASR failed: {e}")

    os.remove(tmp_path)

    transcript = (result.get("text") or "").strip()
    norm = normalize_tamil_text(transcript)
    words = norm.split()
    word_count = len(words)

    segments = result.get("segments") or []
    if segments:
        avg_logprob = np.mean(
            [s["avg_logprob"] for s in segments if "avg_logprob" in s]
        )
        # Real teacher mode: Don't reject just because of accent logprob. Let relevance decide.
        stt_ok = word_count >= 2
    else:
        stt_ok = False

    relevance_ok = simple_relevance_check(questionText, norm)
    sufficiency_ok = check_sufficiency(norm, duration)

    is_valid = bool(stt_ok and relevance_ok and sufficiency_ok)

    if not stt_ok:
        message = "Speech recognition confidence is too low or audio too short."
    elif not relevance_ok:
        message = "Answer does not seem related to the question."
    elif not sufficiency_ok:
        message = "Answer is too short or lacks content."
    else:
        message = "Answer passed content gate and can be evaluated further."

    return GateResult(
        questionIndex=questionIndex,
        transcript=transcript,
        normalizedTranscript=norm,
        wordCount=word_count,
        duration=duration,
        sttOk=stt_ok,
        relevanceOk=relevance_ok,
        sufficiencyOk=sufficiency_ok,
        isValid=is_valid,
        message=message,
    )


@app.post("/api/assess-answer", response_model=AssessmentResult)
async def assess_answer(
    questionIndex: int = Form(...),
    questionText: str = Form(...),
    duration: Optional[float] = Form(None),
    audio: UploadFile = File(...),
):
    """
    STEP 4 + STEP 5 combined endpoint:
    - Runs Whisper STT + normalization + gate (STEP 4)
    - Uses Ollama (local LLM) to check relevance >= 30%
    - Only if relevant, computes speaking-skill metrics (STEP 5)
    """
    if not audio.filename:
        raise HTTPException(status_code=400, detail="No audio file uploaded")

    suffix = os.path.splitext(audio.filename)[1] or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        contents = await audio.read()
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        print(f"--- Processing Question {questionIndex} ---")
        print(f"--- Audio path: {tmp_path} ---")
        audio_arr = load_audio_array(tmp_path, sr=16000)
        print("--- Running Whisper STT... ---")
        result = whisper_model.transcribe(
            audio_arr,
            language="ta",
            fp16=False,
            beam_size=1,
            best_of=1,
            temperature=0,
        )
        print("--- Whisper STT complete. ---")
    except Exception as e:
        # Most common reason: ffmpeg missing / can't decode webm
        traceback.print_exc()
        ff = ffmpeg_info()
        os.remove(tmp_path)
        print(f"--- ASR failed: {e} ---")
        raise HTTPException(
            status_code=500,
            detail=(
                f"ASR failed ({type(e).__name__}): {e}. "
                f"ffmpegPath={ff.get('ffmpegPath')}, imageioFfmpegExe={ff.get('imageioFfmpegExe')}. "
                "If ffmpegPath is null, run: pip install -r requirements.txt (imageio-ffmpeg) "
                "or install ffmpeg and add it to PATH."
            ),
        )

    transcript = (result.get("text") or "").strip()
    norm = normalize_tamil_text(transcript)
    word_count = len([w for w in norm.split() if w])

    segments = result.get("segments") or []
    if segments:
        avg_logprob = np.mean([s["avg_logprob"] for s in segments if "avg_logprob" in s])
        # Real teacher mode: Let relevance check handle weird text, don't fail logprob implicitly.
        stt_ok = word_count >= 2
    else:
        stt_ok = False

    # STEP 1: Check STT first
    sufficiency_ok = check_sufficiency(norm, duration)
    
    if not stt_ok:
        os.remove(tmp_path)
        return AssessmentResult(
            questionIndex=questionIndex,
            transcript=transcript,
            normalizedTranscript=norm,
            wordCount=word_count,
            duration=duration,
            sttOk=stt_ok,
            relevanceOk=False,
            sufficiencyOk=sufficiency_ok,
            isValid=False,
            message="Speech recognition confidence is too low or audio too short.",
            relevancePercent=0.0,
            relevanceStatus="Not Checked",
            relevanceThreshold=30.0,
            relevanceMethod="stt_failed",
            relevanceReason="STT failed, cannot check relevance",
            minOverallRequired=0.0,
            minOverallOk=False,
            finalOverall=0.0,
            step5=None,
        )
    
    if not sufficiency_ok:
        os.remove(tmp_path)
        return AssessmentResult(
            questionIndex=questionIndex,
            transcript=transcript,
            normalizedTranscript=norm,
            wordCount=word_count,
            duration=duration,
            sttOk=stt_ok,
            relevanceOk=False,
            sufficiencyOk=sufficiency_ok,
            isValid=False,
            message="Answer is too short or lacks content.",
            relevancePercent=0.0,
            relevanceStatus="Not Checked",
            relevanceThreshold=30.0,
            relevanceMethod="sufficiency_failed",
            relevanceReason="Answer too short, cannot check relevance",
            minOverallRequired=0.0,
            minOverallOk=False,
            finalOverall=0.0,
            step5=None,
        )

    # STEP 2: Check relevance FIRST - this is the critical gate
    print("--- Running Relevance Check... ---")
    rel_percent, rel_threshold, rel_method, rel_reason = relevance_gate_70(questionText, norm, questionIndex)
    print(f"--- Relevance: {rel_percent}% (Method: {rel_method}) ---")
    
    relevance_ok = bool(rel_percent >= rel_threshold)  # >= 30%
    relevance_status = "Relevant" if relevance_ok else "Not Relevant"
    
    # STEP 3: If relevance FAILS, return immediately with "wrong" message
    if not relevance_ok:
        os.remove(tmp_path)
        return AssessmentResult(
            questionIndex=questionIndex,
            transcript=transcript,
            normalizedTranscript=norm,
            wordCount=word_count,
            duration=duration,
            sttOk=stt_ok,
            relevanceOk=False,
            sufficiencyOk=sufficiency_ok,
            isValid=False,
            message=f"Answer context does not match the question. Relevance: {rel_percent:.1f}% (Required: {rel_threshold}%). The answer is wrong.",
            relevancePercent=float(round(rel_percent, 2)),
            relevanceStatus=relevance_status,
            relevanceThreshold=float(rel_threshold),
            relevanceMethod=rel_method,
            relevanceReason=rel_reason or "Answer topic does not match question topic",
            minOverallRequired=0.0,
            minOverallOk=False,
            finalOverall=0.0,
            step5=None,
        )

    # STEP 4: Relevance PASSED - Now evaluate all speaking skill factors
    step5 = None
    try:
        step5 = compute_step5(tmp_path, norm, segments, duration)
    except Exception as e:
        step5 = None
        os.remove(tmp_path)
        return AssessmentResult(
            questionIndex=questionIndex,
            transcript=transcript,
            normalizedTranscript=norm,
            wordCount=word_count,
            duration=duration,
            sttOk=stt_ok,
            relevanceOk=relevance_ok,
            sufficiencyOk=sufficiency_ok,
            isValid=False,
            message=f"Relevance check passed ({rel_percent:.1f}%), but evaluation failed: {e}",
            relevancePercent=float(round(rel_percent, 2)),
            relevanceStatus=relevance_status,
            relevanceThreshold=float(rel_threshold),
            relevanceMethod=rel_method,
            relevanceReason=rel_reason or "",
            minOverallRequired=0.0,
            minOverallOk=False,
            finalOverall=0.0,
            step5=None,
        )

    # Calculate weighted overall
    min_overall_required = 8.0
    if step5 is not None:
        raw_overall = weighted_overall(questionIndex, step5)
    else:
        raw_overall = 0.0

    final_overall = raw_overall if (stt_ok and sufficiency_ok) else 0.0
    min_overall_ok = bool(final_overall >= min_overall_required)
    
    # Answer is valid if relevance passed and all checks passed
    is_valid = bool(stt_ok and sufficiency_ok and relevance_ok)

    os.remove(tmp_path)

    # Success message with percentages
    message = (
        f"Answer is correct! Relevance: {rel_percent:.1f}%. "
        f"Speaking Skills - Fluency: {step5.fluencyPercent:.1f}%, "
        f"Pronunciation: {step5.pronunciationPercent:.1f}%, "
        f"Confidence: {step5.confidencePercent:.1f}%, "
        f"Coherence: {step5.coherencePercent:.1f}%, "
        f"Lexical: {step5.lexicalPercent:.1f}%, "
        f"Overall: {step5.overallPercent:.1f}%"
    )

    return AssessmentResult(
        questionIndex=questionIndex,
        transcript=transcript,
        normalizedTranscript=norm,
        wordCount=word_count,
        duration=duration,
        sttOk=stt_ok,
        relevanceOk=relevance_ok,
        sufficiencyOk=sufficiency_ok,
        isValid=is_valid,
        message=message,
        relevancePercent=float(round(rel_percent, 2)),
        relevanceStatus=relevance_status,
        relevanceThreshold=float(rel_threshold),
        relevanceMethod=rel_method,
        relevanceReason=rel_reason or "",
        minOverallRequired=min_overall_required,
        minOverallOk=min_overall_ok,
        finalOverall=final_overall,
        step5=step5,
    )

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/debug")
async def debug():
    base_url, model_name = get_ollama_config()
    # Check if Ollama is reachable
    ollama_available = False
    try:
        resp = requests.get(f"{base_url}/api/tags", timeout=2)
        ollama_available = resp.status_code == 200
    except Exception:
        pass
    return {
        "python": sys.version,
        "whisperModuleFile": getattr(whisper, "__file__", None),
        "whisperModel": WHISPER_MODEL_NAME,
        "ollamaConfigured": ollama_available,
        "ollamaBaseUrl": base_url,
        "ollamaModel": model_name,
        "ffmpeg": ffmpeg_info(),
    }



@app.get("/api/status")
async def api_status():
    """API info (formerly at /). Kept for health checks and docs."""
    return {
        "service": "Tamil Speaking Skill – STEP 4/5 API",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "gate": "/api/gate-answer",
            "assess": "/api/assess-answer",
            "tts": "/api/tts",
        },
    }


# TTS Request Model
class TTSRequest(BaseModel):
    text: str
    language: str = "ta-IN"


@app.post("/api/tts")
async def text_to_speech(request: TTSRequest):
    """
    Convert Tamil text to speech using TTS service.
    Uses gTTS (free) by default, or Google/Azure TTS if API keys are configured.
    """
    try:
        # Option 1: Use Google Cloud TTS (if API key available)
        google_api_key = os.getenv("GOOGLE_TTS_API_KEY")
        if google_api_key:
            return await use_google_tts(request.text, request.language, google_api_key)
        
        # Option 2: Use Azure TTS (if available)
        azure_key = os.getenv("AZURE_TTS_KEY")
        azure_region = os.getenv("AZURE_TTS_REGION")
        if azure_key and azure_region:
            return await use_azure_tts(request.text, request.language, azure_key, azure_region)
        
        # Option 3: Use edge-tts (High quality free neural voices - Male voice)
        try:
            import edge_tts
            import io
            
            # Use ta-IN-PallaviNeural for a clear female Tamil voice (more natural)
            # Alternative: ta-IN-KumarNeural, ta-IN-ValluvarNeural
            async def generate_edge_tts():
                communicate = edge_tts.Communicate(request.text, "ta-IN-PallaviNeural", rate="+0%", pitch="+0Hz")
                audio_data = b""
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_data += chunk["data"]
                return audio_data

            audio_content = await generate_edge_tts()
            
            from fastapi.responses import Response
            return Response(
                content=audio_content,
                media_type="audio/mpeg",
                headers={"Content-Disposition": "attachment; filename=speech.mp3"}
            )
        except ImportError:
            print("edge-tts not installed, falling back to gTTS")
        except Exception as e:
            print(f"edge-tts error: {e}, falling back to gTTS")

        # Option 4: Use gTTS (Google Text-to-Speech library - free but requires internet)
        try:
            from gtts import gTTS
            import io
            
            tts = gTTS(text=request.text, lang='ta', slow=False)
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            
            from fastapi.responses import StreamingResponse
            return StreamingResponse(
                audio_buffer,
                media_type="audio/mpeg",
                headers={"Content-Disposition": "attachment; filename=speech.mp3"}
            )
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="gTTS not installed. Install with: pip install gtts"
            )
        except Exception as e:
            print(f"gTTS error: {e}")
            raise HTTPException(status_code=500, detail=f"gTTS failed: {str(e)}")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS failed: {str(e)}")


async def use_google_tts(text: str, language: str, api_key: str):
    """Use Google Cloud Text-to-Speech API"""
    try:
        from google.cloud import texttospeech
        
        client = texttospeech.TextToSpeechClient()
        
        synthesis_input = texttospeech.SynthesisInput(text=text)
        
        # Use Tamil (India) voice - try different voice names
        voice_names = ["ta-IN-Wavenet-A", "ta-IN-Wavenet-B", "ta-IN-Standard-A", "ta-IN-Standard-B"]
        voice = None
        for vn in voice_names:
            try:
                voice = texttospeech.VoiceSelectionParams(
                    language_code="ta-IN",
                    name=vn,
                    ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
                )
                break
            except:
                continue
        
        if not voice:
            voice = texttospeech.VoiceSelectionParams(
                language_code="ta-IN",
                ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
            )
        
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        
        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        
        from fastapi.responses import StreamingResponse
        import io
        return StreamingResponse(
            io.BytesIO(response.audio_content),
            media_type="audio/mpeg",
            headers={"Content-Disposition": "attachment; filename=speech.mp3"}
        )
    except ImportError:
        raise HTTPException(status_code=503, detail="Google Cloud TTS library not installed. Install: pip install google-cloud-texttospeech")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Google TTS error: {str(e)}")


async def use_azure_tts(text: str, language: str, api_key: str, region: str):
    """Use Azure Cognitive Services Text-to-Speech"""
    try:
        import aiohttp
        
        url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
        headers = {
            "Ocp-Apim-Subscription-Key": api_key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-16khz-128kbitrate-mono-mp3"
        }
        
        # Use Tamil neural voice for natural sound
        ssml = f"""<speak version='1.0' xml:lang='ta-IN'>
            <voice xml:lang='ta-IN' xml:gender='Neutral' name='ta-IN-PrabhaNeural'>
                {text}
            </voice>
        </speak>"""
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=ssml.encode('utf-8')) as response:
                if response.status == 200:
                    audio_data = await response.read()
                    from fastapi.responses import StreamingResponse
                    import io
                    return StreamingResponse(
                        io.BytesIO(audio_data),
                        media_type="audio/mpeg",
                        headers={"Content-Disposition": "attachment; filename=speech.mp3"}
                    )
                else:
                    error_text = await response.text()
                    raise HTTPException(status_code=response.status, detail=f"Azure TTS failed: {error_text}")
    except ImportError:
        raise HTTPException(status_code=503, detail="aiohttp not installed. Install: pip install aiohttp")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Azure TTS error: {str(e)}")


# ---------------------------------------------------------------------------
# Assessment flow: next skill after speaking (reading only for intermediate/advanced)
# ---------------------------------------------------------------------------
READING_MODULE_URL = os.getenv("READING_MODULE_URL", "http://127.0.0.1:5003")
LEVELS_WITH_READING = ("intermediate", "advanced")  # both get reading after speaking; basic = listening + speaking only


@app.get("/api/flow/next-skill")
async def flow_next_skill(level: str = "basic"):
    """
    Returns the next assessment skill after speaking, based on selected level.
    - basic: no reading (listening + speaking only).
    - intermediate / advanced: next skill is reading.
    Query param: level = basic | intermediate | advanced (case-insensitive).
    """
    level_normalized = (level or "basic").strip().lower()
    show_reading = level_normalized in LEVELS_WITH_READING
    if show_reading:
        url = READING_MODULE_URL.rstrip("/") + "?fromFlow=1"
        return {"next_skill": "reading", "show_reading": True, "url": url}
    return {"next_skill": None, "show_reading": False, "url": None}


# Serve frontend (index.html, app.js, style.css) at root so portal opens the UI
# Must be last: API routes above take precedence; unmatched paths serve static files
app.mount("/", StaticFiles(directory=_FRONTEND_DIR, html=True), name="frontend")
