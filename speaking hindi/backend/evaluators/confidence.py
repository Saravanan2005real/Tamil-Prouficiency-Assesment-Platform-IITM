# -*- coding: utf-8 -*-
"""
STEP 6: Confidence Evaluation
Estimates how confident the speaker sounds using:
- Volume stability (from RMS)
- Pitch variation
- Filler word counting (Hindi)
"""
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
import sys
import os

# Add parent directory to path to import audio_utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from audio_utils import compute_rms_stats, compute_pitch_stats


def evaluate_confidence(
    rms_frames: np.ndarray,
    pitch_frames: np.ndarray,
    transcript: str,
    fillers: Optional[List[str]] = None
) -> Tuple[float, Dict[str, Any]]:
    """
    Evaluate confidence based on volume stability, pitch variation, and filler words.
    
    Args:
        rms_frames: Array of RMS energy values per frame
        pitch_frames: Array of pitch values (Hz), with unvoiced frames filtered out
        transcript: The transcribed text (Hindi)
        fillers: Optional custom list of filler words (defaults to Hindi fillers)
    
    Returns:
        Tuple of (confidence_score (0-10), info_dict)
        info_dict contains: rms_cv, pitch_std, filler_count, etc.
    """
    # Default Hindi filler words
    if fillers is None:
        fillers = ["उह", "अ", "हम्म", "मतलब", "तो", "देखिए", "यानी", "वो", "जैसे"]
    
    # 1️⃣ Volume stability (from RMS)
    rms_stats = compute_rms_stats(rms_frames)
    rms_mean = rms_stats["mean_rms"]
    rms_std = rms_stats["std_rms"]
    rms_cv = rms_stats["cv_rms"]
    volume_subscore = compute_volume_subscore(rms_mean, rms_cv)
    
    # 2️⃣ Pitch variation
    pitch_stats = compute_pitch_stats(pitch_frames)
    pitch_mean = pitch_stats["mean_pitch"]
    pitch_std = pitch_stats["std_pitch"]
    pitch_cv = pitch_stats["cv_pitch"]
    pitch_subscore = compute_pitch_subscore(pitch_std)
    
    # 3️⃣ Filler word counting (Hindi)
    filler_count = count_fillers(transcript, fillers)
    filler_subscore = compute_filler_subscore(filler_count)
    
    # 4️⃣ Combine into confidence score
    # Average the three sub-scores
    confidence_score = (volume_subscore + pitch_subscore + filler_subscore) / 3.0
    
    # 5️⃣ Clamp to 0-10
    confidence_score = max(0.0, min(10.0, confidence_score))
    
    # 6️⃣ Return score
    return confidence_score, {
        "confidence_score": round(confidence_score, 2),
        "volume_subscore": round(volume_subscore, 2),
        "pitch_subscore": round(pitch_subscore, 2),
        "filler_subscore": round(filler_subscore, 2),
        "rms_mean": round(rms_mean, 4),
        "rms_std": round(rms_std, 4),
        "rms_cv": round(rms_cv, 3),
        "pitch_mean": round(pitch_mean, 1) if pitch_mean > 0 else 0.0,
        "pitch_std": round(pitch_std, 1) if pitch_std > 0 else 0.0,
        "pitch_cv": round(pitch_cv, 3) if pitch_cv > 0 else 0.0,
        "filler_count": filler_count,
    }


def compute_volume_subscore(rms_mean: float, rms_cv: float) -> float:
    """
    1️⃣ Volume stability sub-score
    
    Interpretation:
    - Very low mean → weak voice → less confident
    - Very high CV → shaky loudness → less confident
    - Moderate mean + low CV → confident
    
    Ranges:
    - CV < 0.4 → good
    - 0.4-0.6 → ok
    - > 0.6 → poor
    """
    # Start with base score
    score = 10.0
    
    # Penalty for very low mean RMS (weak voice)
    if rms_mean < 0.01:
        score -= 3.0  # Very weak
    elif rms_mean < 0.02:
        score -= 1.5  # Weak
    
    # Penalty/adjustment based on CV (stability)
    if rms_cv < 0.4:
        # Good stability → no penalty (or small bonus)
        score = min(10.0, score + 0.5)
    elif 0.4 <= rms_cv <= 0.6:
        # Ok stability → small penalty
        score -= 1.0
    else:
        # Poor stability (CV > 0.6) → bigger penalty
        if rms_cv > 1.0:
            score -= 3.0  # Very shaky
        else:
            score -= 2.0  # Shaky
    
    return max(0.0, score)


def compute_pitch_subscore(pitch_std: float) -> float:
    """
    2️⃣ Pitch variation sub-score
    
    Interpretation:
    - Very low std → monotone → less engaging (less confident)
    - Very high std → nervous
    - Moderate std → confident
    
    Define moderate range: 15-50 Hz std is good for confident speech
    """
    # Start with base score
    score = 10.0
    
    if pitch_std == 0.0:
        # No pitch variation (monotone) → less engaging
        score = 5.0
    elif 15.0 <= pitch_std <= 50.0:
        # Moderate variation → confident
        # No penalty, maybe small bonus
        score = min(10.0, score + 0.5)
    elif 8.0 <= pitch_std < 15.0:
        # Low variation → somewhat monotone
        score -= 1.5
    elif pitch_std < 8.0:
        # Very low variation → monotone
        score -= 2.5
    elif 50.0 < pitch_std <= 70.0:
        # High variation → somewhat nervous
        score -= 1.0
    else:
        # Very high variation (pitch_std > 70) → nervous
        score -= 2.5
    
    return max(0.0, score)


def count_fillers(transcript: str, fillers: List[str]) -> int:
    """
    3️⃣ Count filler words in transcript
    
    Args:
        transcript: The transcribed text (Hindi)
        fillers: List of filler words to count
    
    Returns:
        Total count of filler words
    """
    if not transcript:
        return 0
    
    # Normalize transcript: lowercase and split into words
    words = transcript.lower().split()
    
    # Count occurrences of each filler
    filler_count = 0
    for filler in fillers:
        filler_count += words.count(filler.lower())
    
    return filler_count


def compute_filler_subscore(filler_count: int) -> float:
    """
    3️⃣ Filler word sub-score
    
    Interpretation:
    - 0-1 → good
    - 2-4 → ok
    - > 4 → poor
    """
    # Start with base score
    score = 10.0
    
    if filler_count <= 1:
        # Good: no penalty
        pass
    elif 2 <= filler_count <= 4:
        # Ok: small penalty
        score -= 1.5
    else:
        # Poor: bigger penalty
        # Penalty increases with more fillers
        penalty = 2.0 + min(3.0, (filler_count - 4) * 0.5)
        score -= penalty
    
    return max(0.0, score)

