# -*- coding: utf-8 -*-
"""
FINAL AGGREGATION: Compute all 5 modules and aggregate with specified weights
Supports Unicode Tamil text processing
"""
from typing import Optional, Any
from fluency import analyze_fluency
from pronunciation import analyze_pronunciation
from confidence import analyze_confidence
from lexical import analyze_lexical
from coherence import analyze_coherence
from utils import audio_duration_sec_from_path, estimate_speech_activity_ratio, clamp


def compute_step5(audio_path: str, norm_text: str, segments: list[dict[str, Any]], duration: Optional[float]):
    """
    FINAL AGGREGATION: Compute all 5 modules and aggregate with specified weights
    Weights: 0.25 * fluency + 0.20 * pronunciation + 0.20 * confidence + 0.20 * coherence + 0.15 * lexical
    """
    # If duration isn't provided, infer duration from audio file.
    if duration is None or float(duration) <= 0.0:
        duration = audio_duration_sec_from_path(audio_path)

    # MODULE 1: Fluency & Pace Analyzer
    if segments:
        fluency, fluency_details = analyze_fluency(segments, norm_text, duration)
    else:
        # Fallback: estimate from audio if no segments available
        vad = estimate_speech_activity_ratio(audio_path)
        # Rough WPM estimate
        words = [w for w in norm_text.split() if w]
        word_count = len(words)
        total_dur = float(vad["totalDuration"])
        duration_minutes = total_dur / 60.0 if total_dur > 0 else 0.001
        wpm = word_count / duration_minutes if duration_minutes > 0 else 0.0
        
        # Use same scoring logic
        if 110 <= wpm <= 150:
            fluency = 9.5
        elif 90 <= wpm < 110 or 150 < wpm <= 170:
            fluency = 7.5
        elif 70 <= wpm < 90 or 170 < wpm <= 190:
            fluency = 5.5
        else:
            fluency = 3.5
        fluency = clamp(fluency, 0.0, 10.0)
        
        fluency_details = {
            "wpm": round(wpm, 1),
            "longPauses": 0,
            "method": "audio_fallback",
        }

    # MODULE 2: Pronunciation Clarity Analyzer
    pron, pron_details = analyze_pronunciation(segments, audio_path)

    # MODULE 3: Confidence (Delivery) Analyzer
    conf, conf_details = analyze_confidence(audio_path, norm_text)

    # MODULE 4: Lexical Richness Analyzer
    lex, lex_details = analyze_lexical(norm_text)

    # MODULE 5: Structural Coherence Analyzer
    coh, coh_details = analyze_coherence(norm_text)

    # FINAL AGGREGATION with specified weights
    overall = (
        0.25 * fluency +
        0.20 * pron +
        0.20 * conf +
        0.20 * coh +
        0.15 * lex
    )
    overall = round(overall, 2)

    # Convert scores (0-10) to percentages (0-100%)
    fluency_percent = round(fluency * 10.0, 2)
    pron_percent = round(pron * 10.0, 2)
    conf_percent = round(conf * 10.0, 2)
    coh_percent = round(coh * 10.0, 2)
    lex_percent = round(lex * 10.0, 2)
    overall_percent = round(overall * 10.0, 2)

    # Import Step5Scores from main to avoid circular imports (import at function level)
    import main
    Step5Scores = main.Step5Scores

    return Step5Scores(
        fluency=round(fluency, 2),
        pronunciation=round(pron, 2),
        coherence=round(coh, 2),
        lexical=round(lex, 2),
        confidence=round(conf, 2),
        overall=overall,
        fluencyPercent=fluency_percent,
        pronunciationPercent=pron_percent,
        coherencePercent=coh_percent,
        lexicalPercent=lex_percent,
        confidencePercent=conf_percent,
        overallPercent=overall_percent,
        details={
            "fluency": fluency_details,
            "pronunciation": pron_details,
            "coherence": coh_details,
            "lexical": lex_details,
            "confidence": conf_details,
        },
    )

