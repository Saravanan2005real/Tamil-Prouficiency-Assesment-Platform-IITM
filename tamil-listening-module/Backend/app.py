"""
Flask application for Tamil Listening Test.
Level submissions only validate attempts and store raw answers.
No correctness, accuracy, precision, or relevance calculations during level submissions.
Evaluation is postponed until final submission after Level 3.
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
import base64
import tempfile
import subprocess
import shutil
from evaluator import evaluate_level1, evaluate_level2, evaluate_level3

app = Flask(__name__, static_folder='..', static_url_path='')
CORS(app, resources={r"/*": {"origins": "*"}})

# Get the Backend directory path
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))

# Whisper model cache
whisper_model = None

# FFmpeg path cache
_ffmpeg_path = None


def find_ffmpeg():
    """Find ffmpeg executable, with fallback to imageio-ffmpeg."""
    global _ffmpeg_path
    
    if _ffmpeg_path is not None:
        return _ffmpeg_path
    
    # Try system ffmpeg first
    ffmpeg_candidates = ['ffmpeg', 'ffmpeg.exe']
    for candidate in ffmpeg_candidates:
        if shutil.which(candidate):
            _ffmpeg_path = candidate
            print(f"✅ Found system ffmpeg: {_ffmpeg_path}")
            return _ffmpeg_path
    
    # Fallback to imageio-ffmpeg
    try:
        import imageio_ffmpeg
        _ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        print(f"✅ Using bundled ffmpeg from imageio-ffmpeg: {_ffmpeg_path}")
        return _ffmpeg_path
    except ImportError:
        print("⚠️ imageio-ffmpeg not installed. Install with: pip install imageio-ffmpeg")
        return None
    except Exception as e:
        print(f"⚠️ Error getting imageio-ffmpeg: {e}")
        return None


# Storage for raw answers (in-memory for now; can be replaced with database)
# Structure: { level_1: { q1: answer, q2: answer, ... }, level_2: {...}, level_3: {...} }
raw_answers_store = {
    "level_1": None,
    "level_2": None,
    "level_3": None
}

# Helper function to check if a value is considered "attempted" (non-empty)
def is_attempted(value):
    """
    Check if an answer is considered attempted (non-empty input).
    
    Args:
        value: The answer value (can be str, int, list, dict, None)
    
    Returns:
        bool: True if the value represents an attempt, False otherwise
    """
    if value is None:
        return False
    
    if isinstance(value, str):
        # String: check if it's non-empty after stripping whitespace
        return len(value.strip()) > 0
    
    if isinstance(value, (int, float)):
        # Numbers: always considered attempted (even 0)
        return True
    
    if isinstance(value, list):
        # List: check if it has at least one element
        return len(value) > 0
    
    if isinstance(value, dict):
        # Dictionary: check if it has at least one key-value pair
        return len(value) > 0
    
    # For other types, consider them attempted if they're not None
    return True


def check_level_attempts(level, responses):
    """
    Check if all questions for a level have been attempted.
    
    Args:
        level: Level number (1, 2, or 3)
        responses: The responses dict from the request
    
    Returns:
        tuple: (all_attempted: bool, missing_questions: list)
            - all_attempted: True if all questions are attempted, False otherwise
            - missing_questions: List of question numbers (as strings) that are not attempted
    """
    missing_questions = []
    
    if level == 1:
        # Level 1: Questions are stored directly as "1", "2", "3", "4"
        expected_questions = ["1", "2", "3", "4"]
        for q_id in expected_questions:
            q_answer = responses.get(q_id)
            if not is_attempted(q_answer):
                missing_questions.append(q_id)
    
    elif level == 2:
        # Level 2: Questions are stored in responses.level2Answers
        level2Answers = responses.get("level2Answers", {})
        
        # Question 1: identify_speaker
        if not is_attempted(level2Answers.get("identify_speaker")):
            missing_questions.append("1")
        
        # Question 2: dialogue_ordering
        dialogue_ordering = level2Answers.get("dialogue_ordering")
        if not is_attempted(dialogue_ordering):
            missing_questions.append("2")
        
        # Question 3: main_problem_discussed
        if not is_attempted(level2Answers.get("main_problem_discussed")):
            missing_questions.append("3")
        
        # Question 4: match_speaker_role
        match_speaker_role = level2Answers.get("match_speaker_role")
        if not is_attempted(match_speaker_role):
            missing_questions.append("4")
    
    elif level == 3:
        # Level 3: Questions are stored in responses.level3Answers
        level3Answers = responses.get("level3Answers", {})
        
        # Remove identify_emotion (Q1) if it exists (defensive check)
        if "identify_emotion" in level3Answers:
            level3Answers.pop("identify_emotion", None)
        
        # Question 1: next_action (ID "1")
        if not is_attempted(level3Answers.get("next_action")):
            missing_questions.append("1")
        
        # Question 2: fill_missing_phrase (ID "2")
        if not is_attempted(level3Answers.get("fill_missing_phrase")):
            missing_questions.append("2")
        
        # Question 3: long_answer with ID "3"
        long_answers = level3Answers.get("long_answers", {})
        if not is_attempted(long_answers.get("3")):
            missing_questions.append("3")
        
        # Question 4: long_answer with ID "4"
        if not is_attempted(long_answers.get("4")):
            missing_questions.append("4")
    
    all_attempted = len(missing_questions) == 0
    return (all_attempted, missing_questions)


def validate_level_attempts(level_id, user_answers):
    """
    Validate that all questions for a level have been attempted.
    
    Args:
        level_id: Level number (1, 2, or 3)
        user_answers: The user answers object from the request
    
    Returns:
        dict: 
            - If all questions attempted: { "allowed": True }
            - If any question missing: { "allowed": False, "missing_question": X }
                where X is the first missing question number (as integer)
    """
    # Use check_level_attempts to get missing questions
    all_attempted, missing_questions = check_level_attempts(level_id, user_answers)
    
    if all_attempted:
        return {"allowed": True}
    else:
        # Return the first missing question number as integer
        first_missing = int(missing_questions[0]) if missing_questions else None
        return {
            "allowed": False,
            "missing_question": first_missing
        }


def normalize_responses(level, responses):
    """
    Normalize responses into the standardized storage format.
    
    Structure:
    {
        level_1: { q1: answer, q2: answer, q3: answer, q4: answer },
        level_2: { q1: answer, q2: answer, q3: answer, q4: answer },
        level_3: { q1: answer, q2: answer, q3: answer, q4: answer }
    }
    
    Args:
        level: Level number (1, 2, or 3)
        responses: The responses dict from the request
    
    Returns:
        dict: Normalized answers with q1, q2, q3, q4 keys
    """
    normalized = {}
    
    if level == 1:
        # Level 1: Responses are directly keyed as "1", "2", "3", "4"
        normalized = {
            "q1": responses.get("1"),
            "q2": responses.get("2"),
            "q3": responses.get("3"),
            "q4": responses.get("4")
        }
    
    elif level == 2:
        # Level 2: Responses are nested in responses["level2Answers"]
        level2Answers = responses.get("level2Answers", {})
        normalized = {
            "q1": level2Answers.get("identify_speaker"),
            "q2": level2Answers.get("dialogue_ordering"),
            "q3": level2Answers.get("main_problem_discussed"),
            "q4": level2Answers.get("match_speaker_role")
        }
    
    elif level == 3:
        # Level 3: Responses are nested in responses["level3Answers"]
        # Note: identify_emotion removed
        level3Answers = responses.get("level3Answers", {})
        
        # Remove identify_emotion if it exists (defensive check)
        if "identify_emotion" in level3Answers:
            level3Answers.pop("identify_emotion", None)
        
        # Get long_answers dictionary
        long_answers = level3Answers.get("long_answers", {})
        
        # IDs now start at 1..4
        normalized = {
            "q1": level3Answers.get("next_action"),           # ID "1"
            "q2": level3Answers.get("fill_missing_phrase"),   # ID "2"
            "q3": long_answers.get("3"),                      # ID "3"
            "q4": long_answers.get("4")                       # ID "4"
        }
    
    return normalized


def load_questions_for_level(level):
    """
    Load questions from JSON file for a specific level.
    
    Args:
        level: Level number (1, 2, or 3)
    
    Returns:
        list: List of question dictionaries
    """
    level_files = {
        1: "data/questions/level1_classroom_tamil.json",
        2: "data/questions/level2_dialogue_tamil.json",
        3: "data/questions/level3_scene_tamil.json"
    }
    
    if level not in level_files:
        raise ValueError(f"Invalid level: {level}")
    
    file_path = os.path.join(BACKEND_DIR, level_files[level])
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Questions file not found: {file_path}")
    
    with open(file_path, "r", encoding="utf-8") as f:
        questions_data = json.load(f)
    
    questions = questions_data.get("questions", [])
    
    # For Level 3, filter out Q1 (identify_emotion MCQ) if it exists
    if level == 3:
        questions = [q for q in questions if not (q.get('id') == "1" and q.get('type') == "mcq")]
    
    return questions


def denormalize_answers_for_evaluation(level, normalized_answers, questions):
    """
    Convert normalized answers back to format expected by evaluator functions.
    
    Args:
        level: Level number (1, 2, or 3)
        normalized_answers: Dict with q1, q2, q3, q4 keys
        questions: List of question dictionaries
    
    Returns:
        dict: Answers in format expected by evaluator functions
    """
    if level == 1:
        # Level 1: Map q1->"1", q2->"2", etc. based on question IDs
        denormalized = {}
        for idx, q in enumerate(questions, start=1):
            q_id = q.get('id', str(idx))
            denormalized[q_id] = normalized_answers.get(f"q{idx}")
        return denormalized
    
    elif level == 2:
        # Level 2: Map back to level2Answers structure
        return {
            "level2Answers": {
                "identify_speaker": normalized_answers.get("q1"),
                "dialogue_ordering": normalized_answers.get("q2"),
                "main_problem_discussed": normalized_answers.get("q3"),
                "match_speaker_role": normalized_answers.get("q4")
            }
        }
    
    elif level == 3:
        # Level 3: Map back to level3Answers structure
        # IDs now 1,2,3,4 (identify_emotion removed)
        level3_answers = {
            "next_action": normalized_answers.get("q1"),              # ID "1"
            "fill_missing_phrase": normalized_answers.get("q2"),      # ID "2"
            "long_answers": {
                "3": normalized_answers.get("q3"),                    # ID "3"
                "4": normalized_answers.get("q4")                     # ID "4"
            }
        }
        return {"level3Answers": level3_answers}
    
    return {}


def get_question_text(question):
    """
    Extract question text from a question object.
    Prioritizes Tamil text, falls back to English, then generic 'question' field.
    
    Args:
        question: Question dictionary from JSON
    
    Returns:
        str: Question text
    """
    # Try question_text_tamil first (Level 2, 3)
    if 'question_text_tamil' in question and question['question_text_tamil']:
        return question['question_text_tamil']
    
    # Try question_text_english (Level 2, 3)
    if 'question_text_english' in question and question['question_text_english']:
        return question['question_text_english']
    
    # Try generic 'question' field (Level 1)
    if 'question' in question and question['question']:
        return question['question']
    
    # Fallback to empty string
    return ""


def is_accuracy_eligible_type(question_type):
    """
    Check if a question type is eligible for Accuracy calculation.
    
    Accuracy-eligible types:
    - MCQs
    - Ordering (ordering, dialogue_ordering)
    - Matching (match_speaker_role)
    - Fill in the blanks (fill_blank, fill_missing_phrase)
    - Emotion identification (emotion, identify_emotion)
    
    Args:
        question_type: String question type from question JSON
    
    Returns:
        bool: True if question type is accuracy-eligible, False otherwise
    """
    accuracy_eligible_types = {
        'mcq',
        'ordering',
        'dialogue_ordering',
        'match_speaker_role',
        'fill_blank',
        'fill_missing_phrase',
        'emotion',
        'identify_emotion'
    }
    return question_type in accuracy_eligible_types


def is_answer_relevance_eligible(question_type, level, question_id):
    """
    Check if a question is eligible for Answer Relevance calculation.
    
    Answer Relevance-eligible types:
    - Main topic / main problem (short answer) - Level 2 Q3: main_problem_discussed
    - Inference / next action - Level 3 Q1 (internal ID "2"): next_action
    - Long answer questions - Level 3 Q3, Q4 (internal IDs "4", "5")
    
    Args:
        question_type: String question type from question JSON
        level: Level number (1, 2, or 3)
        question_id: Question ID string
    
    Returns:
        bool: True if question is relevance-eligible, False otherwise
    """
    # Main topic / main problem (short answer) - Level 2 Q3
    if level == 2 and question_id == "3" and question_type == "short_answer":
        return True
    
    # Inference / next action - Level 3 Q1 (internal ID "2")
    if level == 3 and question_id == "2" and question_type == "short_answer":
        return True
    
    # Long answer questions - Level 3 Q3, Q4 (internal IDs "4", "5")
    if level == 3 and question_id in ["4", "5"] and question_type == "long_answer":
        return True
    
    return False


def is_precision_eligible_type(question_type, level, question_id):
    """
    Check if a question type is eligible for Precision calculation.
    
    Precision-eligible types (must be exact match):
    - Who said what (Level 2 Q1: mcq for identify_speaker)
    - Dialogue ordering (dialogue_ordering)
    - Match speakers to roles (match_speaker_role)
    - Fill in the missing phrase (fill_missing_phrase)
    
    Args:
        question_type: String question type from question JSON
        level: Level number (1, 2, or 3)
        question_id: Question ID string
    
    Returns:
        bool: True if question type is precision-eligible, False otherwise
    """
    # Who said what: Level 2 Q1 (mcq for identify_speaker)
    if question_type == 'mcq' and level == 2 and question_id == "1":
        return True
    
    # Dialogue ordering, Match speakers to roles, Fill in the missing phrase
    precision_eligible_types = {
        'dialogue_ordering',
        'match_speaker_role',
        'fill_missing_phrase'
    }
    return question_type in precision_eligible_types


def transform_level_results(level, evaluator_result, questions):
    """
    Transform evaluator results to the requested format.
    
    Args:
        level: Level number (1, 2, or 3)
        evaluator_result: Result dict from evaluate_level1/2/3 with 'details' key
        questions: List of question dictionaries from JSON
    
    Returns:
        dict: {
            'level': N,
            'questions': [
                {
                    'question_id': str,
                    'question_text': str,
                    'status': "correct" | "wrong"
                }
            ]
        }
    """
    details = evaluator_result.get('details', {})
    
    # Build questions list in the order they appear in the questions list
    questions_list = []
    for question in questions:
        question_id = question.get('id')
        question_detail = details.get(question_id, {})
        
        # Get correctness status
        is_correct = question_detail.get('correct', False)
        status = "correct" if is_correct else "wrong"
        
        # Get question text
        question_text = get_question_text(question)
        
        questions_list.append({
            'question_id': question_id,
            'question_text': question_text,
            'status': status,
            'user_answer': question_detail.get('user_answer', ''),
            'correct_answer': question_detail.get('correct_answer', '')
        })
    
    return {
        'level': level,
        'questions': questions_list
    }


def run_final_evaluation():
    """
    Run final evaluation on all three levels after Level 3 completion.
    
    STAGE 2: Level-wise question correctness display, Accuracy, Precision, and Answer Relevance calculation.
    
    Accuracy is calculated STRICTLY for:
    - MCQs
    - Ordering (ordering, dialogue_ordering)
    - Matching (match_speaker_role)
    - Fill in the blanks (fill_blank, fill_missing_phrase)
    - Emotion identification (emotion, identify_emotion)
    
    Formula: Accuracy = (correct Accuracy-eligible answers) / (total Accuracy-eligible questions)
    
    Precision is calculated STRICTLY for (must be exact match, partial match = incorrect):
    - Who said what (Level 2 Q1: mcq for identify_speaker)
    - Dialogue ordering (dialogue_ordering)
    - Match speakers to roles (match_speaker_role)
    - Fill in the missing phrase (fill_missing_phrase)
    
    Formula: Precision = (correct Precision-eligible answers) / (total Precision-eligible questions)
    
    Answer Relevance is calculated STRICTLY for:
    - Main topic / main problem (short answer) - Level 2 Q3: main_problem_discussed
    - Inference / next action - Level 3 Q1 (internal ID "2"): next_action
    - Long answer questions - Level 3 Q3, Q4 (internal IDs "4", "5")
    
    Formula: Answer Relevance = average semantic similarity score (0-1)
    
    Returns:
        dict: {
            'level_results': [
                {
                    'level': 1,
                    'questions': [
                        {
                            'question_id': str,
                            'question_text': str,
                            'status': "correct" | "wrong"
                        }
                    ]
                },
                {
                    'level': 2,
                    'questions': [...]
                },
                {
                    'level': 3,
                    'questions': [...]
                }
            ],
            'accuracy': float,  # Overall accuracy for accuracy-eligible questions only
            'precision': float,  # Overall precision for precision-eligible questions only (exact match required)
            'answer_relevance': float,  # Overall answer relevance (average semantic similarity) for relevance-eligible questions only
            'overall_score': float,  # Average of accuracy, precision, and answer_relevance
            'learner_level': str  # Beginner, Intermediate, or Pro based on overall_score
        }
    """
    level_results = []
    
    # Store all questions and their evaluation details for accuracy and precision calculation
    all_questions_with_details = []
    
    print("")
    print("=" * 60)
    print("   FINAL EVALUATION STARTED")
    print("   Evaluating all 3 levels (1 → 2 → 3)")
    print("   This may take 1–3 minutes. Please wait.")
    print("=" * 60)
    print("")
    
    # Evaluate each level
    for level in [1, 2, 3]:
        level_key = f"level_{level}"
        normalized_answers = raw_answers_store.get(level_key)
        
        if normalized_answers is None:
            print(f"⚠️ Warning: No answers found for {level_key}")
            continue
        
        print("-" * 50)
        print(f"   EVALUATING LEVEL {level} OF 3")
        print("-" * 50)
        
        # Load questions for this level
        questions = load_questions_for_level(level)
        
        # Denormalize answers for evaluation
        denormalized_answers = denormalize_answers_for_evaluation(level, normalized_answers, questions)
        
        # Run evaluation based on level
        evaluator_result = None
        
        if level == 1:
            print(f"   → Running Level 1 evaluation...")
            user_responses = denormalized_answers
            evaluator_result = evaluate_level1(user_responses, questions)
            sc, tot = evaluator_result.get('score', 0), evaluator_result.get('total', 0)
            print(f"   ✅ Level 1 evaluation completed (Score: {sc}/{tot})")
        
        elif level == 2:
            print(f"   → Running Level 2 evaluation...")
            level2Answers = denormalized_answers.get("level2Answers", {})
            # Convert to format expected by evaluate_level2
            user_responses = {}
            for q in questions:
                q_id = q.get('id')
                if q_id == "1":
                    user_responses[q_id] = level2Answers.get("identify_speaker")
                elif q_id == "2":
                    user_responses[q_id] = level2Answers.get("dialogue_ordering")
                elif q_id == "3":
                    user_responses[q_id] = level2Answers.get("main_problem_discussed")
                elif q_id == "4":
                    user_responses[q_id] = level2Answers.get("match_speaker_role")
            
            evaluator_result = evaluate_level2(user_responses, questions)
            sc, tot = evaluator_result.get('score', 0), evaluator_result.get('total', 0)
            print(f"   ✅ Level 2 evaluation completed (Score: {sc}/{tot})")
        
        elif level == 3:
            print(f"   → Running Level 3 evaluation (may take longer due to ML models)...")
            level3Answers = denormalized_answers.get("level3Answers", {})
            # Convert to format expected by evaluate_level3 (IDs 1..4)
            user_responses = {}
            for idx, q in enumerate(questions, start=1):
                q_id = q.get('id')
                display_id = str(idx)  # force sequential labels 1..n for frontend
                if q_id == "1":
                    user_responses[display_id] = level3Answers.get("next_action")
                elif q_id == "2":
                    user_responses[display_id] = level3Answers.get("fill_missing_phrase")
                elif q_id == "3":
                    long_answers = level3Answers.get("long_answers", {})
                    user_responses[display_id] = long_answers.get("3")
                elif q_id == "4":
                    long_answers = level3Answers.get("long_answers", {})
                    user_responses[display_id] = long_answers.get("4")
            
            # Get audio transcript from questions JSON for Level 3 Q4
            audio_transcript = ""
            if level == 3:
                # Load full JSON to get audio_transcript
                level_file = os.path.join(BACKEND_DIR, "data/questions/level3_scene_tamil.json")
                if os.path.exists(level_file):
                    with open(level_file, 'r', encoding='utf-8') as f:
                        level3_data = json.load(f)
                        audio_transcript = level3_data.get('audio_transcript', '')
            
            evaluator_result = evaluate_level3(user_responses, questions, audio_transcript=audio_transcript)
            sc, tot = evaluator_result.get('score', 0), evaluator_result.get('total', 0)
            print(f"   ✅ Level 3 evaluation completed (Score: {sc}/{tot})")
        
        # Transform evaluator result to requested format
        if evaluator_result:
            transformed_result = transform_level_results(level, evaluator_result, questions)
            level_results.append(transformed_result)
            
            # Store questions with their types, correctness, and semantic similarity for calculation
            details = evaluator_result.get('details', {})
            for question in questions:
                question_id = question.get('id')
                question_type = question.get('type', '')
                question_detail = details.get(question_id, {})
                is_correct = question_detail.get('correct', False)
                
                # Extract semantic similarity score if available
                # Check multiple possible locations where it might be stored
                semantic_similarity = None
                if 'semantic_similarity' in question_detail:
                    semantic_similarity = question_detail.get('semantic_similarity')
                elif 'answer_relevance' in question_detail:
                    semantic_similarity = question_detail.get('answer_relevance')
                elif 'evaluation_metrics' in question_detail:
                    eval_metrics = question_detail.get('evaluation_metrics', {})
                    semantic_similarity = eval_metrics.get('answer_relevance') or eval_metrics.get('semantic_similarity')
                
                all_questions_with_details.append({
                    'question_id': question_id,
                    'question_type': question_type,
                    'level': level,
                    'is_correct': is_correct,
                    'semantic_similarity': semantic_similarity,
                    'question_detail': question_detail  # Store full detail for potential later use
                })
    
    # Calculate Accuracy for accuracy-eligible question types only
    accuracy_eligible_questions = [
        q for q in all_questions_with_details
        if is_accuracy_eligible_type(q['question_type'])
    ]
    
    total_accuracy_eligible = len(accuracy_eligible_questions)
    correct_accuracy_eligible = sum(1 for q in accuracy_eligible_questions if q['is_correct'])
    
    # Calculate accuracy (handle division by zero)
    accuracy = 0.0
    if total_accuracy_eligible > 0:
        accuracy = correct_accuracy_eligible / total_accuracy_eligible
    
    print("")
    print("📊 Accuracy Calculation:")
    print(f"   Accuracy-eligible questions: {total_accuracy_eligible}")
    print(f"   Correct answers: {correct_accuracy_eligible}")
    print(f"   Accuracy: {accuracy:.4f} ({accuracy * 100:.2f}%)")
    
    # Calculate Precision for precision-eligible question types only
    precision_eligible_questions = [
        q for q in all_questions_with_details
        if is_precision_eligible_type(q['question_type'], q['level'], q['question_id'])
    ]
    
    total_precision_eligible = len(precision_eligible_questions)
    correct_precision_eligible = sum(1 for q in precision_eligible_questions if q['is_correct'])
    
    # Calculate precision (handle division by zero)
    precision = 0.0
    if total_precision_eligible > 0:
        precision = correct_precision_eligible / total_precision_eligible
    
    print("")
    print("📊 Precision Calculation:")
    print(f"   Precision-eligible questions: {total_precision_eligible}")
    print(f"   Correct answers (exact match): {correct_precision_eligible}")
    print(f"   Precision: {precision:.4f} ({precision * 100:.2f}%)")
    
    # Calculate Answer Relevance for relevance-eligible question types only
    # Extract semantic similarity scores from stored question details
    relevance_eligible_questions = []
    for q in all_questions_with_details:
        if is_answer_relevance_eligible(q['question_type'], q['level'], q['question_id']):
            semantic_sim = q.get('semantic_similarity')
            # Only include if semantic similarity score is available (0-1 range)
            if semantic_sim is not None and isinstance(semantic_sim, (int, float)) and 0 <= semantic_sim <= 1:
                relevance_eligible_questions.append(semantic_sim)
    
    # Calculate Answer Relevance as average of semantic similarity scores
    answer_relevance = 0.0
    if len(relevance_eligible_questions) > 0:
        answer_relevance = sum(relevance_eligible_questions) / len(relevance_eligible_questions)
    
    print("")
    print("📊 Answer Relevance Calculation:")
    print(f"   Relevance-eligible questions: {len(relevance_eligible_questions)}")
    print(f"   Answer Relevance (avg semantic similarity): {answer_relevance:.4f} ({answer_relevance * 100:.2f}%)")
    
    # Calculate overall_score as average of accuracy, precision, and answer_relevance
    overall_score = (accuracy + precision + answer_relevance) / 3.0
    
    # Assign learner level based on overall_score
    if overall_score < 0.4:
        learner_level = "Beginner"
    elif overall_score < 0.7:
        learner_level = "Intermediate"
    else:  # overall_score >= 0.7
        learner_level = "Pro"
    
    print("")
    print("📊 Overall Score Calculation:")
    print(f"   Accuracy: {accuracy:.4f}")
    print(f"   Precision: {precision:.4f}")
    print(f"   Answer Relevance: {answer_relevance:.4f}")
    print(f"   Overall Score: {overall_score:.4f} ({overall_score * 100:.2f}%)")
    print(f"   Learner Level: {learner_level}")
    print("")
    print("=" * 60)
    print("   FINAL EVALUATION COMPLETED")
    print("=" * 60)
    print("")
    
    return {
        'level_results': level_results,
        'accuracy': accuracy,
        'precision': precision,
        'answer_relevance': answer_relevance,
        'overall_score': overall_score,
        'learner_level': learner_level
    }


@app.route("/evaluate", methods=["POST"])
def evaluate():
    """
    Level submission endpoint with per-level evaluation and optional overall evaluation.
    """
    try:
        data = request.get_json()
        print("🛰️ /evaluate received data:", data)
        if not data:
            return jsonify({"status": "error", "error": "No data received"}), 400
        
        level = data.get("level")
        responses = data.get("responses", {})
        # Accept correct key and common typos from frontend
        trigger_final_evaluation = (
            data.get("trigger_final_evaluation", False) or
            data.get("trigger_final_evaluationn", False) or
            data.get("triggeer_final_evaluation", False)
        )
        print("🛰️ /evaluate level:", level, "response keys:", list(responses.keys()) if isinstance(responses, dict) else type(responses))
        
        if not level or level not in [1, 2, 3]:
            return jsonify({"status": "error", "error": f"Invalid level: {level}. Must be 1, 2, or 3."}), 400
        
        # "Final evaluation only" request: level=3, empty responses, trigger_final_evaluation=True
        if level == 3 and trigger_final_evaluation and isinstance(responses, dict) and len(responses) == 0:
            if not (raw_answers_store.get("level_1") and raw_answers_store.get("level_2") and raw_answers_store.get("level_3")):
                return jsonify({
                    "error": True,
                    "message": "Complete all three levels (1, 2, and 3) before requesting final evaluation."
                }), 400
            # All levels already stored – run final evaluation using stored answers
            print("🎯 Final evaluation only (empty responses) - using stored answers")
            try:
                import time
                start_time = time.time()
                evaluation_results = run_final_evaluation()
                elapsed_time = time.time() - start_time
                print(f"📊 Level-wise Evaluation Results Generated (took {elapsed_time:.2f} seconds)")
                response_data = {
                    "status": "success",
                    "level": 3,
                    "completed": True,
                    "level_results": evaluation_results['level_results'],
                    "accuracy": evaluation_results.get('accuracy', 0.0),
                    "precision": evaluation_results.get('precision', 0.0),
                    "answer_relevance": evaluation_results.get('answer_relevance', 0.0),
                    "overall_score": evaluation_results.get('overall_score', 0.0),
                    "overall_accuracy": evaluation_results.get('accuracy', 0.0),
                    "overall_precision": evaluation_results.get('precision', 0.0),
                    "overall_answer_relevance": evaluation_results.get('answer_relevance', 0.0),
                    "final_listening_score": evaluation_results.get('overall_score', 0.0),
                    "learner_level": evaluation_results.get('learner_level', 'Beginner'),
                    "show_overall_results_button": True,
                }
                return jsonify(response_data)
            except Exception as e:
                print(f"❌ Final evaluation failed: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({"status": "error", "error": str(e)}), 500
        
        # STAGE 1: Level completion validation
        validation = validate_level_attempts(level, responses)
        print("🛰️ /evaluate validation:", validation)
        if not validation["allowed"]:
            return jsonify({"error": True, "message": f"First attempt Question {validation['missing_question']}"}), 400
        
        # Normalize and store raw answers (no evaluation)
        level_key = f"level_{level}"
        normalized_responses = normalize_responses(level, responses)
        raw_answers_store[level_key] = normalized_responses
        print(f"✅ Level {level} submission received - all questions attempted")
        print(f"📦 Stored normalized answers for Level {level}: {normalized_responses}")
        response_data = {}
        
        # For levels 1-2: Only store answers, NO evaluation (evaluation happens only after Level 3)
        if level in [1, 2]:
            response_data = {
                "status": "success",
                "level": level,
                "completed": True,
                "message": f"Level {level} answers stored successfully. Evaluation will happen after Level 3 submission.",
                "evaluation_deferred": True
            }
            print(f"✅ Level {level} answers stored (evaluation deferred until Level 3)")
        
        else:
            # Level 3: Evaluate immediately for this level (no need for overall report)
            questions = load_questions_for_level(level)
            denormalized_answers = denormalize_answers_for_evaluation(level, normalized_responses, questions)
            level3Answers = denormalized_answers.get("level3Answers", {})
            
            user_responses = {}
            for idx, q in enumerate(questions, start=1):
                q_id = q.get('id')
                display_id = str(idx)  # sequential labels for frontend
                if q_id == "1":
                    user_responses[display_id] = level3Answers.get("next_action")
                elif q_id == "2":
                    user_responses[display_id] = level3Answers.get("fill_missing_phrase")
                elif q_id == "3":
                    long_answers = level3Answers.get("long_answers", {})
                    user_responses[display_id] = long_answers.get("3")
                elif q_id == "4":
                    long_answers = level3Answers.get("long_answers", {})
                    user_responses[display_id] = long_answers.get("4")
            
            # Get audio transcript from questions JSON for Level 3 Q4
            audio_transcript = ""
            if level == 3:
                # Load full JSON to get audio_transcript
                level_file = os.path.join(BACKEND_DIR, "data/questions/level3_scene_tamil.json")
                if os.path.exists(level_file):
                    with open(level_file, 'r', encoding='utf-8') as f:
                        level3_data = json.load(f)
                        audio_transcript = level3_data.get('audio_transcript', '')
            
            evaluator_result = evaluate_level3(user_responses, questions, audio_transcript=audio_transcript)
            response_data = {
                "status": "success",
                "level": level,
                "score": evaluator_result.get('score', 0),
                "total": evaluator_result.get('total', 0),
                "details": evaluator_result.get('details', {}),
                "completed": True,
                "message": f"Level {level} submitted successfully. All questions attempted.",
                "accuracy": evaluator_result.get('accuracy', 0.0),
                "precision": evaluator_result.get('precision', 0.0) if isinstance(evaluator_result.get('precision'), (int, float)) else 0.0,
                "answer_relevance": evaluator_result.get('avg_semantic_similarity', 0.0),
                "overall_score": evaluator_result.get('accuracy', 0.0),
                "overall_accuracy": evaluator_result.get('accuracy', 0.0),
                "overall_precision": evaluator_result.get('precision', 0.0) if isinstance(evaluator_result.get('precision'), (int, float)) else 0.0,
                "overall_answer_relevance": evaluator_result.get('avg_semantic_similarity', 0.0),
                "final_listening_score": evaluator_result.get('accuracy', 0.0),
                "pass": (evaluator_result.get('score', 0) / evaluator_result.get('total', 1)) >= 0.3,  # 30% threshold
                "show_overall_results_button": True
            }
            print(f"✅ Level {level} evaluation completed: {evaluator_result.get('score', 0)}/{evaluator_result.get('total', 0)}")
        
        # STAGE 2: Optional overall evaluation trigger (only for Level 3)
        if level == 3:
            all_levels_completed = (
                raw_answers_store.get("level_1") is not None and
                raw_answers_store.get("level_2") is not None and
                raw_answers_store.get("level_3") is not None
            )
            if all_levels_completed and trigger_final_evaluation:
                print("🎯 All levels completed and trigger_final_evaluation = True - Running level-wise evaluation...")
                print("⏳ This may take 30-60 seconds for ML model processing...")
                try:
                    import time
                    start_time = time.time()
                    evaluation_results = run_final_evaluation()
                    elapsed_time = time.time() - start_time
                    print(f"📊 Level-wise Evaluation Results Generated (took {elapsed_time:.2f} seconds)")
                    
                    response_data.update({
                        "level_results": evaluation_results['level_results'],
                        "accuracy": evaluation_results.get('accuracy', 0.0),
                        "precision": evaluation_results.get('precision', 0.0),
                        "answer_relevance": evaluation_results.get('answer_relevance', 0.0),
                        "overall_score": evaluation_results.get('overall_score', 0.0),
                        "learner_level": evaluation_results.get('learner_level', "Beginner"),
                        "show_overall_results_button": True,
                        "overall_accuracy": evaluation_results.get('accuracy', 0.0),
                        "overall_precision": evaluation_results.get('precision', 0.0),
                        "overall_answer_relevance": evaluation_results.get('answer_relevance', 0.0),
                        "final_listening_score": evaluation_results.get('overall_score', 0.0)
                    })
                    
                    level3_result = next((lr for lr in evaluation_results.get('level_results', []) if lr.get('level') == 3), None)
                    if level3_result:
                        questions_list = level3_result.get('questions', [])
                        level3_score = sum(1 for q in questions_list if q.get('status') == 'correct')
                        level3_total = len(questions_list)
                        details_map = {
                            q.get('question_id'): {
                                "correct": q.get('status') == 'correct',
                                "question_text": q.get('question_text')
                            }
                            for q in questions_list if q.get('question_id')
                        }
                        response_data.update({
                            "score": level3_score,
                            "total": level3_total,
                            "details": details_map,
                            "pass": (level3_score / level3_total) >= 0.3 if level3_total > 0 else False  # 30% threshold
                        })
                except Exception as eval_error:
                    print(f"❌ Error during evaluation: {eval_error}")
                    response_data.update({"show_overall_results_button": True})
        
        # Final safety: ensure required keys
        response_data.setdefault("score", 0)
        if response_data.get("total") is None:
            try:
                response_data["total"] = len(load_questions_for_level(level))
            except Exception:
                response_data["total"] = 0
        response_data.setdefault("details", {})
        response_data.setdefault("accuracy", 0.0)
        response_data.setdefault("precision", 0.0)
        response_data.setdefault("answer_relevance", 0.0)
        response_data.setdefault("overall_score", response_data.get("accuracy", 0.0))
        response_data.setdefault("overall_accuracy", response_data.get("accuracy", 0.0))
        response_data.setdefault("overall_precision", response_data.get("precision", 0.0))
        response_data.setdefault("overall_answer_relevance", response_data.get("answer_relevance", 0.0))
        response_data.setdefault("final_listening_score", response_data.get("overall_score", 0.0))
        response_data.setdefault("pass", False)
        response_data.setdefault("show_overall_results_button", True)
        
        try:
            print("📤 Returning evaluate response:", {
                "status": response_data.get("status"),
                "level": response_data.get("level"),
                "score": response_data.get("score"),
                "total": response_data.get("total"),
                "details_keys": list(response_data.get("details", {}).keys()),
                "accuracy": response_data.get("accuracy"),
                "precision": response_data.get("precision"),
                "answer_relevance": response_data.get("answer_relevance"),
                "overall_score": response_data.get("overall_score"),
                "overall_accuracy": response_data.get("overall_accuracy"),
                "overall_precision": response_data.get("overall_precision"),
                "overall_answer_relevance": response_data.get("overall_answer_relevance"),
                "final_listening_score": response_data.get("final_listening_score"),
                "show_overall_results_button": response_data.get("show_overall_results_button"),
            })
        except Exception:
            pass
        
        return jsonify(response_data), 200
    
    except Exception as e:
        print(f"❌ Error in evaluate endpoint: {e}")
        return jsonify({"status": "error", "error": f"Server error: {str(e)}"}), 500


@app.route("/api/start-test/<int:level>", methods=["GET"])
def start_test(level):
    """
    Get questions and audio for a specific level.
    """
    try:
        print(f"📥 start_test called for level {level}")
        # Load questions from JSON files
        level_files = {
            1: "data/questions/level1_classroom_tamil.json",
            2: "data/questions/level2_dialogue_tamil.json",
            3: "data/questions/level3_scene_tamil.json"
        }
        
        if level not in level_files:
            print(f"❌ Invalid level: {level}")
            return jsonify({"error": f"Invalid level: {level}"}), 400
        
        file_path = os.path.join(BACKEND_DIR, level_files[level])
        print(f"📂 Loading questions from: {file_path}")
        
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return jsonify({"error": f"Questions file not found: {file_path}"}), 404
        
        with open(file_path, "r", encoding="utf-8") as f:
            questions_data = json.load(f)
        
        # Extract questions and audio info
        questions = questions_data.get("questions", [])
        print(f"✅ Loaded {len(questions)} questions for level {level}")

        # Prefer explicit audio info; fall back to top-level audio_id/audio_url if provided
        audio_info = questions_data.get("audio") or {}
        if not audio_info:
            top_level_audio_id = questions_data.get("audio_id")
            top_level_audio_url = questions_data.get("audio_url")
            if top_level_audio_id:
                audio_info = {"audio_id": top_level_audio_id}
                if top_level_audio_url:
                    audio_info["url"] = top_level_audio_url
        
        # Ensure audio_info always has at least an empty dict
        if not audio_info:
            audio_info = {}
        
        print(f"🔊 Audio info for level {level}: {audio_info}")
        
        # Always return response (moved outside conditional)
        response = {
            "level": level,
            "questions": questions,
            "audio": audio_info
        }
        print(f"📤 Returning response with {len(questions)} questions")
        return jsonify(response), 200
        
    except Exception as e:
        print(f"❌ Error in start_test endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500


@app.route("/audio/<audio_id>")
def serve_audio(audio_id):
    """
    Serve audio file by audio_id.
    Looks for common audio extensions in Backend/uploads/audio/.
    """
    try:
        audio_dir = os.path.join(BACKEND_DIR, "uploads", "audio")
        # Try common extensions in order
        for ext in [".mp3", ".mpeg", ".wav", ".m4a", ".aac"]:
            candidate = os.path.join(audio_dir, f"{audio_id}{ext}")
            if os.path.exists(candidate):
                mimetype = "audio/mpeg" if ext in [".mp3", ".mpeg", ".m4a", ".aac"] else "audio/wav"
                return send_from_directory(audio_dir, f"{audio_id}{ext}", mimetype=mimetype)
        
        return jsonify({"error": f"Audio file not found: {audio_id}"}), 404
    except Exception as e:
        print(f"❌ Error serving audio {audio_id}: {e}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@app.route("/api/speech-to-text", methods=["POST"])
def speech_to_text():
    """Convert Tamil speech to text using Whisper model."""
    global whisper_model
    
    try:
        import whisper
    except ImportError:
        return jsonify({
            "status": "error",
            "error": "Whisper not installed. Please install: pip install openai-whisper"
        }), 500
    
    # Get model name from environment
    WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL", "base").strip() or "base"
    
    # Load model (cache it)
    if whisper_model is None:
        try:
            print(f"🔄 Loading Whisper model: {WHISPER_MODEL_NAME}...")
            whisper_model = whisper.load_model(WHISPER_MODEL_NAME)
            print(f"✅ Whisper model '{WHISPER_MODEL_NAME}' loaded successfully")
        except Exception as e:
            return jsonify({
                "status": "error",
                "error": f"Failed to load Whisper model: {str(e)}"
            }), 500
    
    # Get audio data
    audio_bytes = None
    if request.is_json and 'audio' in request.json:
        audio_data = request.json['audio']
        # Remove data URL prefix if present
        if ',' in audio_data:
            _, audio_data = audio_data.split(',', 1)
        try:
            audio_bytes = base64.b64decode(audio_data)
        except Exception as e:
            return jsonify({
                "status": "error",
                "error": f"Invalid base64 data: {str(e)}"
            }), 400
    elif 'audio' in request.files:
        audio_file = request.files['audio']
        audio_bytes = audio_file.read()
    
    if not audio_bytes:
        return jsonify({
            "status": "error",
            "error": "No audio data provided"
        }), 400
    
    # Process audio using ffmpeg
    input_audio_path = None
    output_audio_path = None
    try:
        # Find ffmpeg
        ffmpeg_exe = find_ffmpeg()
        if not ffmpeg_exe:
            return jsonify({
                "status": "error",
                "error": "ffmpeg not found. Please install ffmpeg or run: pip install imageio-ffmpeg"
            }), 500
        
        # Save input audio to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as tmp_input:
            tmp_input.write(audio_bytes)
            input_audio_path = tmp_input.name
        
        # Create output WAV file path
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_output:
            output_audio_path = tmp_output.name
        
        # Convert audio to WAV using ffmpeg
        print(f"🔄 Converting audio with ffmpeg: {input_audio_path} -> {output_audio_path}")
        ffmpeg_cmd = [
            ffmpeg_exe,
            '-i', input_audio_path,
            '-ar', '16000',  # Sample rate: 16kHz (Whisper's preferred)
            '-ac', '1',      # Mono channel
            '-f', 'wav',     # WAV format
            '-y',            # Overwrite output file
            output_audio_path
        ]
        
        result_process = subprocess.run(
            ffmpeg_cmd,
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout
        )
        
        if result_process.returncode != 0:
            error_output = result_process.stderr or result_process.stdout
            print(f"❌ ffmpeg conversion failed: {error_output}")
            return jsonify({
                "status": "error",
                "error": f"Audio conversion failed: {error_output[:200]}"
            }), 500
        
        print(f"✅ Audio converted successfully: {output_audio_path}")
        
        # Transcribe using Whisper (it can handle WAV files directly)
        result = whisper_model.transcribe(
            output_audio_path,
            language="ta",
            task="transcribe",
            fp16=False,
            temperature=0
        )
        
        transcribed_text = result.get("text", "").strip()
        
        if not transcribed_text:
            return jsonify({
                "status": "error",
                "error": "Transcription returned empty text"
            }), 400
        
        return jsonify({
            "status": "success",
            "text": transcribed_text
        }), 200
        
    except subprocess.TimeoutExpired:
        return jsonify({
            "status": "error",
            "error": "Audio conversion timed out. Please try again with a shorter audio clip."
        }), 500
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Transcription error: {error_msg}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "status": "error",
            "error": f"Transcription failed: {error_msg}"
        }), 500
    finally:
        # Clean up temp files
        for temp_path in [input_audio_path, output_audio_path]:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception as cleanup_error:
                    print(f"⚠️ Could not delete temp file {temp_path}: {cleanup_error}")


@app.route("/api/test-whisper", methods=["GET"])
def test_whisper():
    """Test if Whisper is working"""
    try:
        import whisper
        WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL", "base").strip() or "base"
        model = whisper.load_model(WHISPER_MODEL_NAME)
        return jsonify({
            "status": "success",
            "message": "Whisper is installed and working",
            "model": WHISPER_MODEL_NAME
        }), 200
    except ImportError:
        return jsonify({
            "status": "error",
            "message": "Whisper not installed. Run: pip install openai-whisper"
        }), 500
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Whisper error: {str(e)}"
        }), 500


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "message": "Backend is running"}), 200


@app.route("/")
def index():
    """Serve the main index.html file"""
    return send_from_directory('..', 'index.html')


@app.route("/ListeningSummary.html")
def listening_summary():
    """Serve the ListeningSummary.html file"""
    return send_from_directory('..', 'ListeningSummary.html')


@app.route("/teacher-agent.js")
def teacher_agent_js():
    """Serve the teacher-agent.js file"""
    return send_from_directory('..', 'teacher-agent.js')


@app.route("/style.css")
def style_css():
    """Serve the style.css file"""
    return send_from_directory('..', 'style.css')


@app.route("/script.js")
def script_js():
    """Serve the script.js file"""
    return send_from_directory('..', 'script.js')


if __name__ == "__main__":
    print("🚀 Starting Tamil Listening Test Backend...")
    print("📝 Level submissions will only validate attempts and store raw answers")
    print("⏸️  Evaluation is postponed until final submission after Level 3")
    print("🌐 Server will be available at http://127.0.0.1:5001")
    print("📂 Serving static files from parent directory")
    # Disable reloader to prevent connection issues during requests
    app.run(debug=False, use_reloader=False, port=5001, host='127.0.0.1')
