# -*- coding: utf-8 -*-
"""
STEP 7: Lexical Richness (Vocabulary Diversity)
Measures how rich and varied the speaker's Hindi vocabulary is using Type-Token Ratio (TTR).
Pure statistics, no model.
"""
import re
from typing import Dict, Any, Tuple, List


def evaluate_lexical(transcript: str) -> Tuple[float, Dict[str, Any]]:
    """
    Evaluate lexical richness based on Type-Token Ratio (TTR).
    
    Args:
        transcript: The transcribed text (Hindi)
    
    Returns:
        Tuple of (lexical_score (0-10), info_dict)
        info_dict contains: ttr, total_words, unique_words, etc.
    """
    # 1️⃣ Clean and tokenize Hindi text
    words = clean_and_tokenize(transcript)
    
    # 2️⃣ Count tokens and types
    total_words = len(words)
    unique_words = len(set(words))
    
    # If total words are very few, treat as low lexical richness
    if total_words < 10:
        lexical_score = 2.0  # Very low score for insufficient content
        ttr = unique_words / total_words if total_words > 0 else 0.0
    else:
        # 3️⃣ Compute TTR
        ttr = unique_words / total_words if total_words > 0 else 0.0
        
        # 4️⃣ Map TTR to score
        lexical_score = map_ttr_to_score(ttr)
    
    # 5️⃣ Clamp and return
    lexical_score = max(0.0, min(10.0, lexical_score))
    
    return lexical_score, {
        "lexical_score": round(lexical_score, 2),
        "ttr": round(ttr, 3),
        "total_words": total_words,
        "unique_words": unique_words,
    }


def clean_and_tokenize(transcript: str) -> List[str]:
    """
    1️⃣ Clean and tokenize Hindi text
    
    Steps:
    - Convert to lowercase
    - Remove punctuation/special characters
    - Split by spaces
    - Optionally remove very common stopwords (optional)
    
    Returns:
        List of cleaned words
    """
    if not transcript:
        return []
    
    # Convert to lowercase
    text = transcript.lower()
    
    # Remove punctuation and special characters, keep Hindi Unicode characters, spaces, and basic alphanumeric
    # Hindi Unicode range: \u0900-\u097F (Devanagari script)
    text = re.sub(r"[^\u0900-\u097Fa-z0-9\s]", " ", text)
    
    # Normalize spaces (replace multiple spaces with single space)
    text = re.sub(r"\s+", " ", text)
    
    # Strip leading/trailing spaces
    text = text.strip()
    
    # Split by space and filter out empty strings
    words = [w for w in text.split() if w]
    
    # Optional: Remove very common Hindi stopwords
    # Common Hindi stopwords: है, के, की, और, में, से, को, का, ने, पर, etc.
    common_stopwords = {
        "है", "के", "की", "और", "में", "से", "को", "का", "ने", "पर",
        "यह", "वह", "इस", "उस", "तो", "भी", "ही", "कि", "जो", "जैसे"
    }
    
    # Filter out stopwords (optional - can be enabled/disabled)
    # For now, keeping stopwords to get more accurate TTR
    # words = [w for w in words if w not in common_stopwords]
    
    return words


def map_ttr_to_score(ttr: float) -> float:
    """
    4️⃣ Map TTR to score
    
    Define ranges:
    - TTR > 0.50 → rich → score ~8-10
    - 0.35 - 0.50 → average → score ~5-7
    - < 0.35 → poor → score ~2-4
    
    Linearly map inside ranges.
    """
    if ttr > 0.50:
        # Rich vocabulary: 8-10 range
        # Map linearly: 0.50 → 8, 1.0 → 10
        if ttr >= 1.0:
            score = 10.0
        else:
            score = 8.0 + ((ttr - 0.50) / 0.50) * 2.0
    elif ttr >= 0.35:
        # Average vocabulary: 5-7 range
        # Map linearly: 0.35 → 5, 0.50 → 7
        score = 5.0 + ((ttr - 0.35) / 0.15) * 2.0
    else:
        # Poor vocabulary: 2-4 range
        # Map linearly: 0.0 → 2, 0.35 → 4
        if ttr <= 0.0:
            score = 2.0
        else:
            score = 2.0 + (ttr / 0.35) * 2.0
    
    return score

