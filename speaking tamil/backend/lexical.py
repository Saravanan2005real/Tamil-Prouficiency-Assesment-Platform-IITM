# -*- coding: utf-8 -*-
"""
MODULE 4 — Lexical Richness Analyzer (Text-based)
Measures: Variety of words used (no semantics, only stats)
Supports Unicode Tamil text processing
"""
from typing import Any
from utils import clamp


def analyze_lexical(norm_text: str) -> tuple[float, dict[str, Any]]:
    """
    MODULE 4: Lexical Richness Analyzer
    Inputs: Normalized transcript text
    Output: {lexical: score, uniqueWords: count}
    """
    
    tokens = [t for t in norm_text.split() if t]
    total = len(tokens)
    
    if total == 0:
        return 0.0, {"uniqueWords": 0, "typeTokenRatio": 0.0}
    
    unique = len(set(tokens))
    ttr = unique / total  # Type-Token Ratio
    
    # Tamil-specific scoring based on TTR ranges - more lenient thresholds
    if ttr >= 0.40:  # Lowered from 0.55
        score = 9.0  # 8-10 range
    elif 0.30 <= ttr < 0.40:  # Lowered from 0.45
        score = 7.5  # Increased from 6.5
    elif 0.20 <= ttr < 0.30:  # Lowered from 0.35
        score = 6.0  # Increased from 4.5
    else:
        score = 4.5  # Increased from 2.5
    
    score = clamp(score, 0.0, 10.0)
    
    return score, {
        "lexical": round(score, 2),
        "uniqueWords": int(unique),
        "totalWords": int(total),
        "typeTokenRatio": round(ttr, 3),
    }

