# -*- coding: utf-8 -*-
"""
STEP 8: Coherence Evaluation (Rule-based Structure)
Checks whether Hindi speech is well structured and logically connected using phrase matching.
No models — only rule-based patterns.
"""
import json
import os
from typing import Dict, Any, Tuple, List, Optional


def evaluate_coherence(transcript: str, config: Optional[Dict[str, Any]] = None) -> Tuple[float, Dict[str, Any]]:
    """
    Evaluate coherence based on structural elements (intro, connectors, conclusion).
    
    Args:
        transcript: The transcribed text (Hindi)
        config: Optional config dict with phrase lists. If None, loads from hi_config.json
    
    Returns:
        Tuple of (coherence_score (0-10), info_dict)
        info_dict contains: intro_present, connector_count, conclusion_present, etc.
    """
    # 1️⃣ Normalize transcript
    normalized_text = normalize_transcript(transcript)
    
    # 2️⃣ Load phrase lists from config
    if config is None:
        config = load_config()
    
    intro_phrases = config.get("intro", [])
    connectors = config.get("connectors", [])
    conclusion_phrases = config.get("conclusion", [])
    
    # 3️⃣ Check for introduction
    intro_present = check_intro(normalized_text, intro_phrases)
    
    # 4️⃣ Count connectors
    connector_count = count_connectors(normalized_text, connectors)
    
    # 5️⃣ Check for conclusion
    conclusion_present = check_conclusion(normalized_text, conclusion_phrases)
    
    # 6️⃣ Map structure to score
    coherence_score = map_structure_to_score(intro_present, connector_count, conclusion_present)
    
    # 7️⃣ Clamp and return
    coherence_score = max(0.0, min(10.0, coherence_score))
    
    return coherence_score, {
        "coherence_score": round(coherence_score, 2),
        "intro_present": intro_present,
        "connector_count": connector_count,
        "conclusion_present": conclusion_present,
    }


def normalize_transcript(transcript: str) -> str:
    """
    1️⃣ Normalize transcript
    
    Steps:
    - Convert to lowercase
    - Remove extra spaces
    - Keep as one string for phrase search
    """
    if not transcript:
        return ""
    
    # Convert to lowercase
    text = transcript.lower()
    
    # Remove extra spaces (normalize multiple spaces to single space)
    text = " ".join(text.split())
    
    # Strip leading/trailing spaces
    text = text.strip()
    
    return text


def load_config() -> Dict[str, Any]:
    """
    2️⃣ Load phrase lists from hi_config.json
    
    Returns:
        Dictionary with 'intro', 'connectors', and 'conclusion' lists
    """
    # Get the directory where this file is located
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up one level to backend directory
    backend_dir = os.path.dirname(current_dir)
    config_path = os.path.join(backend_dir, "hi_config.json")
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        # Fallback: return default Hindi phrases if config file not found
        return {
            "intro": [
                "मेरे विचार से",
                "मैं सोचता हूं",
                "मैं",
                "मुझे लगता है",
                "पहले",
                "शुरुआत में",
            ],
            "connectors": [
                "क्योंकि",
                "लेकिन",
                "इसलिए",
                "और",
                "फिर",
                "तो",
            ],
            "conclusion": [
                "अंत में",
                "निष्कर्ष में",
                "संक्षेप में",
                "इसलिए",
                "अतः",
            ],
        }
    except json.JSONDecodeError:
        # If JSON is invalid, return default
        return {
            "intro": [],
            "connectors": [],
            "conclusion": [],
        }


def check_intro(text: str, intro_phrases: List[str]) -> bool:
    """
    3️⃣ Check for introduction
    
    If any phrase from intro appears in transcript → intro_present = True
    """
    if not text or not intro_phrases:
        return False
    
    return any(phrase in text for phrase in intro_phrases)


def count_connectors(text: str, connectors: List[str]) -> int:
    """
    4️⃣ Count connectors
    
    Count how many different connector phrases appear in the transcript.
    """
    if not text or not connectors:
        return 0
    
    # Count occurrences of each connector
    count = 0
    for connector in connectors:
        if connector in text:
            count += 1
    
    return count


def check_conclusion(text: str, conclusion_phrases: List[str]) -> bool:
    """
    5️⃣ Check for conclusion
    
    If any phrase from conclusion appears → conclusion_present = True
    """
    if not text or not conclusion_phrases:
        return False
    
    return any(phrase in text for phrase in conclusion_phrases)


def map_structure_to_score(intro_present: bool, connector_count: int, conclusion_present: bool) -> float:
    """
    6️⃣ Map structure to score
    
    Design logic:
    - Intro present → + points
    - At least 2 connectors → + points
    - Conclusion present → + points
    
    Scoring:
    - All three present → high score (8-10)
    - Two present → medium (5-7)
    - One or none → low (2-4)
    
    Also gives partial credit for more connectors.
    """
    points = 0
    
    # Intro present → +1 point
    if intro_present:
        points += 1
    
    # Connectors: at least 2 different connectors → +1 point
    # Also give partial credit: 1 connector = +0.5, 3+ connectors = +1.5
    if connector_count >= 3:
        points += 1.5  # Bonus for many connectors
    elif connector_count >= 2:
        points += 1.0  # Good number of connectors
    elif connector_count >= 1:
        points += 0.5  # Some connectors
    
    # Conclusion present → +1 point
    if conclusion_present:
        points += 1
    
    # Map points to score
    # Max points = 3.5 (intro + 3+ connectors + conclusion)
    if points >= 3.0:
        # All three present (or close) → high score (8-10)
        score = 8.0 + min(2.0, (points - 3.0) * 2.0)
    elif points >= 1.5:
        # Two present → medium (5-7)
        score = 5.0 + ((points - 1.5) / 1.5) * 2.0
    else:
        # One or none → low (2-4)
        score = 2.0 + (points / 1.5) * 2.0
    
    return score

