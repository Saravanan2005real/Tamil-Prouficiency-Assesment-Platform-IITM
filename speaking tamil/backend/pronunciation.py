# -*- coding: utf-8 -*-
"""
MODULE 2 — Pronunciation Clarity Analyzer
Measures: How clearly words are articulated (NOT accent)
Supports Unicode Tamil text processing
"""
import numpy as np
from typing import Optional, Any
from utils import load_audio_array, clamp


def analyze_pronunciation(segments: list[dict[str, Any]], audio_path: Optional[str] = None) -> tuple[float, dict[str, Any]]:
    """
    MODULE 2: Pronunciation Clarity Analyzer
    Inputs: Whisper word confidence, Audio RMS stability
    Output: {pronunciation: score, avg_conf: value}
    """
    segs = segments or []
    
    # Extract word-level confidence from Whisper segments
    # Whisper provides avg_logprob per segment, convert to confidence
    logprobs = [float(s["avg_logprob"]) for s in segs if "avg_logprob" in s]
    
    if not logprobs:
        # Fallback: use audio RMS stability if Whisper confidence unavailable
        if audio_path:
            return analyze_pronunciation_from_audio(audio_path)
        return 0.0, {"avg_conf": 0.0, "method": "whisper_unavailable"}
    
    # Convert logprobs to confidence scores (0-1 range)
    # avg_logprob typically ranges from -0.2 (high confidence) to -2.0 (low confidence)
    confidences = []
    for lp in logprobs:
        # Map logprob to confidence: higher logprob = higher confidence
        # Normalize: -0.2 -> ~0.95, -1.0 -> ~0.73, -2.0 -> ~0.27
        conf = 1.0 / (1.0 + np.exp(-(lp + 1.0)))
        confidences.append(conf)
    
    avg_conf = float(np.mean(confidences))
    
    # Calculate low-confidence ratio (% of words with conf < 0.6)
    low_conf_count = sum(1 for c in confidences if c < 0.6)
    low_conf_ratio = (low_conf_count / len(confidences)) * 100.0 if confidences else 0.0
    
    # Scoring based on avg_conf ranges
    if avg_conf >= 0.85:
        score = 9.5  # 9-10 range
    elif 0.75 <= avg_conf < 0.85:
        score = 7.5  # 7-8 range
    elif 0.65 <= avg_conf < 0.75:
        score = 5.5  # 5-6 range
    else:
        score = 3.5  # 3-4 range
    
    # Penalty if low_conf_ratio > 30%
    if low_conf_ratio > 30.0:
        penalty = min(2.0, (low_conf_ratio - 30.0) / 10.0)
        score -= penalty
    
    score = clamp(score, 0.0, 10.0)
    
    return score, {
        "pronunciation": round(score, 2),
        "avg_conf": round(avg_conf, 3),
        "lowConfRatio": round(low_conf_ratio, 1),
    }


def analyze_pronunciation_from_audio(audio_path: str) -> tuple[float, dict[str, Any]]:
    """Fallback pronunciation analysis using audio RMS stability"""
    audio = load_audio_array(audio_path, sr=16000)
    sr = 16000
    if audio.size == 0:
        return 0.0, {"avg_conf": 0.0, "method": "audio_proxy"}
    
    frame_len = int(0.05 * sr)  # 50ms
    hop = frame_len
    rms_vals = []
    for i in range(0, len(audio) - frame_len + 1, hop):
        frame = audio[i : i + frame_len]
        rms_vals.append(float(np.sqrt(np.mean(frame * frame))))
    
    rms_arr = np.array(rms_vals) if rms_vals else np.array([0.0])
    mean_rms = float(np.mean(rms_arr))
    std_rms = float(np.std(rms_arr))
    cv = std_rms / (mean_rms + 1e-6)  # Coefficient of variation
    
    # Signal clarity: lower CV = more stable = clearer articulation
    # Map CV to confidence proxy (inverse relationship)
    clarity_proxy = 1.0 / (1.0 + cv)
    clarity_proxy = clamp(clarity_proxy, 0.0, 1.0)
    
    # Use same scoring as confidence-based method
    if clarity_proxy >= 0.85:
        score = 9.5
    elif 0.75 <= clarity_proxy < 0.85:
        score = 7.5
    elif 0.65 <= clarity_proxy < 0.75:
        score = 5.5
    else:
        score = 3.5
    
    score = clamp(score, 0.0, 10.0)
    
    return score, {
        "pronunciation": round(score, 2),
        "avg_conf": round(clarity_proxy, 3),
        "method": "audio_proxy",
        "volumeCV": round(cv, 3),
    }

