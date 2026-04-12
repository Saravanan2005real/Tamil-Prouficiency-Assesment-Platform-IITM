# -*- coding: utf-8 -*-
"""
Hindi Speaking Skill Assessment API
Supports Unicode Hindi text processing
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


# Configure FastAPI for Unicode support
from fastapi.responses import JSONResponse

# Custom JSON encoder that preserves Unicode
class UnicodeJSONResponse(JSONResponse):
    def render(self, content) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,  # Preserve Unicode characters (Hindi text)
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")

app = FastAPI(
    title="Hindi Speaking Skill – STEP 4/5 API",
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
_BASE_DIR = os.path.dirname(__file__)
# Always load backend/.env regardless of where uvicorn is started from.
load_dotenv(dotenv_path=os.path.join(_BASE_DIR, ".env"), override=False)


def get_ollama_config() -> tuple[str, str]:
    """
    Returns (base_url, model_name) for Ollama.
    Defaults: http://localhost:11434, mistral
    """
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip()
    model_name = os.getenv("OLLAMA_MODEL", "mistral").strip()
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


def normalize_hindi_text(text: str) -> str:
    cleaned = text.strip()
    # Common Hindi filler words
    fillers = ["अ", "अरे", "उम्म", "मतलब", "जैसे", "वो", "यानी"]
    for f in fillers:
        cleaned = cleaned.replace(f, " ")
    cleaned = " ".join(cleaned.split())
    return cleaned


def simple_relevance_check(question: str, transcript: str) -> bool:
    if not question or not transcript:
        return False
    import re

    def tokenize(s: str):
        if not s:
            return []
        s = s.lower().strip()
        # Hindi Unicode range: \u0900-\u097F (Devanagari script)
        # Keep Hindi characters, spaces, and basic alphanumeric
        s = re.sub(r"[^\u0900-\u097Fa-z0-9\s]", " ", s)
        # Normalize multiple spaces
        s = re.sub(r"\s+", " ", s)
        tokens = [t for t in s.split() if t and len(t) > 0]
        return tokens

    q_tokens = set(tokenize(question))
    t_tokens = set(tokenize(transcript))
    if not q_tokens or not t_tokens:
        return False
    overlap = q_tokens.intersection(t_tokens)
    ratio = len(overlap) / len(q_tokens) if q_tokens else 0.0
    # More lenient: accept 15% overlap (reduced from 20%)
    return ratio >= 0.15


def simple_relevance_ratio(question: str, transcript: str) -> float:
    if not question or not transcript:
        return 0.0
    import re

    def tokenize(s: str):
        if not s:
            return []
        s = s.lower().strip()
        # Hindi Unicode range: \u0900-\u097F (Devanagari script)
        # Keep Hindi characters, spaces, and basic alphanumeric
        s = re.sub(r"[^\u0900-\u097Fa-z0-9\s]", " ", s)
        # Normalize multiple spaces
        s = re.sub(r"\s+", " ", s)
        tokens = [t for t in s.split() if t and len(t) > 0]
        return tokens

    q_tokens = set(tokenize(question))
    t_tokens = set(tokenize(transcript))
    if not q_tokens or not t_tokens:
        return 0.0
    overlap = q_tokens.intersection(t_tokens)
    ratio = len(overlap) / len(q_tokens) if q_tokens else 0.0
    return float(ratio)


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
    prompt = f"""You are a content relevance checker. Check if the answer addresses the question topic.

QUESTION: {question}
ANSWER: {transcript}

STEP 1: Identify question topic:
- "नई चीजें सीखना क्यों जरूरी है, आप क्या सोचते हैं?" = asks about IMPORTANCE OF LEARNING / WHY LEARNING IS NECESSARY
- "अगर आप किसी नई जगह जाएं तो वहाँ के लोगों के साथ कैसे घुलमिल जाएंगे?" = asks about SOCIAL INTERACTION methods
- "समय प्रबंधन जीवन में कितना महत्वपूर्ण है, इसे उदाहरण के साथ बताइए।" = asks about TIME MANAGEMENT importance

STEP 2: Identify answer topic - what is the answer talking about?

STEP 3: Compare - does the answer address the question topic?

RULES:
- If question asks "importance of learning/why learning is necessary" and answer discusses learning, education, growth, development, benefits → 30-100% (RELEVANT)
- If question asks "social interaction" and answer discusses meeting people, communication, making friends, socializing → 30-100% (RELEVANT)
- If question asks "time management" and answer discusses time, scheduling, planning, organization → 30-100% (RELEVANT)
- If answer is completely unrelated (movies, unrelated stories) → 0-29% (NOT RELEVANT)
- Be REASONABLE: If answer is short but on-topic, give at least 30-50%. Only mark as 0-29% if clearly off-topic.

Return JSON:
{{
  "relevance_percent": number
}}""".strip()

    try:
        resp = requests.post(
            f"{base_url}/api/generate",
            json={
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.0},
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data.get("response", "").strip()
        if not text:
            return None, "ollama_error", "Ollama returned empty response"
        obj = parse_json_from_text(text)
        if not obj:
            # Show more context for debugging (first 300 chars)
            preview = text[:300] if len(text) > 300 else text
            return None, "ollama_parse_error", f"Ollama returned non-JSON output: {preview}..."
        percent = obj.get("relevance_percent", None)
        reason = obj.get("reason", "") or ""
        
        # Handle various types: number, string number, null
        if percent is None:
            return None, "ollama_parse_error", f"Ollama JSON missing relevance_percent. Got: {obj}"
        try:
            # Try converting to float (handles both int and string numbers)
            percent = float(percent)
        except (ValueError, TypeError) as e:
            return None, "ollama_parse_error", f"Invalid relevance_percent type: {type(percent).__name__} = {percent}. Full response: {text[:200]}"
        
        percent = clamp(percent, 0.0, 100.0)
        return percent, f"ollama:{model_name}", reason[:240]
    except requests.exceptions.ConnectionError:
        return None, "ollama_unavailable", f"Ollama server not reachable at {base_url}. Install Ollama and start it: https://ollama.ai"
    except requests.exceptions.Timeout:
        return None, "ollama_timeout", "Ollama request timed out (>30s)"
    except requests.exceptions.HTTPError as e:
        return None, "ollama_error", f"Ollama HTTP error: {e}"
    except Exception as e:
        return None, "ollama_error", str(e)[:240]


def relevance_gate_70(question: str, transcript: str, question_index: Optional[int] = None) -> tuple[float, float, str, str]:
    """
    Returns (percent, threshold, method, reason). Always returns a percent.
    Primary: Ollama (local LLM) ONLY.
    question_index: Optional question index (0-based) for question-specific leniency.
    NOTE: Threshold is 10% - if >=10%, it's "Relevant", else "Not Relevant".
    No token-overlap or semantic fallback is used. Purely Ollama-based.
    """
    # 10% threshold - >=10% = Relevant, <10% = Not Relevant
    threshold = 10.0

    # Call Ollama to get relevance score (0–100)
    percent, method, reason = ollama_relevance_gate(question, transcript, question_index)

    # If Ollama returned a score, use it directly
    if percent is not None:
        return percent, threshold, method, reason or "Ollama relevance check"

    # Ollama failed or returned no score – no fallback, just report 0%
    return 0.0, threshold, method or "ollama_unavailable", reason or "No relevance detected"

def check_sufficiency(transcript: str, duration: Optional[float]) -> bool:
    """
    Check sufficiency - used for informational purposes.
    Actual blocking is done in assess_answer with explicit checks.
    """
    words = transcript.split()
    word_count = len(words)
    unique_words = len(set(words))
    # Check minimum requirements
    if word_count < 10:
        return False
    if unique_words < 5:
        return False
    if duration is not None and duration < 20:
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
            language="hi",
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
    norm = normalize_hindi_text(transcript)
    words = norm.split()
    word_count = len(words)

    segments = result.get("segments") or []
    if segments:
        avg_logprob = np.mean(
            [s["avg_logprob"] for s in segments if "avg_logprob" in s]
        )
        stt_ok = avg_logprob > -1.0 and word_count >= 5
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
    clientTranscript: Optional[str] = Form(None),
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
        audio_arr = load_audio_array(tmp_path, sr=16000)
        result = whisper_model.transcribe(
            audio_arr,
            language="hi",
            fp16=False,
            beam_size=1,
            best_of=1,
            temperature=0,
        )
    except Exception as e:
        # Most common reason: ffmpeg missing / can't decode webm
        traceback.print_exc()
        ff = ffmpeg_info()
        os.remove(tmp_path)
        raise HTTPException(
            status_code=500,
            detail=(
                f"ASR failed ({type(e).__name__}): {e}. "
                f"ffmpegPath={ff.get('ffmpegPath')}, imageioFfmpegExe={ff.get('imageioFfmpegExe')}. "
                "If ffmpegPath is null, run: pip install -r requirements.txt (imageio-ffmpeg) "
                "or install ffmpeg and add it to PATH."
            ),
        )

    # Prefer browser (client) transcript if provided, otherwise use Whisper transcript
    whisper_text = (result.get("text") or "").strip()
    chosen_text = (clientTranscript or "").strip() or whisper_text

    transcript = chosen_text
    norm = normalize_hindi_text(transcript)
    word_count = len([w for w in norm.split() if w])

    segments = result.get("segments") or []
    if segments:
        avg_logprob = np.mean([s["avg_logprob"] for s in segments if "avg_logprob" in s])
        stt_ok = float(avg_logprob) > -1.0 and word_count >= 5
    else:
        stt_ok = False

    # STEP 1: Check minimum requirements (duration and word count)
    # These are separate from relevance - they're basic input requirements
    sufficiency_ok = check_sufficiency(norm, duration)

    # Check minimum word count (at least 10 words)
    if word_count < 10:
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
            message=f"Answer is too short. Please speak at least 10 words (you spoke {word_count} words).",
            relevancePercent=0.0,
            relevanceStatus="Not Checked",
            relevanceThreshold=10.0,
            relevanceMethod="insufficient_words",
            relevanceReason=f"Insufficient words: {word_count} (minimum 10 required)",
            minOverallRequired=0.0,
            minOverallOk=False,
            finalOverall=0.0,
            step5=None,
        )

    # Check minimum duration (at least 20 seconds)
    if duration is not None and duration < 20:
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
            message=f"Answer is too short. Please speak for at least 20 seconds (you spoke for {duration:.1f} seconds).",
            relevancePercent=0.0,
            relevanceStatus="Not Checked",
            relevanceThreshold=10.0,
            relevanceMethod="insufficient_duration",
            relevanceReason=f"Insufficient duration: {duration:.1f}s (minimum 20s required)",
            minOverallRequired=0.0,
            minOverallOk=False,
            finalOverall=0.0,
            step5=None,
        )

    # STEP 2: Check relevance FIRST - this is the critical gate
    rel_percent, rel_threshold, rel_method, rel_reason = relevance_gate_70(questionText, norm, questionIndex)
    
    # The relevance_gate_70 function now handles all fallback logic internally
    # No need for additional handling here - it already uses fallback as safety net
    
    # Relevance pass condition: >= 10%
    relevance_ok = bool(rel_percent >= rel_threshold)  # >= 10%
    relevance_status = "Relevant" if rel_percent >= rel_threshold else "Not Relevant"
    
    # STEP 3: If relevance FAILS (< 30%), return immediately with "wrong" message
    # This is the ONLY reason to FAIL - content not relevant to question
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
            message=f"Answer context does not match the question. Relevance: {rel_percent:.1f}% (Required: {rel_threshold}%).",
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

    # STEP 4: Relevance PASSED (>= 30%) - Now evaluate all speaking skill factors
    # Always evaluate speaking skills if relevance passed, regardless of other factors
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
    # Don't require minimum overall - just calculate and show percentages
    min_overall_required = 0.0  # No minimum required
    if step5 is not None:
        raw_overall = weighted_overall(questionIndex, step5)
    else:
        raw_overall = 0.0

    # Always use the calculated overall, don't set to 0 based on other factors
    final_overall = raw_overall
    min_overall_ok = True  # Always OK since we don't require minimum
    
    # Answer is valid if relevance passed (>= 30%) - that's the only requirement
    is_valid = bool(relevance_ok)

    os.remove(tmp_path)

    # Success message - relevance passed, show percentages
    message = (
        f"Answer is relevant! Relevance: {rel_percent:.1f}%. "
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



@app.get("/")
async def root():
    return {
        "service": "Hindi Speaking Skill – STEP 4/5 API",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "gate": "/api/gate-answer",
            "assess": "/api/assess-answer",
        },
    }


