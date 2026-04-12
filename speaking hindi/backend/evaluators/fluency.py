# -*- coding: utf-8 -*-
"""
STEP 4: Fluency Evaluation (WPM + Pauses)
Measures how smoothly and steadily the speaker talks in Hindi.
"""
import re
from typing import Optional, Any, Dict, List, Tuple


def evaluate_fluency(transcript: str, segments: List[Dict[str, Any]], duration: Optional[float]) -> Tuple[float, Dict[str, Any]]:
    """
    Evaluate fluency based on speaking speed (WPM) and pauses.
    
    Args:
        transcript: The transcribed text (Hindi)
        segments: Whisper segments with 'start' and 'end' timestamps
        duration: Total audio duration in seconds (optional, can be inferred from segments)
    
    Returns:
        Tuple of (fluency_score (0-10), info_dict)
        info_dict contains: wpm, pause_count, avg_pause_duration, etc.
    """
    # 1️⃣ Count words
    word_count = count_words(transcript)
    
    # 2️⃣ Compute WPM (Words Per Minute)
    total_duration = get_duration(segments, duration)
    wpm = compute_wpm(word_count, total_duration)
    
    # 3️⃣ Detect pauses using segments
    pauses = detect_pauses(segments, pause_threshold=0.8)
    pause_count = len(pauses)
    avg_pause_duration = sum(pauses) / len(pauses) if pauses else 0.0
    
    # 4️⃣ & 5️⃣ Map to 0-10 score based on WPM and pauses
    score = map_to_score(wpm, pause_count, avg_pause_duration)
    
    # 6️⃣ Return useful info
    return score, {
        "fluency_score": round(score, 2),
        "wpm": round(wpm, 1),
        "pause_count": pause_count,
        "avg_pause_duration": round(avg_pause_duration, 2),
        "word_count": word_count,
        "duration": round(total_duration, 2),
    }


def count_words(transcript: str) -> int:
    """
    1️⃣ Count words
    
    Clean the transcript:
    - Remove punctuation/symbols
    - Normalize spaces
    - Split by space to get words
    - Count total words
    """
    if not transcript:
        return 0
    
    # Remove punctuation and symbols, keep Hindi Unicode characters, spaces, and basic alphanumeric
    # Hindi Unicode range: \u0900-\u097F (Devanagari script)
    cleaned = re.sub(r"[^\u0900-\u097Fa-z0-9\s]", " ", transcript)
    
    # Normalize spaces (replace multiple spaces with single space)
    cleaned = re.sub(r"\s+", " ", cleaned)
    
    # Strip leading/trailing spaces
    cleaned = cleaned.strip()
    
    # Split by space and filter out empty strings
    words = [w for w in cleaned.split() if w]
    
    return len(words)


def get_duration(segments: List[Dict[str, Any]], duration: Optional[float]) -> float:
    """
    Get total duration from segments or provided duration.
    """
    if duration is not None and duration > 0:
        return float(duration)
    
    # Infer from segments
    if segments:
        segs_with_times = []
        for s in segments:
            if "start" in s and "end" in s:
                try:
                    segs_with_times.append((float(s["start"]), float(s["end"])))
                except (ValueError, TypeError):
                    continue
        
        if segs_with_times:
            segs_with_times.sort(key=lambda x: x[0])
            last_end = segs_with_times[-1][1]
            return float(last_end)
    
    return 0.001  # Minimum duration to avoid division by zero


def compute_wpm(word_count: int, duration_seconds: float) -> float:
    """
    2️⃣ Compute WPM (Words Per Minute)
    
    WPM = total_words / (duration_in_seconds / 60)
    """
    if duration_seconds <= 0:
        return 0.0
    
    duration_minutes = duration_seconds / 60.0
    wpm = word_count / duration_minutes if duration_minutes > 0 else 0.0
    return wpm


def detect_pauses(segments: List[Dict[str, Any]], pause_threshold: float = 0.8) -> List[float]:
    """
    3️⃣ Detect pauses using segments
    
    For each consecutive pair of segments:
    - gap = start[i+1] - end[i]
    - If gap > pause_threshold: count as a pause
    
    Returns:
        List of pause durations (in seconds)
    """
    pauses = []
    
    if not segments or len(segments) < 2:
        return pauses
    
    # Extract and sort segments by start time
    segs_with_times = []
    for s in segments:
        if "start" in s and "end" in s:
            try:
                segs_with_times.append((float(s["start"]), float(s["end"])))
            except (ValueError, TypeError):
                continue
    
    if len(segs_with_times) < 2:
        return pauses
    
    segs_with_times.sort(key=lambda x: x[0])
    
    # Check gaps between consecutive segments
    for i in range(len(segs_with_times) - 1):
        end_time = segs_with_times[i][1]
        start_time = segs_with_times[i + 1][0]
        gap = start_time - end_time
        
        if gap > pause_threshold:
            pauses.append(gap)
    
    return pauses


def map_to_score(wpm: float, pause_count: int, avg_pause_duration: float) -> float:
    """
    4️⃣ & 5️⃣ Map to a 0-10 score
    
    Define "good" fluency ranges for Hindi:
    - WPM: 90-130 → good, 70-90 or 130-160 → acceptable, <70 or >160 → poor
    - Pauses: 0-2 → good, 3-5 → ok, >5 → poor
    
    Start from base score and reduce based on:
    - WPM too low/high
    - Many pauses
    - Long average pause
    """
    # Start with base score
    score = 10.0
    
    # WPM penalties
    if 90 <= wpm <= 130:
        # Good range: no penalty
        pass
    elif 70 <= wpm < 90 or 130 < wpm <= 160:
        # Acceptable range: small penalty
        score -= 1.5
    else:
        # Poor range: bigger penalty
        if wpm < 70:
            score -= 3.0  # Too slow
        else:  # wpm > 160
            score -= 3.0  # Too fast
    
    # Pause penalties
    if pause_count <= 2:
        # Good: no penalty
        pass
    elif 3 <= pause_count <= 5:
        # Ok: small penalty
        score -= 1.0
    else:
        # Poor: bigger penalty
        score -= 2.5
    
    # Long average pause penalty
    if avg_pause_duration > 2.0:
        score -= 1.0  # Very long pauses indicate hesitation
    elif avg_pause_duration > 1.5:
        score -= 0.5  # Moderately long pauses
    
    # Clamp score between 0 and 10
    score = max(0.0, min(10.0, score))
    
    return score

