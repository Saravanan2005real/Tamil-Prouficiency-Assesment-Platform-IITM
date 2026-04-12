"""
Question generation module for creating questions from transcripts.
"""

import json

def generate_questions(transcript, level):
    """
    Generate questions from transcript for a specific level.
    
    Args:
        transcript: Transcript text (str)
        level: Level number (int: 1, 2, or 3)
    
    Returns:
        list: List of question dictionaries
    """
    print(f"   📝 Generating questions for Level {level}...")
    
    # TODO: Implement actual question generation logic
    # This could use:
    # - NLP models to extract key information
    # - Rule-based templates
    # - LLM-based generation
    
    # Placeholder implementation based on level
    questions = []
    
    if level == 1:
        questions = [
            {
                "id": "q1",
                "type": "fill-missing-word",
                "question": "Fill the missing word / விடுபட்ட சொல்லை நிரப்பவும்",
                "questionTa": "விடுபட்ட சொல்லை நிரப்பவும்",
                "audioContext": "The teacher said: \"Today we will learn about ___\"",
                "correctAnswer": "animals",
                "alternatives": ["animals", "animal", "creatures"]
            },
            {
                "id": "q2",
                "type": "identify-topic",
                "question": "What is the main topic? (1-2 words) / முக்கிய தலைப்பு என்ன?",
                "questionTa": "முக்கிய தலைப்பு என்ன?",
                "correctAnswer": "classroom lesson",
                "alternatives": ["classroom lesson", "lesson", "teaching", "class", "school"]
            }
        ]
    elif level == 2:
        questions = [
            {
                "id": "q1",
                "type": "identify-speaker",
                "question": "Who said \"Let's go to the market\"? (1-2 words) / \"சந்தைக்கு போவோம்\" என்று யார் சொன்னார்?",
                "questionTa": "\"சந்தைக்கு போவோம்\" என்று யார் சொன்னார்?",
                "correctAnswer": "Ravi",
                "alternatives": ["Ravi", "ravi", "Ravi said"]
            }
        ]
    else:  # level == 3
        # Note: Q1 (emotion-mcq) has been removed from Level 3
        # Level 3 questions are now loaded from level3_scene_tamil.json
        # This is a placeholder - actual questions come from JSON files
        questions = []
    
    print(f"   ✅ Generated {len(questions)} questions")
    return questions
