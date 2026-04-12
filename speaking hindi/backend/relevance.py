# -*- coding: utf-8 -*-
"""
STEP 9: Relevance Gate (Answer vs Question)
Checks if the spoken answer is actually related to the given question.
Rule-based only - no models.
"""
import re
from typing import Set


def is_relevant(answer_text: str, question_text: str) -> bool:
    """
    Check if answer is relevant to the question using keyword overlap.
    
    Args:
        answer_text: The transcribed answer text (Hindi)
        question_text: The question text (Hindi)
    
    Returns:
        True if relevant (proceed with scoring), False if not relevant
    """
    # 1️⃣ Normalize both texts
    normalized_answer = normalize_text(answer_text)
    normalized_question = normalize_text(question_text)
    
    # 2️⃣ Tokenize into keywords
    answer_keywords = extract_keywords(normalized_answer)
    question_keywords = extract_keywords(normalized_question)
    
    # 3️⃣ Compute keyword overlap
    overlap_count, overlap_ratio = compute_overlap(answer_keywords, question_keywords)
    
    # 4️⃣ Decide relevance threshold
    relevant = check_relevance_threshold(overlap_count, overlap_ratio)
    
    # 5️⃣ Return result
    return relevant


def normalize_text(text: str) -> str:
    """
    1️⃣ Normalize text
    
    Steps:
    - Lowercase
    - Remove punctuation
    - Normalize spaces
    """
    if not text:
        return ""
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove punctuation and special characters, keep Hindi Unicode characters, spaces, and basic alphanumeric
    # Hindi Unicode range: \u0900-\u097F (Devanagari script)
    text = re.sub(r"[^\u0900-\u097Fa-z0-9\s]", " ", text)
    
    # Normalize spaces (replace multiple spaces with single space)
    text = re.sub(r"\s+", " ", text)
    
    # Strip leading/trailing spaces
    text = text.strip()
    
    return text


def extract_keywords(text: str) -> Set[str]:
    """
    2️⃣ Tokenize into keywords
    
    Steps:
    - Split into words
    - Optionally remove very common Hindi stopwords
    """
    if not text:
        return set()
    
    # Split into words
    words = text.split()
    
    # Remove very common Hindi stopwords
    # Common stopwords: है, के, की, और, में, से, को, का, ने, पर, etc.
    common_stopwords = {
        "है", "के", "की", "और", "में", "से", "को", "का", "ने", "पर",
        "यह", "वह", "इस", "उस", "तो", "भी", "ही", "कि", "जो", "जैसे",
        "एक", "दो", "तीन", "क्या", "कैसे", "कब", "कहां", "कौन"
    }
    
    # Filter out stopwords and empty strings
    keywords = {w for w in words if w and w not in common_stopwords}
    
    return keywords


def compute_overlap(answer_keywords: Set[str], question_keywords: Set[str]) -> tuple[int, float]:
    """
    3️⃣ Compute keyword overlap
    
    Find intersection between answer_words and question_words.
    Count how many common words and compute overlap ratio.
    
    Returns:
        Tuple of (overlap_count, overlap_ratio)
    """
    if not question_keywords:
        return 0, 0.0
    
    # Find intersection
    common_words = answer_keywords.intersection(question_keywords)
    overlap_count = len(common_words)
    
    # Compute overlap ratio: common_words / question_keywords
    overlap_ratio = overlap_count / len(question_keywords) if question_keywords else 0.0
    
    return overlap_count, overlap_ratio


def check_relevance_threshold(overlap_count: int, overlap_ratio: float) -> bool:
    """
    4️⃣ Decide relevance threshold
    
    Rule:
    - If overlap_count >= 2 OR overlap_ratio >= 0.2 → relevant
    - Else → not relevant
    
    Args:
        overlap_count: Number of common keywords
        overlap_ratio: Ratio of common keywords to question keywords
    
    Returns:
        True if relevant, False otherwise
    """
    # Threshold: at least 2 common keywords OR at least 20% overlap
    if overlap_count >= 2 or overlap_ratio >= 0.2:
        return True
    else:
        return False

