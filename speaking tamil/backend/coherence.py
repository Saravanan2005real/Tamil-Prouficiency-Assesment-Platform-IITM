# -*- coding: utf-8 -*-
"""
MODULE 5 — Structural Coherence Analyzer (Rule-based, No LLM)
Measures: Whether speech has structure
Supports Unicode Tamil text processing
"""
from typing import Any
from utils import clamp


def analyze_coherence(norm_text: str) -> tuple[float, dict[str, Any]]:
    """
    MODULE 5: Structural Coherence Analyzer
    Inputs: Normalized transcript text
    Output: {coherence: score, intro: bool, connectors: bool, conclusion: bool}
    """
    if not norm_text or not norm_text.strip():
        return 0.0, {"intro": False, "connectors": False, "conclusion": False}
    
    text_lower = norm_text.lower()
    
    # Opening phrases (intro detection)
    opening_phrases = [
        "என்னுடைய", "நான் நினைப்பது", "நான்", "எனக்கு", 
        "முதலில்", "தொடக்கத்தில்", "ஆரம்பத்தில்"
    ]
    has_intro = any(op in text_lower for op in opening_phrases)
    
    # Connectors
    connectors = [
        "அதனால்", "மேலும்", "எடுத்துக்காட்டாக", "முதலில்", 
        "அடுத்து", "பிறகு", "கடைசியாக", "என்பதால்", "ஆகவே",
        "மற்றும்", "அல்லது", "ஆனால்", "எனவே"
    ]
    connector_hits = sum(1 for c in connectors if c in text_lower)
    has_connectors = connector_hits > 0
    
    # Ending phrases (conclusion detection)
    ending_phrases = [
        "முடிவில்", "இதனால்", "கடைசியாக", "சுருக்கமாக", 
        "மொத்தத்தில்", "எனவே", "ஆகவே"
    ]
    has_conclusion = any(ep in text_lower for ep in ending_phrases)
    
    # Count points: Each = +1
    points = 0
    if has_intro:
        points += 1
    if has_connectors:
        points += 1
    if has_conclusion:
        points += 1
    
    # Scoring based on points - more lenient
    if points == 3:
        score = 9.5  # Increased from 9.0
    elif points == 2:
        score = 8.0  # Increased from 6.5
    elif points == 1:
        score = 6.5  # Increased from 4.5
    else:
        score = 5.0  # Increased from 2.5 (even with 0 points, give decent score)
    
    score = clamp(score, 0.0, 10.0)
    
    return score, {
        "coherence": round(score, 2),
        "intro": has_intro,
        "connectors": has_connectors,
        "conclusion": has_conclusion,
        "connectorCount": int(connector_hits),
    }

