# -*- coding: utf-8 -*-
"""
MODULE 1 — Fluency & Pace Analyzer
Measures: Smoothness and speed of speech
Supports Unicode Tamil text processing
"""
from typing import Optional, Any


def analyze_fluency(segments: list[dict[str, Any]], norm_text: str, duration: Optional[float]) -> tuple[float, dict[str, Any]]:
    """
    MODULE 1: Fluency & Pace Analyzer
    Inputs: Transcript text, Audio duration, Word timestamps (if available)
    Output: {fluency: score, wpm: value, longPauses: count}
    """
    words = [w for w in norm_text.split() if w]
    word_count = len(words)

    # Extract timestamps from segments
    segs = []
    for s in segments or []:
        if "start" in s and "end" in s:
            segs.append((float(s["start"]), float(s["end"])))
    segs.sort(key=lambda x: x[0])

    # Calculate duration
    inferred_duration = segs[-1][1] if segs else (duration or 0.0)
    total_dur = float(duration) if duration is not None else float(inferred_duration)
    total_dur = max(total_dur, 0.001)

    # Calculate WPM (Words Per Minute)
    duration_minutes = total_dur / 60.0
    wpm = word_count / duration_minutes if duration_minutes > 0 else 0.0

    # Detect pauses from timestamp gaps
    pauses = []
    for (s1, e1), (s2, e2) in zip(segs, segs[1:]):
        gap = max(0.0, s2 - e1)
        pauses.append(gap)
    
    pause_count = sum(1 for p in pauses if p > 0.6)  # Pauses > 0.6 sec
    long_pauses = sum(1 for p in pauses if p > 1.5)  # Long pauses > 1.5 sec

    # Scoring based on WPM ranges (Tamil ideal: 110-150 WPM)
    if 110 <= wpm <= 150:
        score = 9.5  # Ideal range: 9-10
    elif 90 <= wpm < 110 or 150 < wpm <= 170:
        score = 7.5  # 7-8 range
    elif 70 <= wpm < 90 or 170 < wpm <= 190:
        score = 5.5  # 5-6 range
    else:
        score = 3.5  # 3-4 range

    # Reduce score for long pauses: -0.5 per long pause (max -2)
    long_pause_penalty = min(2.0, long_pauses * 0.5)
    score -= long_pause_penalty

    score = _clamp(score, 0.0, 10.0)
    
    return score, {
        "fluency": round(score, 2),
        "wpm": round(wpm, 1),
        "longPauses": int(long_pauses),
        "pauseCount": int(pause_count),
    }


def _clamp(x: float, lo: float, hi: float) -> float:
    """Clamp a value between lo and hi."""
    return max(lo, min(hi, x))

