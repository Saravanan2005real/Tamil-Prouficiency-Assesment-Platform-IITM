# -*- coding: utf-8 -*-
"""
STEP 5: Pronunciation Evaluation (Hybrid)
Estimates how clearly the speaker pronounces words using:
- Whisper's confidence (model proxy)
- Audio stability (rule-based fallback)
"""
import numpy as np
from typing import Optional, Dict, Any, Tuple
import sys
import os

# Add parent directory to path to import audio_utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from audio_utils import compute_rms_stats


def evaluate_pronunciation(
    avg_logprob: Optional[float],
    rms_frames: np.ndarray
) -> Tuple[float, Dict[str, Any]]:
    """
    Evaluate pronunciation clarity using hybrid approach.
    
    Args:
        avg_logprob: Average log probability from Whisper (higher/closer to 0 = better)
        rms_frames: Array of RMS energy values per frame (from audio_utils)
    
    Returns:
        Tuple of (pronunciation_score (0-10), info_dict)
        info_dict contains: avg_logprob, rms_mean, rms_cv, method, etc.
    """
    # 2️⃣ Compute RMS stability from audio
    rms_stats = compute_rms_stats(rms_frames)
    rms_mean = rms_stats["mean_rms"]
    rms_std = rms_stats["std_rms"]
    rms_cv = rms_stats["cv_rms"]
    
    # 1️⃣ Use Whisper avg_logprob as primary signal
    if avg_logprob is not None:
        # Primary method: use Whisper confidence
        score = map_logprob_to_score(avg_logprob)
        method = "whisper_primary"
        
        # 3️⃣ Combine both signals - adjust using RMS
        score = adjust_score_with_rms(score, rms_mean, rms_cv)
    else:
        # Fallback: use RMS stability if avg_logprob is missing/unreliable
        score = map_rms_to_score(rms_mean, rms_cv)
        method = "rms_fallback"
    
    # 4️⃣ Clamp to 0-10
    score = max(0.0, min(10.0, score))
    
    # 5️⃣ Return the score
    return score, {
        "pronunciation_score": round(score, 2),
        "avg_logprob": round(avg_logprob, 3) if avg_logprob is not None else None,
        "rms_mean": round(rms_mean, 4),
        "rms_std": round(rms_std, 4),
        "rms_cv": round(rms_cv, 3),
        "method": method,
    }


def map_logprob_to_score(avg_logprob: float) -> float:
    """
    1️⃣ Map avg_logprob to base score
    
    Define ranges:
    - avg_logprob > -0.3 → very good (8-10)
    - -0.6 to -0.3 → average (5-7)
    - < -0.6 → poor (2-4)
    
    Higher logprob (closer to 0) = better match = clearer speech.
    """
    if avg_logprob > -0.3:
        # Very good: 8-10 range
        # Map linearly: -0.3 → 10, 0 → 10 (cap at 10)
        score = 10.0
    elif avg_logprob >= -0.6:
        # Average: 5-7 range
        # Map linearly: -0.3 → 7, -0.6 → 5
        score = 5.0 + ((avg_logprob + 0.6) / 0.3) * 2.0
    else:
        # Poor: 2-4 range
        # Map linearly: -0.6 → 4, -1.5 → 2 (or lower)
        if avg_logprob >= -1.5:
            score = 2.0 + ((avg_logprob + 1.5) / 0.9) * 2.0
        else:
            # Very poor: < -1.5
            score = 2.0
    
    return score


def adjust_score_with_rms(base_score: float, rms_mean: float, rms_cv: float) -> float:
    """
    3️⃣ Adjust score using RMS stability
    
    Interpretation:
    - Very low mean RMS → mumbling → penalize
    - CV < ~0.4 → stable → good (no penalty, maybe small bonus)
    - CV > ~0.6 → unstable → penalize
    
    Args:
        base_score: Score from avg_logprob
        rms_mean: Mean RMS value
        rms_cv: Coefficient of variation (std / mean)
    
    Returns:
        Adjusted score
    """
    score = base_score
    
    # Penalty for very low mean RMS (mumbling)
    if rms_mean < 0.01:
        score -= 2.0  # Very quiet/mumbling
    elif rms_mean < 0.02:
        score -= 1.0  # Quiet
    
    # Adjust based on CV (stability)
    if rms_cv < 0.4:
        # Stable loudness → good articulation
        # Small bonus (but don't exceed 10)
        score = min(10.0, score + 0.5)
    elif rms_cv > 0.6:
        # Unstable loudness → unclear articulation
        if rms_cv > 1.0:
            score -= 1.5  # Very unstable
        else:
            score -= 0.8  # Moderately unstable
    
    return score


def map_rms_to_score(rms_mean: float, rms_cv: float) -> float:
    """
    Fallback: Map RMS stability to score when avg_logprob is unavailable.
    
    Args:
        rms_mean: Mean RMS value
        rms_cv: Coefficient of variation
    
    Returns:
        Score (0-10)
    """
    # Start with base score based on mean RMS
    if rms_mean >= 0.03:
        base_score = 7.0  # Good volume
    elif rms_mean >= 0.02:
        base_score = 5.0  # Moderate volume
    elif rms_mean >= 0.01:
        base_score = 3.0  # Low volume
    else:
        base_score = 1.0  # Very low volume (mumbling)
    
    # Adjust based on CV
    if rms_cv < 0.4:
        # Stable → bonus
        base_score = min(10.0, base_score + 1.5)
    elif rms_cv > 0.6:
        # Unstable → penalty
        if rms_cv > 1.0:
            base_score -= 2.0
        else:
            base_score -= 1.0
    
    return max(0.0, base_score)

