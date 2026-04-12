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
    
    # Tamil-specific scoring based on TTR ranges
    if ttr >= 0.55:
        score = 9.0  # 8-10 range
    elif 0.45 <= ttr < 0.55:
        score = 6.5  # 6-7 range
    elif 0.35 <= ttr < 0.45:
        score = 4.5  # 4-5 range
    else:
        score = 2.5  # 2-3 range
    
    score = clamp(score, 0.0, 10.0)
    
    return score, {
        "lexical": round(score, 2),
        "uniqueWords": int(unique),
        "totalWords": int(total),
        "typeTokenRatio": round(ttr, 3),
    }

