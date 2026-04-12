# -*- coding: utf-8 -*-
"""
MODULE 3 — Confidence (Delivery) Analyzer
Measures: Stability and assertiveness of voice
Supports Unicode Tamil text processing
"""
import numpy as np
from typing import Any
from utils import load_audio_array, estimate_pitch_hz, clamp


def analyze_confidence(audio_path: str, norm_text: str) -> tuple[float, dict[str, Any]]:
    """
    MODULE 3: Confidence (Delivery) Analyzer
    Inputs: Audio waveform, Pitch contour, RMS energy, Transcript
    Output: {confidence: score, fillers: count}
    """
    audio = load_audio_array(audio_path, sr=16000)  # float32 mono
    sr = 16000
    if audio.size == 0:
        return 0.0, {"fillers": 0}

    frame_len = int(0.05 * sr)  # 50ms
    hop = frame_len
    rms_vals = []
    pitch_vals = []
    
    for i in range(0, len(audio) - frame_len + 1, hop):
        frame = audio[i : i + frame_len]
        rms = float(np.sqrt(np.mean(frame * frame)))
        rms_vals.append(rms)
        p = estimate_pitch_hz(frame, sr)
        if p is not None:
            pitch_vals.append(p)

    rms_arr = np.array(rms_vals) if rms_vals else np.array([0.0])
    vol_mean = float(np.mean(rms_arr))
    vol_std = float(np.std(rms_arr))
    vol_cv = vol_std / (vol_mean + 1e-6)  # Volume stability (lower = more stable)

    # Detect hesitation markers: volume drop-offs
    drop_ratio = float(np.mean(rms_arr < max(0.01, vol_mean * 0.35)))

    # Pitch variation analysis
    pitch_arr = np.array(pitch_vals) if pitch_vals else np.array([])
    pitch_std = float(np.std(pitch_arr)) if pitch_arr.size else 0.0

    # Count fillers in transcript: "அ…", "ம்…", repeated fillers
    filler_words = {"அ", "ம்", "அப்படின்னா", "அதாவது", "சரி", "என்னனா", "அம்", "அம்மா", "அஅ", "ஆ"}
    tokens = norm_text.split()
    filler_count = sum(1 for t in tokens if t in filler_words)

    # Heuristic scoring: High confidence if RMS stable, few fillers, no frequent drop-offs
    score = 7.0  # Base score
    
    # Volume stability: lower CV = more stable = higher confidence
    if vol_cv < 0.5:
        score += 1.5  # Very stable
    elif vol_cv < 1.0:
        score += 0.5  # Moderately stable
    elif vol_cv > 1.5:
        score -= 1.0  # Unstable
    
    # Few drop-offs = confident delivery
    if drop_ratio < 0.2:
        score += 1.0
    elif drop_ratio > 0.4:
        score -= 1.5  # Many hesitations
    
    # Pitch variation: moderate variation = confident (not monotone, not erratic)
    if pitch_std > 0:
        if 15.0 <= pitch_std <= 50.0:
            score += 0.5  # Good variation
        elif pitch_std < 8.0:
            score -= 1.0  # Too monotone
        elif pitch_std > 70.0:
            score -= 1.0  # Too erratic
    
    # Penalty for fillers
    if filler_count > 5:
        score -= min(2.0, (filler_count - 5) * 0.3)
    
    score = clamp(score, 0.0, 10.0)
    
    return score, {
        "confidence": round(score, 2),
        "fillers": int(filler_count),
        "volumeStability": round(vol_cv, 3),
        "dropOffRatio": round(drop_ratio, 3),
        "pitchVariation": round(pitch_std, 2),
    }

