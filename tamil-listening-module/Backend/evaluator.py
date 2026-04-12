"""
Evaluation module for checking user answers against correct answers.
"""

import re
import json
import ast
from typing import Dict, List, Tuple, Optional

# ML/DL imports for Level 3 ONLY
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    print("Warning: numpy not available. Level 3 ML features will be disabled.")

try:
    from sentence_transformers import SentenceTransformer
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    print("Warning: sentence-transformers not available. Level 3 ML features will be disabled.")

# Set overall ML availability
ML_AVAILABLE = ML_AVAILABLE and NUMPY_AVAILABLE

def normalize_text(text):
    """
    Normalize text for comparison: trim spaces, remove punctuation, convert to lowercase.
    Works with Tamil text.
    """
    if not text:
        return ""
    # Remove punctuation and extra spaces, convert to lowercase
    normalized = re.sub(r'[^\w\s]', '', text.strip())
    normalized = ' '.join(normalized.split())  # Normalize whitespace
    return normalized.lower()

def normalize_tamil_ra_variations(text):
    """
    Normalize Tamil 'ர' (ra) variations for lenient matching.
    Converts different forms of 'ர' to a common form for comparison.
    """
    if not text:
        return text
    # Normalize different forms of 'ர' - this helps with spelling variations
    # ர, ற, and other ra variations are normalized
    # For now, we'll use a simple approach: replace common ra variations
    normalized = text
    # You can add more Tamil character normalizations here if needed
    return normalized

def fuzzy_match_classroom(text):
    """
    Check if text contains classroom-related words, allowing for spelling variations.
    Accepts variations like வகுப்பறை, வகுப்பரை, வகுப்பு அறை, etc.
    Very lenient - accepts even if "ர" (ra) is misspelled.
    """
    if not text:
        return False
    
    text_normalized = normalize_text(text)
    text_original = text.strip()
    
    # Check for English classroom keywords
    if 'classroom' in text_normalized or 'class room' in text_normalized:
        return True
    
    # Check for Tamil classroom keywords with lenient matching
    # Look for "வகுப்ப" (vaguppa) followed by room-related characters
    if 'வகுப்ப' in text_original or 'வகுப்ப' in text_normalized:
        # Check if followed by room-related endings (accepting various "ர" forms)
        # Accept: வகுப்பறை, வகுப்பரை, வகுப்பு அறை, வகுப்பறைக்குள், etc.
        room_endings = ['றை', 'ரை', 'அறை', 'றைக்குள்', 'ரைக்குள்', 'றைக்கு', 'ரைக்கு']
        for ending in room_endings:
            if ending in text_original or ending in text_normalized:
                return True
        # Also accept if "வகுப்பு" is followed by "அறை" (with space)
        if 'வகுப்பு' in text_original and 'அறை' in text_original:
            return True
    
    # Also check standalone "அறை" (room) if context suggests classroom
    if 'அறை' in text_original and len(text_original) < 20:  # Short answer likely means "room/classroom"
        return True
    
    return False

def evaluate_level1(user_responses, reference_questions):
    """
    Evaluate Level 1 user answers against reference questions.
    Learning-oriented and lenient evaluation for beginners.
    
    Args:
        user_responses: Dictionary mapping question_id to user_answer
        reference_questions: List of question dictionaries with id, type, answer/correctAnswer, etc.
    
    Returns:
        dict: {
            'score': int,
            'total': int,
            'details': {
                question_id: {
                    'correct': bool,
                    'user_answer': str,
                    'correct_answer': str
                }
            }
        }
    """
    details = {}
    score = 0
    total = len(reference_questions)
    
    for question in reference_questions:
        question_id = question.get('id')
        user_answer = user_responses.get(question_id, '').strip()
        # Support both 'answer' and 'correctAnswer' fields
        correct_answer = question.get('answer') or question.get('correctAnswer', '')
        question_type = question.get('type', '')
        
        is_correct = False
        
        # Fill-in-the-blank questions: normalized string matching (RULE-BASED ONLY for Level 1)
        if question_type == 'fill_blank' or question_type == 'fill-missing-word':
            user_normalized = normalize_text(user_answer)
            correct_normalized = normalize_text(correct_answer)
            
            # Check normalized exact match
            if user_normalized == correct_normalized:
                is_correct = True
            else:
                # Check alternatives if they exist (rule-based)
                alternatives = question.get('alternatives', [])
                for alt in alternatives:
                    alt_normalized = normalize_text(str(alt))
                    if user_normalized == alt_normalized:
                        is_correct = True
                        break
                
                # For Question 1 (classroom): Accept any variation of "classroom" (வகுப்பறை, வகுப்பு அறை)
                # This makes it lenient for spelling variations including wrong "ர" (ra) characters
                if question_id == "1" and not is_correct:
                    # Use fuzzy matching to accept classroom variations even with spelling errors
                    # This will accept: வகுப்பறை, வகுப்பரை, வகுப்பு அறை, etc.
                    contains_classroom = fuzzy_match_classroom(user_answer)
                    
                    # Reject if it's clearly "school" (பள்ளி) without classroom context
                    school_keywords = ['பள்ளி', 'school']
                    user_lower = user_normalized.lower()
                    is_only_school = any(
                        (keyword in user_lower or normalize_text(keyword) in user_lower) and
                        not fuzzy_match_classroom(user_answer)
                        for keyword in school_keywords
                    )
                    
                    # Accept if it contains classroom concept (even with spelling variations) and is not just "school"
                    if contains_classroom and not is_only_school:
                        is_correct = True
                
                # NOTE: For Level 1 fill-in-the-blank, we intentionally DO NOT use
                # semantic similarity ML here. Only exact/alternative rule-based
                # matches are allowed, to avoid over-lenient acceptance like "நிலையம்".
        
        # Ordering questions: split by commas, compare sequence order
        elif question_type == 'ordering':
            # Get correct order (can be array or string)
            correct_order = question.get('answer', [])
            if isinstance(correct_order, str):
                # If answer is a string, try to parse it
                correct_order = [item.strip() for item in correct_order.split(',')]
            
            # Split user input by commas and normalize
            user_order = [normalize_text(item.strip()) for item in user_answer.split(',') if item.strip()]
            correct_order_normalized = [normalize_text(str(item)) for item in correct_order]
            
            # Check if sequences match (same length and same order)
            if len(user_order) == len(correct_order_normalized):
                # Compare each position
                matches = sum(1 for i in range(len(user_order)) 
                            if user_order[i] == correct_order_normalized[i])
                # If all positions match, it's correct
                if matches == len(user_order):
                    is_correct = True
                # Lenient: if most positions match (80%), consider correct
                elif matches >= len(user_order) * 0.8:
                    is_correct = True
        
        # Number-based answers: match Tamil number words exactly (after normalization)
        elif question_type == 'short_answer' and any(keyword in question.get('question', '').lower() 
                                                      for keyword in ['எத்தனை', 'எண்', 'number']):
            user_normalized = normalize_text(user_answer)
            correct_normalized = normalize_text(correct_answer)
            
            # Exact match after normalization (for Tamil numbers like "இருபது")
            if user_normalized == correct_normalized:
                is_correct = True
            else:
                # Check alternatives
                alternatives = question.get('alternatives', [])
                for alt in alternatives:
                    alt_normalized = normalize_text(str(alt))
                    if user_normalized == alt_normalized:
                        is_correct = True
                        break
        
        # Short-answer questions: keyword matching (allow longer phrases)
        elif question_type == 'short_answer':
            user_normalized = normalize_text(user_answer)
            correct_normalized = normalize_text(correct_answer)
            
            # Check if correct answer keyword appears in user answer
            # Split correct answer into words
            correct_words = correct_normalized.split()
            
            if len(correct_words) > 0:
                # Check if all key words from correct answer appear in user answer
                all_keywords_present = all(word in user_normalized for word in correct_words)
                if all_keywords_present:
                    is_correct = True
                # Also check exact match
                elif user_normalized == correct_normalized:
                    is_correct = True
                # Check alternatives
                else:
                    alternatives = question.get('alternatives', [])
                    for alt in alternatives:
                        alt_normalized = normalize_text(str(alt))
                        alt_words = alt_normalized.split()
                        if len(alt_words) > 0:
                            if all(word in user_normalized for word in alt_words):
                                is_correct = True
                                break
                            elif user_normalized == alt_normalized:
                                is_correct = True
                                break
        
        # MCQ questions: exact match (case-insensitive, normalized)
        elif question_type == 'mcq':
            user_normalized = normalize_text(user_answer)
            correct_normalized = normalize_text(correct_answer)
            
            if user_normalized == correct_normalized:
                is_correct = True
            else:
                alternatives = question.get('alternatives', [])
                for alt in alternatives:
                    alt_normalized = normalize_text(str(alt))
                    if user_normalized == alt_normalized:
                        is_correct = True
                        break
        
        # Store detailed information for each question
        details[question_id] = {
            'correct': is_correct,
            'user_answer': user_answer,
            'correct_answer': correct_answer
        }
        
        if is_correct:
            score += 1
    
    return {
        'score': score,
        'total': total,
        'details': details
    }

def evaluate_answers(questions, user_responses):
    """
    Evaluate user answers against reference questions.
    
    Args:
        questions: List of question dictionaries with id, type, correctAnswer, etc.
        user_responses: Dictionary mapping question_id to user_answer
    
    Returns:
        dict: {
            'results': [
                {
                    'question_id': str,
                    'correct': bool,
                    'user_answer': str,
                    'correct_answer': str
                }
            ],
            'score': int,
            'total': int,
            'accuracy': float,
            'pass': bool
        }
    """
    results = []
    score = 0
    total = len(questions)
    
    for question in questions:
        question_id = question.get('id')
        user_answer = user_responses.get(question_id, '').strip()
        correct_answer = question.get('correctAnswer', '')
        
        # Check if answer is correct
        is_correct = False
        
        if question.get('type') == 'mcq':
            # For MCQ, check exact match (case-insensitive)
            is_correct = user_answer.lower() == correct_answer.lower()
        else:
            # For short_answer, check exact match or alternatives
            user_lower = user_answer.lower()
            correct_lower = correct_answer.lower()
            
            if user_lower == correct_lower:
                is_correct = True
            else:
                # Check alternatives if they exist
                alternatives = question.get('alternatives', [])
                for alt in alternatives:
                    if user_lower == str(alt).lower():
                        is_correct = True
                        break
        
        if is_correct:
            score += 1
        
        results.append({
            'question_id': question_id,
            'correct': is_correct,
            'user_answer': user_answer,
            'correct_answer': correct_answer
        })
    
    accuracy = (score / total * 100) if total > 0 else 0.0
    pass_threshold = 70  # 70% to pass
    passed = accuracy >= pass_threshold
    
    return {
        'results': results,
        'score': score,
        'total': total,
        'accuracy': round(accuracy, 2),
        'pass': passed
    }


# ============================================================================
# LEVEL 2 EVALUATION (Intermediate evaluation logic - Level 2 ONLY)
# ============================================================================
# Level 2 - Intermediate evaluation logic
# This function handles Level 2 specific evaluation requirements.
# Do NOT modify evaluate_level1() or evaluate_level3().
# ============================================================================

# Level 2 Text Preprocessing Utilities (Level 2 ONLY)
# Robust preprocessing for Level 2 text-based answers (typed or ASR output)
# These functions are used ONLY within evaluate_level2() and do NOT affect Level 1 or Level 3

# Level 2 ML Components (Level 2 ONLY - separate from Level 3 ML)
# Light ML-based semantic similarity for Level 2 short answers (main action, intent)
# Do NOT affect Level 1 or Level 3 ML logic

_level2_model = None

def _load_level2_model():
    """
    Lazy-load ML model for Level 2 semantic similarity (Level 2 ONLY).
    Uses multilingual sentence transformer for Tamil support.
    Only loads when Level 2 ML evaluation is called.
    Does NOT affect Level 3 ML model.
    """
    global _level2_model
    if _level2_model is None and ML_AVAILABLE:
        try:
            # Use lightweight multilingual model for Tamil support
            _level2_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            print("Level 2 ML model loaded successfully.")
        except Exception as e:
            print(f"Warning: Could not load Level 2 ML model: {e}")
            _level2_model = False  # Mark as unavailable
    return _level2_model

def _level2_compute_semantic_similarity(text1: str, text2: str) -> float:
    """
    Compute semantic similarity for Level 2 using ML model (Level 2 ONLY).
    Used as fallback for short open answers (main action, intent).
    Does NOT affect Level 1 or Level 3 ML logic.
    
    Args:
        text1: First text (user answer)
        text2: Second text (correct answer)
    
    Returns:
        Similarity score between 0 and 1
    """
    model = _load_level2_model()
    if not model:
        return 0.0
    
    try:
        if not NUMPY_AVAILABLE:
            return 0.0
        
        embeddings = model.encode([text1, text2], convert_to_numpy=True)
        # Compute cosine similarity
        dot_product = np.dot(embeddings[0], embeddings[1])
        norm1 = np.linalg.norm(embeddings[0])
        norm2 = np.linalg.norm(embeddings[1])
        similarity = dot_product / (norm1 * norm2) if (norm1 * norm2) > 0 else 0.0
        return float(similarity)
    except Exception as e:
        print(f"Error computing Level 2 semantic similarity: {e}")
        return 0.0

def _level2_lowercase(text):
    """
    Convert text to lowercase for Level 2 preprocessing.
    Works with Tamil and English text.
    Level 2 ONLY - does not affect Level 1 or Level 3.
    """
    if not text:
        return ""
    return text.lower()

def _level2_remove_punctuation(text):
    """
    Remove punctuation from text for Level 2 preprocessing.
    Preserves Tamil and English alphanumeric characters and whitespace.
    Level 2 ONLY - does not affect Level 1 or Level 3.
    """
    if not text:
        return ""
    # Remove punctuation but preserve Tamil and English alphanumeric characters and whitespace
    # This regex keeps word characters (including Tamil) and whitespace
    return re.sub(r'[^\w\s]', '', text)

def _level2_trim_whitespace(text):
    """
    Trim and normalize whitespace for Level 2 preprocessing.
    Removes leading/trailing spaces and normalizes internal whitespace.
    Level 2 ONLY - does not affect Level 1 or Level 3.
    """
    if not text:
        return ""
    # Strip leading/trailing whitespace
    text = text.strip()
    # Normalize multiple spaces/tabs/newlines to single space
    text = re.sub(r'\s+', ' ', text)
    return text

def _level2_preprocess_text(text):
    """
    Complete text preprocessing pipeline for Level 2.
    Applies: lowercasing → punctuation removal → whitespace normalization.
    Works with Tamil and English text.
    Level 2 ONLY - does not affect Level 1 or Level 3 preprocessing.
    
    Args:
        text: Input text (can be Tamil or English)
    
    Returns:
        Preprocessed text ready for comparison
    """
    if not text:
        return ""
    
    # Apply preprocessing steps in order
    text = _level2_lowercase(text)
    text = _level2_remove_punctuation(text)
    text = _level2_trim_whitespace(text)
    
    return text

def _level2_process_answer_input(answer_input):
    """
    Optional ASR support for Level 2 spoken answers (non-breaking).
    Processes answer input which can be either text or audio.
    
    Optional ASR support – not mandatory:
    - If input is audio → convert to text using ASR (if available)
    - Else → treat input as text directly
    - System works fully even if ASR is not provided
    
    Args:
        answer_input: Can be str (text) or dict with 'audio_path' or 'audio_data'
    
    Returns:
        str: Text answer ready for evaluation
    """
    # If input is already text (string), return as-is
    if isinstance(answer_input, str):
        return answer_input.strip()
    
    # If input is dict with audio data, try ASR conversion (optional)
    if isinstance(answer_input, dict):
        audio_path = answer_input.get('audio_path')
        audio_data = answer_input.get('audio_data')
        
        # Optional ASR hook – not mandatory
        # System works fully even if ASR is not available
        if audio_path or audio_data:
            try:
                # Try to import ASR module (optional)
                from asr import transcribe_audio
                
                # If audio_path provided, use it
                if audio_path:
                    transcribed_text = transcribe_audio(audio_path)
                    return transcribed_text.strip() if transcribed_text else ""
                
                # If audio_data provided, save temporarily and transcribe
                # (This is a placeholder - actual implementation would handle audio_data)
                elif audio_data:
                    # Placeholder: In real implementation, save audio_data to temp file
                    # then call transcribe_audio(temp_path)
                    print("Warning: audio_data ASR not yet implemented. Treating as text.")
                    return ""
                    
            except ImportError:
                # ASR module not available - system continues without it
                print("ASR module not available. Treating input as text.")
                return ""
            except Exception as e:
                # ASR failed - system continues without it
                print(f"ASR processing failed: {e}. Treating input as text.")
                return ""
    
    # Default: treat as text or return empty string
    return str(answer_input).strip() if answer_input else ""

def evaluate_level2(user_responses, reference_questions):
    """
    Evaluate Level 2 user answers against reference questions.
    Intermediate evaluation logic for Level 2.
    
    Args:
        user_responses: Dictionary mapping question_id to user_answer
        reference_questions: List of question dictionaries with id, type, answer/correctAnswer, etc.
    
    Returns:
        dict: {
            'score': int,
            'total': int,
            'accuracy': float,
            'promotion_status': str,  # "promoted" or "intermediate"
            'details': {
                question_id: {
                    'correct': bool,
                    'user_answer': str,
                    'correct_answer': str
                }
            }
        }
    """
    # ========================================================================
    # LEVEL 2 EVALUATION SCOPE
    # ========================================================================
    # This evaluation module implements logic for 6 question types:
    # 1. identify_speaker - Identify the speaker
    # 2. dialogue_ordering - Dialogue ordering
    # 3. main_action / identify_action - Main action identification
    # 4. who_decided / find_who_decided - WHO decided something
    # 5. match_speaker / match_sentence_speaker - Match sentence to speaker
    # 6. short_answer - Generic short answer questions
    #
    # Note: Currently, only 4 question types are instantiated in the UI:
    # - identify_speaker (MCQ)
    # - dialogue_ordering (drag-and-drop)
    # - main_action (text input with semantic similarity)
    # - match_speaker_role (drag-and-drop matching)
    #
    # The remaining evaluation methods (who_decided, match_sentence_speaker,
    # and generic short_answer) are reserved for future UI extension.
    # ========================================================================
    
    details = {}
    score = 0
    total = len(reference_questions)
    
    for question in reference_questions:
        question_id = question.get('id')
        user_answer_raw = user_responses.get(question_id, '')

        # Debug logging for Q2 and Q4
        if question_id in ["2", "4"]:
            print(f"\n[DEBUG] Evaluating Q{question_id}")
            print(f"  user_answer_raw type: {type(user_answer_raw)}")
            print(f"  user_answer_raw value: {user_answer_raw}")
        
        # ====================================================================
        # Optional ASR support for Level 2 spoken answers (non-breaking)
        # ====================================================================
        # Optional ASR hook – not mandatory:
        # - If input type is audio → convert to text using ASR (if available)
        # - Else → treat input as text directly
        # - System works fully even if ASR is not provided
        # ====================================================================
        # For Q2 (dialogue_ordering) and Q4 (match_speaker_role), preserve original data types
        # Try to parse stringified lists/dicts (single quotes allowed) before ASR/text processing
        if question_id == "2":
            parsed = None
            if isinstance(user_answer_raw, str):
                try:
                    parsed = json.loads(user_answer_raw)
                except Exception:
                    try:
                        parsed = ast.literal_eval(user_answer_raw)
                    except Exception:
                        parsed = None
            if isinstance(parsed, list):
                user_answer = parsed
            elif isinstance(user_answer_raw, list):
                user_answer = user_answer_raw
            else:
                user_answer = _level2_process_answer_input(user_answer_raw)
        elif question_id == "4":
            parsed = None
            if isinstance(user_answer_raw, str):
                try:
                    parsed = json.loads(user_answer_raw)
                except Exception:
                    try:
                        parsed = ast.literal_eval(user_answer_raw)
                    except Exception:
                        parsed = None
            if isinstance(parsed, dict):
                user_answer = parsed
            elif isinstance(user_answer_raw, dict):
                user_answer = user_answer_raw
            else:
                user_answer = _level2_process_answer_input(user_answer_raw)
        else:
            user_answer = _level2_process_answer_input(user_answer_raw)

        if question_id in ["2", "4"]:
            print(f"  user_answer type after processing: {type(user_answer)}")
            print(f"  user_answer value after processing: {user_answer}")
        
        # Support both 'answer' and 'correctAnswer' fields
        correct_answer = question.get('answer') or question.get('correctAnswer', '')
        question_type = question.get('type', '')
        
        is_correct = False
        
        # ====================================================================
        # LEVEL 2 RULE-BASED NLP EVALUATION (Level 2 question types ONLY)
        # ====================================================================
        # Level 2 question types:
        # - Identify the speaker → exact match after preprocessing
        # - WHO decided → entity (name) exact match
        # - Dialogue ordering → strict sequence match (order-sensitive)
        # - Match sentence to speaker → pairwise exact match
        # - Main action → keyword matching (all required keywords must appear)
        # ====================================================================
        
        # 1. Identify the speaker: exact match after preprocessing
        if question_type == 'identify-speaker' or question_type == 'identify_speaker':
            user_normalized = _level2_preprocess_text(user_answer)
            correct_normalized = _level2_preprocess_text(correct_answer)
            
            # Exact match after preprocessing
            if user_normalized == correct_normalized:
                is_correct = True
            else:
                # Check alternatives if they exist
                alternatives = question.get('alternatives', [])
                for alt in alternatives:
                    alt_normalized = _level2_preprocess_text(str(alt))
                    if user_normalized == alt_normalized:
                        is_correct = True
                        break
        
        # 2. WHO decided: entity (name) exact match
        elif question_type == 'find-who-decided' or question_type == 'find_who_decided' or question_type == 'who_decided':
            user_normalized = _level2_preprocess_text(user_answer)
            correct_normalized = _level2_preprocess_text(correct_answer)
            
            # Entity (name) exact match - no partial credit
            if user_normalized == correct_normalized:
                is_correct = True
            else:
                # Check alternatives (other valid names)
                alternatives = question.get('alternatives', [])
                for alt in alternatives:
                    alt_normalized = _level2_preprocess_text(str(alt))
                    if user_normalized == alt_normalized:
                        is_correct = True
                        break
        
        # 3. Dialogue ordering: strict sequence match (order-sensitive)
        # RULE-BASED ONLY - No ML model used for Q2
        elif question_type == 'dialogue-ordering' or question_type == 'dialogue_ordering' or question_type == 'ordering':
            # Get correct order (can be array or string)
            correct_order = question.get('answer', [])
            if isinstance(correct_order, str):
                correct_order = [item.strip() for item in correct_order.split(',')]
            
            # Get items array from question (for index-based answers)
            question_items = question.get('items', [])
            
            # Build correct index order (1-indexed) from items array for direct index comparison
            correct_index_order = []
            for ans_item in correct_order:
                try:
                    idx = question_items.index(ans_item) + 1
                    correct_index_order.append(idx)
                except ValueError:
                    correct_index_order.append(None)
            
            # Handle user input: can be comma-separated string, array of indices, or array of text
            is_index_list = False
            user_order_exact = []
            user_order = []
            user_index_order = []
            
            if isinstance(user_answer, str):
                parts = [p.strip() for p in user_answer.split(',') if p.strip()]
                if all(p.replace('.','',1).isdigit() for p in parts):
                    is_index_list = True
                    user_index_order = [int(float(p)) for p in parts]
                else:
                    user_order = [_level2_preprocess_text(item) for item in parts]
                    user_order_exact = parts
            elif isinstance(user_answer, list):
                first_item = user_answer[0] if len(user_answer) > 0 else None
                if first_item is not None:
                    try:
                        float(first_item)
                        is_index_list = True
                    except (ValueError, TypeError):
                        is_index_list = False
                
                if is_index_list:
                    for idx in user_answer:
                        try:
                            idx_int = int(float(idx))
                            user_index_order.append(idx_int)
                            if 1 <= idx_int <= len(question_items):
                                item_text = str(question_items[idx_int - 1])
                                user_order_exact.append(item_text.strip())
                                user_order.append(_level2_preprocess_text(item_text))
                        except (ValueError, TypeError):
                            continue
                else:
                    user_order = [_level2_preprocess_text(str(item).strip()) for item in user_answer if item]
                    user_order_exact = [str(item).strip() for item in user_answer if item]
            else:
                user_order = []
                user_order_exact = []
            
            correct_order_exact = [str(item).strip() for item in correct_order]
            
            if question_id == "2":
                print(f"[DEBUG] Q2 Dialogue Ordering Evaluation:")
                print(f"  User answer (raw): {user_answer}")
                print(f"  User index order: {user_index_order}")
                print(f"  Correct index order: {correct_index_order}")
                print(f"  User order (exact): {user_order_exact}")
                print(f"  Correct order (exact): {correct_order_exact}")
                print(f"  User order length: {len(user_order_exact)}, Correct order length: {len(correct_order_exact)}")
            
            # First: direct index comparison if both are index lists
            if user_index_order and all(i is not None for i in correct_index_order):
                if user_index_order == correct_index_order:
                    is_correct = True
                    if question_id == "2":
                        print("  ✅ Q2 marked as CORRECT (index match)")
                else:
                    if question_id == "2":
                        print("  ❌ Q2 index comparison failed")
            # Second: exact text comparison
            if not is_correct and len(user_order_exact) == len(correct_order_exact):
                exact_matches = sum(1 for i in range(len(user_order_exact)) 
                                  if user_order_exact[i] == correct_order_exact[i])
                if question_id == "2":
                    print(f"  Exact matches: {exact_matches}/{len(user_order_exact)}")
                if exact_matches == len(user_order_exact):
                    is_correct = True
                    if question_id == "2":
                        print(f"  ✅ Q2 marked as CORRECT (exact match)")
            # Third: normalized comparison
            if not is_correct:
                correct_order_normalized = [_level2_preprocess_text(str(item)) for item in correct_order]
                if question_id == "2":
                    print(f"  Trying normalized comparison...")
                    print(f"  User order (normalized): {user_order}")
                    print(f"  Correct order (normalized): {correct_order_normalized}")
                
                if len(user_order) == len(correct_order_normalized):
                    matches = sum(1 for i in range(len(user_order)) 
                                if user_order[i] == correct_order_normalized[i])
                    if question_id == "2":
                        print(f"  Normalized matches: {matches}/{len(user_order)}")
                        for i in range(len(user_order)):
                            match_status = "✓" if user_order[i] == correct_order_normalized[i] else "✗"
                            print(f"    Pos {i+1}: {match_status} User: '{user_order[i][:50]}...' vs Correct: '{correct_order_normalized[i][:50]}...'")
                    if matches == len(user_order):
                        is_correct = True
                        if question_id == "2":
                            print(f"  ✅ Q2 marked as CORRECT (normalized match)")
                else:
                    if question_id == "2":
                        print(f"  ❌ Q2 marked as WRONG - length mismatch (normalized)")
        
        # 4. Match sentence to speaker: all sentence-speaker pairs must match
        elif question_type == 'match-sentence-speaker' or question_type == 'match_sentence_speaker' or question_type == 'match_speaker':
            # Answer is a dictionary mapping sentences to speakers
            correct_mapping = question.get('answer', {})
            if isinstance(correct_mapping, dict):
                # User answer should also be a dictionary or comma-separated pairs
                user_mapping = {}
                
                # Parse user input: can be dict, comma-separated string, or JSON string
                if isinstance(user_answer, dict):
                    user_mapping = user_answer
                elif isinstance(user_answer, str):
                    # Try to parse as JSON first
                    try:
                        import json
                        user_mapping = json.loads(user_answer)
                    except:
                        # Parse comma-separated format: "sentence1:speaker1, sentence2:speaker2"
                        for pair in user_answer.split(','):
                            if ':' in pair:
                                parts = pair.split(':', 1)
                                if len(parts) == 2:
                                    sentence = _level2_preprocess_text(parts[0].strip())
                                    speaker = _level2_preprocess_text(parts[1].strip())
                                    user_mapping[sentence] = speaker
                
                # Check if all sentence-speaker pairs match
                if len(user_mapping) == len(correct_mapping):
                    all_pairs_match = True
                    for correct_sentence, correct_speaker in correct_mapping.items():
                        correct_sentence_norm = _level2_preprocess_text(str(correct_sentence))
                        correct_speaker_norm = _level2_preprocess_text(str(correct_speaker))
                        
                        # Find matching user sentence
                        user_speaker = None
                        for user_sent, user_spk in user_mapping.items():
                            user_sent_norm = _level2_preprocess_text(str(user_sent))
                            if user_sent_norm == correct_sentence_norm:
                                user_speaker = _level2_preprocess_text(str(user_spk))
                                break
                        
                        # Check if speaker matches
                        if user_speaker != correct_speaker_norm:
                            all_pairs_match = False
                            break
                    
                    if all_pairs_match:
                        is_correct = True
            else:
                # Fallback: treat as simple string match
                user_normalized = _level2_preprocess_text(user_answer)
                correct_normalized = _level2_preprocess_text(str(correct_mapping))
                if user_normalized == correct_normalized:
                    is_correct = True
        
        # 5. Main action: keyword matching + ML semantic similarity (fallback)
        elif question_type == 'identify-action' or question_type == 'identify_action' or question_type == 'main_action':
            # Answer can be a string or array of possible answers
            correct_answers = question.get('answer', [])
            if isinstance(correct_answers, str):
                correct_answers = [correct_answers]
            elif not isinstance(correct_answers, list):
                correct_answers = [str(correct_answers)]
            
            user_normalized = _level2_preprocess_text(user_answer)
            keyword_match_success = False
            
            # Check against each possible correct answer
            for correct_answer_item in correct_answers:
                correct_normalized = _level2_preprocess_text(str(correct_answer_item))
                
                # Step 1: Check exact match first
                if user_normalized == correct_normalized:
                    is_correct = True
                    keyword_match_success = True
                    break
                
                # Step 2: Rule-based keyword matching (primary method)
                if not is_correct:
                    correct_words = correct_normalized.split()
                    if len(correct_words) > 0:
                        # All keywords must be present (no partial credit)
                        all_keywords_present = all(word in user_normalized for word in correct_words)
                        if all_keywords_present:
                            is_correct = True
                            keyword_match_success = True
                            break
                
                # Step 3: ML semantic similarity (fallback ONLY if keyword matching fails)
                # Used ONLY for main action questions
                if not keyword_match_success and not is_correct:
                    semantic_sim = _level2_compute_semantic_similarity(user_answer, str(correct_answer_item))
                    
                    # Accept answer if semantic similarity >= 0.70
                    if semantic_sim >= 0.70:
                        is_correct = True
                        break
        
        # ====================================================================
        # Fallback: Generic question types (MCQ, ordering, short_answer, fill_blank)
        # ====================================================================
        elif question_type == 'mcq':
            user_normalized = _level2_preprocess_text(user_answer)
            correct_normalized = _level2_preprocess_text(correct_answer)
            
            if user_normalized == correct_normalized:
                is_correct = True
            else:
                alternatives = question.get('alternatives', [])
                for alt in alternatives:
                    alt_normalized = _level2_preprocess_text(str(alt))
                    if user_normalized == alt_normalized:
                        is_correct = True
                        break
        
        elif question_type == 'ordering' or question_type == 'order-events':
            correct_order = question.get('answer', [])
            if isinstance(correct_order, str):
                correct_order = [item.strip() for item in correct_order.split(',')]
            
            user_order = [_level2_preprocess_text(item.strip()) for item in user_answer.split(',') if item.strip()]
            correct_order_normalized = [_level2_preprocess_text(str(item)) for item in correct_order]
            
            if len(user_order) == len(correct_order_normalized):
                matches = sum(1 for i in range(len(user_order)) 
                            if user_order[i] == correct_order_normalized[i])
                if matches == len(user_order):
                    is_correct = True
        
        elif question_type == 'short_answer':
            # Special handling for Level 2 Question 3: Use ML semantic similarity ONLY
            # Question: "இந்த உரையாடலில் சரத் சந்திக்கும் முக்கிய பிரச்சனை என்ன?"
            # This question asks about the main problem, so we use advanced ML evaluation
            # No keyword matching, no spelling checks - only semantic content evaluation
            if question_id == "3":
                # Use LLM Judge for Level 2 Q3 evaluation
                print(f"   [LLM JUDGE Level 2 Q3] Evaluating answer with LLM judge...")
                question_text = question.get('question_text_tamil', '') or question.get('question_text_english', '')
                
                # Get alternatives for context
                alternatives = question.get('alternatives', [])
                key_ideas = []  # Level 2 Q3 doesn't have key_ideas, but we can extract from answer
                
                # RULE-BASED PRE-CHECK: Detect contradictions BEFORE LLM judge
                # Check if user answer contradicts the correct answer (e.g., says "didn't leak" when answer says "leaked/flooded")
                contradiction_detected = False
                
                # Negation words that contradict the correct answer
                negation_words = ['கசியவில்லை', 'கசியாது', 'கசியவேயில்லை', 'கசியவில்லை', 'கசியவே இல்லை']
                # Words in correct answer that indicate water leaked/flooded
                positive_words = ['குழாய் உடைந்து', 'தண்ணீர் நிரம்பியது', 'தண்ணீர் தேங்கியது', 'குழாய் கசிந்து', 
                                'தண்ணீர் நிரம்ப', 'தண்ணீர் தேங்க', 'குழாய் பழுது', 'குழாய் உடைப்பு']
                
                user_has_negation = any(neg_word in user_answer for neg_word in negation_words)
                correct_has_positive = any(pos_word in correct_answer for pos_word in positive_words)
                
                if user_has_negation and correct_has_positive:
                    print(f"   [RULE-BASED Q3] CONTRADICTION DETECTED: User says water didn't leak, but correct answer says pipe broke/water flooded → WRONG")
                    is_correct = False
                    method = 'rule_based_contradiction'
                    confidence = 0.0
                    contradiction_detected = True
                
                # First check if user answer matches any alternative exactly (normalized)
                user_norm = _level2_preprocess_text(user_answer)
                exact_match_found = False
                if not contradiction_detected:
                    for alt in alternatives:
                        alt_norm = _level2_preprocess_text(str(alt))
                        if user_norm == alt_norm:
                            is_correct = True
                            method = 'exact_match_alternative'
                            confidence = 1.0
                            exact_match_found = True
                            print(f"   [EXACT MATCH] Found exact match in alternatives")
                            break
                
                if not exact_match_found and not contradiction_detected:
                    # Use ONLY LLM judge - no semantic similarity fallback
                    # Ensure Ollama is running and available
                    _init_llm_judge()
                    
                    if not LLM_JUDGE_AVAILABLE:
                        print(f"   [ERROR] Ollama is not available! Please ensure Ollama is running.")
                        print(f"   [ERROR] Start Ollama with: ollama serve")
                        print(f"   [ERROR] Or set OLLAMA_URL environment variable if running on different host/port")
                        is_correct = False
                        method = 'llm_unavailable_error'
                        confidence = 0.0
                    else:
                        # Use LLM judge to evaluate logical correctness
                        # Check against main answer first
                        llm_correct_main, llm_confidence_main, llm_reasoning_main = _llm_judge_logical_correctness(
                            user_answer=user_answer,
                            correct_answer=correct_answer,
                            question_text=question_text,
                            key_ideas=key_ideas
                        )
                        
                        # Only check alternatives if main answer check succeeded
                        if llm_reasoning_main != "llm_unavailable" and llm_reasoning_main != "api_error":
                            # Also check against alternatives to find best match (limit to first 5 to avoid too many API calls)
                            best_llm_match = None
                            best_confidence = llm_confidence_main
                            checked_alts = 0
                            max_alt_checks = min(5, len(alternatives))  # Limit to first 5 alternatives
                            
                            for alt in alternatives[:max_alt_checks]:
                                checked_alts += 1
                                alt_llm_correct, alt_llm_confidence, alt_reasoning = _llm_judge_logical_correctness(
                                    user_answer=user_answer,
                                    correct_answer=str(alt),
                                    question_text=question_text,
                                    key_ideas=key_ideas
                                )
                                if alt_reasoning != "llm_unavailable" and alt_reasoning != "api_error":
                                    if alt_llm_correct and alt_llm_confidence > best_confidence:
                                        best_confidence = alt_llm_confidence
                                        best_llm_match = (alt_llm_correct, alt_llm_confidence, alt_reasoning)
                                else:
                                    # If API error, stop checking alternatives
                                    break
                            
                            # Use the best match (main answer or alternative)
                            if best_llm_match and best_llm_match[1] > llm_confidence_main:
                                llm_correct, llm_confidence, llm_reasoning = best_llm_match
                                print(f"   [LLM JUDGE] Using best alternative match (confidence: {llm_confidence:.3f})")
                            else:
                                llm_correct, llm_confidence, llm_reasoning = llm_correct_main, llm_confidence_main, llm_reasoning_main
                            
                            print(f"   [LLM JUDGE] Result: {'CORRECT' if llm_correct else 'WRONG'} (confidence: {llm_confidence:.3f})")
                            print(f"   [LLM JUDGE] Reasoning: {llm_reasoning[:150]}...")
                            
                            # Use LLM judgment (lower threshold for Q3)
                            if llm_confidence >= 0.5:
                                is_correct = llm_correct
                                method = f'llm_judge_{"correct" if llm_correct else "wrong"}'
                                confidence = llm_confidence
                                print(f"   [LLM JUDGE] Applied LLM judgment (confidence >= 0.5)")
                            else:
                                # Low LLM confidence - mark as wrong
                                is_correct = False
                                method = 'llm_judge_low_confidence'
                                confidence = llm_confidence
                                print(f"   [LLM JUDGE] Low confidence ({llm_confidence:.3f}), marking as wrong")
                        else:
                            # LLM API error
                            print(f"   [ERROR] Ollama API error: {llm_reasoning_main}")
                            print(f"   [ERROR] Please check that Ollama is running and the model is available")
                            is_correct = False
                            method = 'llm_api_error'
                            confidence = 0.0
                
                # Store evaluation details
                details[question_id] = {
                    'correct': is_correct,
                    'user_answer': user_answer,
                    'correct_answer': correct_answer,
                    'evaluation_method': method,
                    'confidence': confidence if 'confidence' in locals() else 0.0
                }
            else:
                # For all other short_answer questions (NOT Q3), use rule-based logic ONLY
                # NO ML model - only exact match and keyword matching
                user_normalized = _level2_preprocess_text(user_answer)
                correct_normalized = _level2_preprocess_text(correct_answer)
                
                # Check exact match first
                if user_normalized == correct_normalized:
                    is_correct = True
                else:
                    # Rule-based keyword matching (primary method)
                    correct_words = correct_normalized.split()
                    keyword_match_success = False
                    
                    if len(correct_words) > 0:
                        keyword_ratio = sum(1 for word in correct_words if word in user_normalized) / len(correct_words)
                        if keyword_ratio >= 0.8:
                            is_correct = True
                            keyword_match_success = True
                        else:
                            # Check alternatives for keyword match
                            alternatives = question.get('alternatives', [])
                            for alt in alternatives:
                                alt_normalized = _level2_preprocess_text(str(alt))
                                alt_words = alt_normalized.split()
                                if len(alt_words) > 0:
                                    alt_keyword_ratio = sum(1 for word in alt_words if word in user_normalized) / len(alt_words)
                                    if alt_keyword_ratio >= 0.8:
                                        is_correct = True
                                        keyword_match_success = True
                                        break
                    
                    # NO ML semantic similarity for non-Q3 questions - rule-based only
        
        elif question_type == 'fill_blank' or question_type == 'fill-missing-word':
            user_normalized = _level2_preprocess_text(user_answer)
            correct_normalized = _level2_preprocess_text(correct_answer)
            
            if user_normalized == correct_normalized:
                is_correct = True
            else:
                alternatives = question.get('alternatives', [])
                for alt in alternatives:
                    alt_normalized = _level2_preprocess_text(str(alt))
                    if user_normalized == alt_normalized:
                        is_correct = True
                        break
        
        # 6. Match speaker to role: dictionary mapping must match exactly
        # RULE-BASED ONLY - No ML model used for Q4
        # Level 2 Q4 has 3 sub-questions (3 speakers), each worth 1 mark (total 3 marks)
        elif question_type == 'match-speaker-role' or question_type == 'match_speaker_role':
            # Answer is a dictionary mapping speakers to roles
            correct_mapping = question.get('answer', {})
            if isinstance(correct_mapping, dict):
                # User answer should also be a dictionary
                user_mapping = {}
                
                # Parse user input: can be dict, JSON string, or other format
                if isinstance(user_answer, dict):
                    user_mapping = user_answer
                elif isinstance(user_answer, str):
                    # Try to parse as JSON first
                    try:
                        import json
                        user_mapping = json.loads(user_answer)
                    except:
                        # If not JSON, treat as empty (will fail validation)
                        user_mapping = {}
                
                # Debug logging for Q4
                if question_id == "4":
                    print(f"[DEBUG] Q4 Match Speaker Role Evaluation:")
                    print(f"  User answer (raw): {user_answer}")
                    print(f"  User mapping: {user_mapping}")
                    print(f"  Correct mapping: {correct_mapping}")
                    print(f"  User mapping length: {len(user_mapping)}, Correct mapping length: {len(correct_mapping)}")
                
                # For Level 2 Q4: Calculate partial marks (3 sub-questions, 1 mark each)
                # Count how many speaker-role pairs match correctly
                correct_pairs = 0
                total_pairs = len(correct_mapping)
                incorrect_mappings = []
                missing_speakers = []
                extra_speakers = []
                
                if len(user_mapping) > 0:
                    # Check each speaker in correct mapping
                    for correct_speaker, correct_role in correct_mapping.items():
                        user_role = user_mapping.get(correct_speaker)
                        if user_role is not None:
                            # Compare with stripped strings to handle whitespace differences
                            if str(user_role).strip() == str(correct_role).strip():
                                correct_pairs += 1
                            else:
                                incorrect_mappings.append({
                                    'speaker': correct_speaker,
                                    'user_role': str(user_role).strip(),
                                    'correct_role': str(correct_role).strip()
                                })
                        else:
                            missing_speakers.append(correct_speaker)
                    
                    # Check for extra speakers in user mapping
                    for user_speaker in user_mapping.keys():
                        if user_speaker not in correct_mapping:
                            extra_speakers.append(user_speaker)
                    
                    # If normalized comparison needed (fallback)
                    if correct_pairs < total_pairs:
                        user_mapping_norm = {}
                        for user_spk, user_rl in user_mapping.items():
                            user_spk_norm = _level2_preprocess_text(str(user_spk))
                            user_rl_norm = _level2_preprocess_text(str(user_rl))
                            user_mapping_norm[user_spk_norm] = user_rl_norm
                        
                        correct_mapping_norm = {}
                        for correct_speaker, correct_role in correct_mapping.items():
                            correct_speaker_norm = _level2_preprocess_text(str(correct_speaker))
                            correct_role_norm = _level2_preprocess_text(str(correct_role))
                            correct_mapping_norm[correct_speaker_norm] = correct_role_norm
                        
                        # Recalculate with normalized comparison
                        correct_pairs_norm = 0
                        for correct_speaker_norm, correct_role_norm in correct_mapping_norm.items():
                            user_role_norm = user_mapping_norm.get(correct_speaker_norm)
                            if user_role_norm == correct_role_norm:
                                correct_pairs_norm += 1
                        
                        # Use normalized count if it's better
                        if correct_pairs_norm > correct_pairs:
                            correct_pairs = correct_pairs_norm
                
                # Calculate marks: Q4 has 3 marks total (1 mark per correct pair)
                # For Level 2 Q4: 3 marks = 3 correct pairs
                marks_earned = correct_pairs
                total_marks = total_pairs  # Should be 3 for Level 2 Q4
                
                # Question is fully correct only if all pairs match
                is_correct = (correct_pairs == total_pairs and total_pairs > 0)
                
                if question_id == "4":
                    print(f"  Q4 Marks: {marks_earned}/{total_marks} (correct pairs: {correct_pairs}/{total_pairs})")
                    if is_correct:
                        print(f"  ✅ Q4 marked as CORRECT (all {total_pairs} pairs match)")
                    else:
                        print(f"  ⚠️ Q4 partial marks: {marks_earned}/{total_marks}")
            else:
                # Fallback: treat as simple string match
                user_normalized = _level2_preprocess_text(str(user_answer))
                correct_normalized = _level2_preprocess_text(str(correct_mapping))
                if user_normalized == correct_normalized:
                    is_correct = True
        
        # Store detailed information (same format as Level 1)
        # Handle correct_answer display (convert array/dict to string for display)
        # Skip if details already stored (e.g., for Question 3 with ML evaluation)
        if question_id not in details:
            if isinstance(correct_answer, (list, dict)):
                correct_answer_display = str(correct_answer)
            else:
                correct_answer_display = correct_answer
            
            # For Level 2 Q4, store marks information
            if question_id == "4" and question_type in ['match-speaker-role', 'match_speaker_role']:
                # Ensure variables exist (they should be set in the match_speaker_role block above)
                q4_marks_earned = marks_earned if 'marks_earned' in locals() else (3 if is_correct else 0)
                q4_total_marks = total_marks if 'total_marks' in locals() else 3
                q4_incorrect_mappings = incorrect_mappings if 'incorrect_mappings' in locals() else []
                q4_missing_speakers = missing_speakers if 'missing_speakers' in locals() else []
                q4_extra_speakers = extra_speakers if 'extra_speakers' in locals() else []
                
                details[question_id] = {
                    'correct': is_correct,
                    'user_answer': str(user_answer) if user_answer else '',
                    'correct_answer': correct_answer_display,
                    'marks_earned': q4_marks_earned,
                    'total_marks': q4_total_marks,
                    'incorrect_mappings': q4_incorrect_mappings,
                    'missing_speakers': q4_missing_speakers,
                    'extra_speakers': q4_extra_speakers
                }
                # Add marks to score (not just 1 for correct)
                score += q4_marks_earned
            else:
                details[question_id] = {
                    'correct': is_correct,
                    'user_answer': str(user_answer) if user_answer else '',
                    'correct_answer': correct_answer_display
                }
                if is_correct:
                    score += 1
    
    # ====================================================================
    # Level 2 Accuracy Calculation and Promotion Decision
    # ====================================================================
    # Calculate accuracy: correct_answers / total_questions
    accuracy = (score / total * 100) if total > 0 else 0.0
    
    # Promotion decision rules:
    # - accuracy >= 70% → Promote to Level 3
    # - accuracy < 70% → Remain Intermediate
    promotion_status = "promoted" if accuracy >= 70.0 else "intermediate"
    # ====================================================================
    
    return {
        'score': score,
        'total': total,
        'accuracy': round(accuracy, 2),
        'promotion_status': promotion_status,
        'details': details
    }


# ============================================================================
# LEVEL 3 EVALUATION (Stricter evaluation - Level 3 ONLY)
# ============================================================================
# Level 3 requires stricter evaluation rules:
# - MCQ: exact match
# - Emotion & ending: exact match
# - Topic & fill phrase: keyword + semantic similarity
# - Event ordering: strict sequence match
# ============================================================================

def _compute_semantic_similarity_simple(text1: str, text2: str) -> float:
    """
    Compute semantic similarity using ML model (if available).
    Returns similarity score between 0 and 1.
    Level 3 ONLY - for topic and fill phrase questions.
    Reuses existing helper function.
    """
    return _compute_semantic_similarity(text1, text2)


def evaluate_level3(user_responses, reference_questions, audio_transcript=""):
    """
    Evaluate Level 3 user answers against reference questions.
    Stricter evaluation rules for advanced level.
    
    Evaluation rules:
    - MCQ: exact match
    - Emotion & ending: exact match
    - Topic & fill phrase: keyword + semantic similarity
    - Event ordering: strict sequence match
    
    Args:
        user_responses: Dictionary mapping question_id to user_answer
        reference_questions: List of question dictionaries with id, type, answer/correctAnswer, etc.
        audio_transcript: Full audio transcript text (for Q4 evaluation)
    
    Returns:
        dict: {
            'score': int,
            'total': int,
            'details': {
                question_id: {
                    'correct': bool,
                    'user_answer': str,
                    'correct_answer': str
                }
            }
        }
        (Same format as Level 1)
    """
    details = {}
    score = 0
    total = len(reference_questions)
    
    for question in reference_questions:
        question_id = question.get('id')
        user_answer = (user_responses.get(question_id) or '').strip()
        correct_answer = (question.get('answer') or question.get('correctAnswer') or '').strip()
        question_type = question.get('type', '')
        question_text = question.get('question', '')
        
        is_correct = False
        
        # ====================================================================
        # MCQ: Exact match (normalized)
        # ====================================================================
        if question_type == 'mcq':
            user_normalized = normalize_text(user_answer)
            correct_normalized = normalize_text(correct_answer)
            
            if user_normalized == correct_normalized:
                is_correct = True
            else:
                # Check alternatives if they exist
                alternatives = question.get('alternatives', [])
                for alt in alternatives:
                    alt_normalized = normalize_text(str(alt))
                    if user_normalized == alt_normalized:
                        is_correct = True
                        break
        
        # ====================================================================
        # Emotion & Ending: Exact match (normalized)
        # ====================================================================
        elif question_type == 'short_answer' and (
            'உணர்ச்சி' in question_text or 'emotion' in question_text.lower() or
            'கடைசி' in question_text or 'ending' in question_text.lower() or
            'last' in question_text.lower()
        ):
            user_normalized = normalize_text(user_answer)
            correct_normalized = normalize_text(correct_answer)
            
            # Exact match
            if user_normalized == correct_normalized:
                is_correct = True
            else:
                # Check alternatives
                alternatives = question.get('alternatives', [])
                for alt in alternatives:
                    alt_normalized = normalize_text(str(alt))
                    if user_normalized == alt_normalized:
                        is_correct = True
                        break
        
        # ====================================================================
        # Topic & Fill Phrase: Keyword + Semantic Similarity
        # ====================================================================
        elif (question_type == 'short_answer' and (
            'தலைப்பு' in question_text or 'topic' in question_text.lower()
        )) or question_type == 'fill_blank' or question_type == 'fill-missing-word':
            user_normalized = normalize_text(user_answer)
            correct_normalized = normalize_text(correct_answer)
            
            # First check keyword matching
            correct_words = correct_normalized.split()
            keyword_match = all(word in user_normalized for word in correct_words) if correct_words else False
            
            if keyword_match:
                is_correct = True
            else:
                # Check exact match
                if user_normalized == correct_normalized:
                    is_correct = True
                else:
                    # Check alternatives for keyword match
                    alternatives = question.get('alternatives', [])
                    for alt in alternatives:
                        alt_normalized = normalize_text(str(alt))
                        alt_words = alt_normalized.split()
                        if alt_words and all(word in user_normalized for word in alt_words):
                            is_correct = True
                            break
                        elif user_normalized == alt_normalized:
                            is_correct = True
                            break
                    
                    # If keyword match fails, try semantic similarity
                    if not is_correct:
                        semantic_sim = _compute_semantic_similarity_simple(user_answer, correct_answer)
                        # Require both keyword presence and high semantic similarity
                        if semantic_sim > 0.75:
                            # Check if at least some keywords are present
                            keyword_ratio = sum(1 for word in correct_words if word in user_normalized) / len(correct_words) if correct_words else 0
                            if keyword_ratio >= 0.5:  # At least 50% keywords present
                                is_correct = True
        
        # ====================================================================
        # Event Ordering: Strict Sequence Match
        # ====================================================================
        elif question_type == 'ordering':
            # Get correct order (can be array or string)
            correct_order = question.get('answer', [])
            if isinstance(correct_order, str):
                correct_order = [item.strip() for item in correct_order.split(',')]
            
            # Split user input by commas and normalize
            user_order = [normalize_text(item.strip()) for item in user_answer.split(',') if item.strip()]
            correct_order_normalized = [normalize_text(str(item)) for item in correct_order]
            
            # Strict sequence match: must have same length and exact order
            if len(user_order) == len(correct_order_normalized):
                # All positions must match exactly
                matches = sum(1 for i in range(len(user_order)) 
                            if user_order[i] == correct_order_normalized[i])
                if matches == len(user_order):
                    is_correct = True
            # If lengths don't match, it's incorrect (strict)
        
        # ====================================================================
        # Default: Fallback to exact match
        # ====================================================================
        else:
            user_normalized = normalize_text(user_answer)
            correct_normalized = normalize_text(correct_answer)
            
            if user_normalized == correct_normalized:
                is_correct = True
            else:
                alternatives = question.get('alternatives', [])
                for alt in alternatives:
                    alt_normalized = normalize_text(str(alt))
                    if user_normalized == alt_normalized:
                        is_correct = True
                        break
        
        # Store detailed information (same format as Level 1)
        details[question_id] = {
            'correct': is_correct,
            'user_answer': user_answer,
            'correct_answer': correct_answer
        }
        
        if is_correct:
            score += 1
    
    return {
        'score': score,
        'total': total,
        'details': details
    }


# ============================================================================
# LEVEL 3 ADVANCED EVALUATION (ML/DL Components - Level 3 ONLY)
# ============================================================================
# This section contains advanced evaluation logic EXCLUSIVELY for Level 3.
# Level 1 and Level 2 evaluation logic remains unchanged above.
# ============================================================================

# Global ML model cache (loaded only when needed for Level 3)
_level3_model = None

def _load_level3_model():
    """
    Load ML model for Level 3 evaluation (lazy loading).
    Only loads when Level 3 evaluation is called.
    """
    global _level3_model
    if _level3_model is None and ML_AVAILABLE:
        try:
            # Use a lightweight multilingual model for Tamil support
            _level3_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            print("Level 3 ML model loaded successfully.")
        except Exception as e:
            print(f"Warning: Could not load Level 3 ML model: {e}")
            _level3_model = False  # Mark as unavailable
    return _level3_model


# ============================================================================
# LLM-AS-A-JUDGE (Logical Correctness Evaluation)
# ============================================================================
# This section provides LLM-based logical correctness checking for borderline cases.
# Supports Ollama (local) and OpenAI API.
# ============================================================================

# LLM configuration
LLM_JUDGE_AVAILABLE = False
LLM_JUDGE_TYPE = None  # 'ollama' or 'openai'
LLM_JUDGE_URL = None
LLM_JUDGE_MODEL = None

def _init_llm_judge():
    """
    Initialize LLM judge configuration from environment variables.
    Checks for Ollama or OpenAI API availability.
    """
    global LLM_JUDGE_AVAILABLE, LLM_JUDGE_TYPE, LLM_JUDGE_URL, LLM_JUDGE_MODEL
    
    import os
    
    # Check for Ollama (local)
    ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
    ollama_model = os.getenv('OLLAMA_MODEL', 'llama3.2:latest')  # Use available model
    
    # Check for OpenAI API
    openai_api_key = os.getenv('OPENAI_API_KEY', '')
    openai_model = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
    
    # Try Ollama first (preferred for local use)
    try:
        import requests
        test_response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        if test_response.status_code == 200:
            # Verify the model is available
            models_response = requests.get(f"{ollama_url}/api/tags", timeout=5)
            if models_response.status_code == 200:
                models_data = models_response.json()
                available_models = [m.get('name', '') for m in models_data.get('models', [])]
                if ollama_model in available_models or any(ollama_model.split(':')[0] in m for m in available_models):
                    LLM_JUDGE_AVAILABLE = True
                    LLM_JUDGE_TYPE = 'ollama'
                    LLM_JUDGE_URL = ollama_url
                    LLM_JUDGE_MODEL = ollama_model
                    print(f"✓ LLM Judge initialized: Ollama at {ollama_url} with model {ollama_model}")
                    return
                else:
                    print(f"⚠ Warning: Model {ollama_model} not found in Ollama. Available models: {', '.join(available_models[:3])}...")
                    print(f"⚠ Please pull the model: ollama pull {ollama_model}")
        else:
            print(f"⚠ Ollama API returned status {test_response.status_code}. Is Ollama running?")
    except requests.exceptions.ConnectionError:
        print(f"⚠ Cannot connect to Ollama at {ollama_url}. Is Ollama running?")
        print(f"⚠ Start Ollama with: ollama serve")
    except Exception as e:
        print(f"⚠ Error checking Ollama: {e}")
    
    # Fallback to OpenAI if available
    if openai_api_key:
        LLM_JUDGE_AVAILABLE = True
        LLM_JUDGE_TYPE = 'openai'
        LLM_JUDGE_MODEL = openai_model
        print(f"LLM Judge initialized: OpenAI API with model {openai_model}")
        return
    
    print("Warning: LLM Judge not available. Using fallback evaluation only.")
    LLM_JUDGE_AVAILABLE = False


def _llm_judge_logical_correctness(
    user_answer: str,
    correct_answer: str,
    question_text: str = "",
    key_ideas: List = None,
    audio_transcript: str = ""
) -> Tuple[bool, float, str]:
    """
    Use LLM to judge if user's answer is logically correct compared to expected answer.
    
    Args:
        user_answer: User's answer in Tamil
        correct_answer: Expected correct answer in Tamil
        question_text: The question text (optional, for context)
        key_ideas: List of key ideas that should be present (optional)
    
    Returns:
        Tuple of (is_correct: bool, confidence: float, reasoning: str)
        If LLM is unavailable, returns (False, 0.0, "llm_unavailable")
    """
    global LLM_JUDGE_AVAILABLE, LLM_JUDGE_TYPE, LLM_JUDGE_URL, LLM_JUDGE_MODEL
    
    if not LLM_JUDGE_AVAILABLE:
        _init_llm_judge()
    
    if not LLM_JUDGE_AVAILABLE:
        return False, 0.0, "llm_unavailable"
    
    try:
        import requests
        import json
        
        # Build key ideas context
        key_ideas_text = ""
        if key_ideas:
            key_ideas_list = []
            for idea in key_ideas:
                if isinstance(idea, dict):
                    tamil_text = idea.get('tamil', '')
                    if tamil_text:
                        key_ideas_list.append(tamil_text)
                else:
                    key_ideas_list.append(str(idea))
            if key_ideas_list:
                key_ideas_text = "\nமுக்கிய கருத்துக்கள் (Key Ideas):\n" + "\n".join(f"- {idea}" for idea in key_ideas_list)
        
        # Create Tamil-specific prompt for STRICT logical evaluation
        # Check if this is an audio summary question (Level 3 Q4) - OLD question type
        # Check if this is an achievements question (Level 3 Q4) - NEW question type
        is_summary_question = ("சுருக்கம்" in question_text or "summary" in question_text.lower() or "transcript" in question_text.lower()) and "சாதனைகள்" not in question_text and "முன்னேற்றங்கள்" not in question_text
        is_achievements_question = "சாதனைகள்" in question_text or "முன்னேற்றங்கள்" in question_text or "achievements" in question_text.lower() or "successes" in question_text.lower()
        
        if is_summary_question:
            # Special prompt for audio summary evaluation
            # Include full audio transcript if available
            transcript_text = ""
            if audio_transcript:
                transcript_text = f"""
**முழு ஒலிப்பதிவின் உரை (Full Audio Transcript):**
{audio_transcript}

"""
            
            prompt = f"""நீங்கள் ஒரு தமிழ் மொழி ஒலிப்பதிவு மதிப்பீட்டாளர். பயனரின் பதிலை மதிப்பீடு செய்யவும்.

🚨🚨🚨 மிக முக்கியமானது - முதலில் இதை சரிபாருங்க! 🚨🚨🚨

**எதிர்மறை/முரண்பாடு சரிபார்ப்பு (CONTRADICTION CHECK - DO THIS FIRST!):**
- ஒலிப்பதிவை கவனமாக படித்து, பயனரின் பதிலில் எதிரான தகவல் உள்ளதா சரிபாருங்க!
- **ஒரு முரண்பாடு மட்டும் இருந்தாலும், பதில் தவறு! தொடர்பு இருந்தாலும் தவறு!**
- ஒலிப்பதிவு "மக்கள் ஓட்டு போடுகிறார்கள்" என்று கூறினால், பயனரின் பதில் "வாக்களிப்பதே இல்லை" என்றால் → **"is_correct": false (தவறு!)**
- ஒலிப்பதிவு "ஏழைகள் ஏழையாகவே" என்று கூறினால், பயனரின் பதில் "ஏழைகள் செல்வந்தர்களாகி விட்டனர்" என்றால் → **"is_correct": false (தவறு!)**
- ஒலிப்பதிவு "கியூவில் நிற்கிறார்கள்" என்று கூறினால், பயனரின் பதில் "வரிசையில் நிற்க வேண்டியதில்லை" என்றால் → **"is_correct": false (தவறு!)**
- ஒலிப்பதிவு "முன்னேற்றம் உள்ளது" (62.5%, 7-வது இடத்திலிருந்து 5-வது) என்று கூறினால், பயனரின் பதில் "எந்த முன்னேற்றமும் இல்லை" என்றால் → **"is_correct": false (தவறு!)**

**✗ தவறான பதிலின் எடுத்துக்காட்டு (WRONG ANSWER EXAMPLE):**
பயனரின் பதில்: "தேர்தலில் மக்கள் வாக்களிப்பதே இல்லை என்று பேச்சாளர் கூறுகிறார். ஆட்சியில் ஏழைகள் அனைவரும் செல்வந்தர்களாகி விட்டனர் என்று கூறப்படுகிறது. மக்கள் அரிசி, மண்ணெண்ணெய் எதற்கும் வரிசையில் நிற்க வேண்டியதில்லை என்று சொல்கிறார். கல்வி மற்றும் தொழில் துறைகளில் எந்த முன்னேற்றமும் இல்லை என்று பேச்சாளர் கூறுகிறார்."
→ **இந்த பதில் ஒலிப்பதிவுக்கு முழுமையாக எதிரானது! ஒலிப்பதிவு "மக்கள் ஓட்டு போடுகிறார்கள்", "ஏழைகள் ஏழையாகவே", "கியூவில் நிற்கிறார்கள்", "முன்னேற்றம் உள்ளது" என்று கூறுகிறது! "is_correct": false!**

⚠️ முக்கியமானது: பயனர் பின்வரும் வடிவங்களில் எதையும் எழுதலாம்:
- ஒலிப்பதிவின் நேரடி உரை/டிரான்ஸ்கிரிப்ட் (transcript)
- ஒலிப்பதிவிலிருந்து புரிந்து கொண்டது (understanding)
- ஒலிப்பதிவின் கருத்து/புள்ளி (point/idea)
- ஒலிப்பதிவு குறித்த கருத்து/கருத்து (opinion)
- ஒலிப்பதிவின் சுருக்கம் (summary)

⚠️ முக்கியமானது: ஒலிப்பதிவுடன் முற்றிலும் தொடர்பில்லாத (totally unrelated) உள்ளடக்கம் மட்டுமே தவறு!
⚠️ **மிக முக்கியமானது: ஒலிப்பதிவுக்கு எதிரான (contradictory) தகவல் இருந்தால், தொடர்பு இருந்தாலும் தவறு!**

{transcript_text}கேள்வி: {question_text if question_text else "கேள்வி வழங்கப்படவில்லை"}
{key_ideas_text}

எதிர்பார்க்கப்படும் சரியான பதில் (எடுத்துக்காட்டு):
{correct_answer}

பயனரின் பதில்:
{user_answer}

மதிப்பீட்டு வழிமுறைகள் (Audio Content Evaluation):
1. **ஒலிப்பதிவுடன் தொடர்பு (Relevance to Audio)**: பயனரின் பதில் ஒலிப்பதிவின் உள்ளடக்கத்துடன் தொடர்புடையதா?
   - ✓ சரியானது: ஒலிப்பதிவின் உரை, சுருக்கம், புரிதல், கருத்து, கருத்து - எதுவாக இருந்தாலும்
   - ✗ தவறு: ஒலிப்பதிவுடன் முற்றிலும் தொடர்பில்லாத விஷயம் (completely unrelated topic)

2. **கேள்வியை திருப்திப்படுத்துகிறதா? (Satisfies Question)**: பயனரின் பதில் கேள்வியை திருப்திப்படுத்துகிறதா?
   - ஒலிப்பதிவின் உரை/டிரான்ஸ்கிரிப்ட் எழுதினாலும் சரி
   - புரிந்து கொண்டதை எழுதினாலும் சரி
   - கருத்து/கருத்து எழுதினாலும் சரி

3. **உண்மையான உள்ளடக்கம் (True Content)**: பயனரின் பதில் ஒலிப்பதிவில் உள்ள உண்மையான உள்ளடக்கத்தை பிரதிபலிக்கிறதா?
   - ஒலிப்பதிவில் இல்லாத தவறான தகவல் இருந்தால் தவறு
   - ஆனால் ஒலிப்பதிவின் உரையை நேரடியாக எழுதினால் சரி

4. **எதிர்மறை/முரண்பாடு சரிபார்ப்பு (CRITICAL - CONTRADICTION CHECK - CHECK THIS FIRST!):** 
   - **முதலில் ஒலிப்பதிவை கவனமாக படித்து, பயனரின் பதிலில் எதிரான தகவல் உள்ளதா சரிபாருங்க!**
   - பயனரின் பதில் ஒலிப்பதிவில் கூறப்பட்டதற்கு எதிரான (contradictory) தகவலைக் கொண்டிருந்தால் → **"is_correct": false (தவறு!)**
   - **ஒரு முரண்பாடு (contradiction) மட்டும் இருந்தாலும், பதில் தவறு!**
   - எடுத்துக்காட்டு: ஒலிப்பதிவு "மக்கள் ஓட்டு போடுகிறார்கள்" என்றால், பயனரின் பதில் "மக்கள் வாக்களிப்பதே இல்லை" என்றால் → **தவறு!**
   - எடுத்துக்காட்டு: ஒலிப்பதிவு "பணக்காரர்கள் மேலும் பணக்காரர்கள், ஏழைகள் ஏழையாகவே" என்றால், பயனரின் பதில் "ஏழைகள் அனைவரும் செல்வந்தர்களாகி விட்டனர்" என்றால் → **தவறு!**
   - எடுத்துக்காட்டு: ஒலிப்பதிவு "மக்கள் கியூவில் நிற்கிறார்கள்" என்றால், பயனரின் பதில் "வரிசையில் நிற்க வேண்டியதில்லை" என்றால் → **தவறு!**
   - எடுத்துக்காட்டு: ஒலிப்பதிவு "முன்னேற்றம் உள்ளது" (62.5%, 7-வது இடத்திலிருந்து 5-வது) என்றால், பயனரின் பதில் "எந்த முன்னேற்றமும் இல்லை" என்றால் → **தவறு!**

**மதிப்பீடு (CHECK IN THIS EXACT ORDER - DO NOT SKIP STEP 1!):**
1. **முதலில் எதிர்மறை/முரண்பாடு சரிபார்ப்பு (MANDATORY FIRST STEP - THIS OVERRIDES EVERYTHING!):**
   - ஒலிப்பதிவை கவனமாக படித்து, பயனரின் பதிலில் எதிரான தகவல் உள்ளதா சரிபாருங்க!
   - பயனரின் பதில் ஒலிப்பதிவுக்கு எதிரானதா? → **ஆம்** → **"is_correct": false (தவறு!) - STOP HERE, DO NOT CHECK RELEVANCE!**
   - பயனரின் பதில் ஒலிப்பதிவுக்கு எதிரானதா? → **இல்லை** → Step 2 க்கு செல்லுங்கள்
   - **ஒரு முரண்பாடு மட்டும் இருந்தாலும், பதில் தவறு! தொடர்பு இருந்தாலும் தவறு!**
   - **முரண்பாடு இருந்தால், "is_correct" எப்போதும் false! confidence எந்த அளவு இருந்தாலும் தவறு!**

2. **அடுத்து தொடர்பு சரிபார்ப்பு (ONLY IF NO CONTRADICTIONS):**
   - ஒலிப்பதிவுடன் குறைந்தது 20% தொடர்பு (at least 20% relevance) இருந்தால் → "is_correct": true
   - ஒலிப்பதிவுடன் முற்றிலும் தொடர்பில்லாததாக இருந்தால் மட்டும் → "is_correct": false
   - பயனர் எழுதியது ஒலிப்பதிவின் உரை, சுருக்கம், புரிதல், கருத்து, கருத்து - எதுவாக இருந்தாலும், ஒலிப்பதிவுடன் குறைந்தது 20% தொடர்பு இருந்தால் சரியானது!

எடுத்துக்காட்டுகள்:
- ✓ சரியானது: ஒலிப்பதிவின் நேரடி உரை/டிரான்ஸ்கிரிப்ட்
- ✓ சரியானது: "மக்கள் தேர்தலில் நம்பிக்கையுடன் ஓட்டு போடுகிறார்கள், ஆனால் ஏமாற்றமடைகிறார்கள்"
- ✓ சரியானது: "பேச்சாளர் தன் ஆட்சியின் முன்னேற்றங்களை கூறுகிறார்"
- ✓ சரியானது: "இந்த ஒலிப்பதிவு தேர்தல் மற்றும் ஆட்சி பற்றி பேசுகிறது"
- ✓ சரியானது: "பேட்டியில் பேச்சாளர், தேர்தல்களில் மக்கள் நம்பிக்கையுடன் வாக்களித்தாலும் இறுதியில் அவர்களுக்கு ஏமாற்றமும் அதிருப்தியுமே மிஞ்சுகிறது எனக் கூறுகிறார். பணக்காரர்கள் மேலும் பணக்காரர்களாகவும், ஏழைகள் இன்னும் ஏழைகளாகவும் இருப்பது சமூக சமத்துவமின்மையை வெளிப்படுத்துகிறது." (புரிதல்/கருத்து - ஒலிப்பதிவுடன் தொடர்புடையது!)
- ✗ தவறு: "இன்று வானிலை நன்றாக இருக்கிறது" (ஒலிப்பதிவுடன் தொடர்பில்லாதது)
- ✗ தவறு: "கணிதம் கற்றுக்கொள்வது முக்கியம்" (ஒலிப்பதிவுடன் தொடர்பில்லாதது)
- ✗ தவறு: "தேர்தலில் மக்கள் வாக்களிப்பதே இல்லை" (ஒலிப்பதிவுக்கு எதிரானது - ஒலிப்பதிவு "மக்கள் ஓட்டு போடுகிறார்கள்" என்று கூறுகிறது!)
- ✗ தவறு: "ஏழைகள் அனைவரும் செல்வந்தர்களாகி விட்டனர்" (ஒலிப்பதிவுக்கு எதிரானது - ஒலிப்பதிவு "ஏழைகள் ஏழையாகவே" என்று கூறுகிறது!)
- ✗ தவறு: "மக்கள் வரிசையில் நிற்க வேண்டியதில்லை" (ஒலிப்பதிவுக்கு எதிரானது - ஒலிப்பதிவு "கியூவில் நிற்கிறார்கள்" என்று கூறுகிறது!)
- ✗ தவறு: "கல்வி மற்றும் தொழில் துறைகளில் எந்த முன்னேற்றமும் இல்லை" (ஒலிப்பதிவுக்கு எதிரானது - ஒலிப்பதிவு "62.5%", "7-வது இடத்திலிருந்து 5-வது" என்று கூறுகிறது!)
- ✗ **தவறு**: "தேர்தலில் மக்கள் வாக்களிப்பதே இல்லை என்று பேச்சாளர் கூறுகிறார். ஆட்சியில் ஏழைகள் அனைவரும் செல்வந்தர்களாகி விட்டனர் என்று கூறப்படுகிறது. மக்கள் அரிசி, மண்ணெண்ணெய் எதற்கும் வரிசையில் நிற்க வேண்டியதில்லை என்று சொல்கிறார். கல்வி மற்றும் தொழில் துறைகளில் எந்த முன்னேற்றமும் இல்லை என்று பேச்சாளர் கூறுகிறார்."
  → **இந்த பதில் ஒலிப்பதிவுக்கு முழுமையாக எதிரானது! ஒலிப்பதிவு "மக்கள் ஓட்டு போடுகிறார்கள்", "ஏழைகள் ஏழையாகவே", "கியூவில் நிற்கிறார்கள்", "முன்னேற்றம் உள்ளது" என்று கூறுகிறது! "is_correct": false!**

பதில் JSON வடிவத்தில் மட்டும் கொடுக்கவும்:
{{
    "is_correct": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "காரணம் (Tamil) - ஒலிப்பதிவுடன் தொடர்பு உள்ளதா/இல்லையா என்பதை விளக்கவும்"
}}

JSON மட்டும்:"""
        elif is_achievements_question:
            # Special prompt for achievements/successes evaluation - check for AT LEAST 3 achievements
            # Include full audio transcript if available
            transcript_text = ""
            if audio_transcript:
                transcript_text = f"""
**முழு ஒலிப்பதிவின் உரை (Full Audio Transcript):**
{audio_transcript}

"""
            
            prompt = f"""நீங்கள் ஒரு தமிழ் மொழி ஒலிப்பதிவு மதிப்பீட்டாளர். பயனரின் பதிலை மதிப்பீடு செய்யவும்.

⚠️ முக்கியமானது: இந்த கேள்வி பேச்சாளர் கூறிய சாதனைகளில் குறைந்தது 3 விஷயங்களைக் குறிப்பிட வேண்டும்!

{transcript_text}கேள்வி: {question_text if question_text else "கேள்வி வழங்கப்படவில்லை"}
{key_ideas_text}

எதிர்பார்க்கப்படும் சரியான பதில் (எடுத்துக்காட்டு):
{correct_answer}

பயனரின் பதில்:
{user_answer}

மதிப்பீட்டு வழிமுறைகள் (3 Achievements Evaluation):
1. **மூன்று சாதனைகள் (3 Achievements)**: பயனரின் பதில் பேச்சாளர் கூறிய சாதனைகளில் குறைந்தது 3 விஷயங்களைக் குறிப்பிடுகிறதா?
   - ⚠️ **முக்கியமானது**: பதில் ஒரு வாக்கியத்தில்/ஒரு புள்ளியில் எழுதப்பட்டாலும், அது 3 சாதனைகளைக் குறிப்பிட்டால் சரியானது!
   - ✓ சரியானது: படித்தவர்களின் சதவீதம்/விகிதம் உயர்ந்தது (numbers not required, content matters)
   - ✓ சரியானது: பஞ்சம்/பட்டினி மரணம் இல்லை (numbers not required, content matters)
   - ✓ சரியானது: தொழில் தரவரிசை முன்னேற்றம்/முன்னேறியது (numbers not required, content matters)
   - ✗ தவறு: 3 க்கும் குறைவான சாதனைகள் மட்டும் குறிப்பிடப்பட்டால்

2. **உள்ளடக்கம் சரிபார்ப்பு (Content Check)**: 
   - ✓ சரியானது: எண்கள் குறிப்பிடப்படாமல், உள்ளடக்கம் மட்டும் குறிப்பிடப்பட்டால் சரியானது!
   - ✗ தவறு: எண்கள் தவறாகக் கூறப்பட்டால் (62.5% vs 100%, 7-5 vs 1) தவறு! எண்கள் குறிப்பிடப்பட்டால், அவை சரியாக இருக்க வேண்டும்!
   - ✗ தவறு: பேச்சாளர் கூறாத சாதனைகள் அல்லது ஒலிப்பதிவுக்கு எதிரான தகவல்

3. **எதிர்மறை/முரண்பாடு சரிபார்ப்பு (CRITICAL - CONTRADICTION CHECK!):** 
   - பயனரின் பதில் ஒலிப்பதிவில் கூறப்பட்டதற்கு எதிரான (contradictory) தகவலைக் கொண்டிருந்தால் → **"is_correct": false**
   - **ஒரு முரண்பாடு மட்டும் இருந்தாலும், 3 சாதனைகள் குறிப்பிடப்பட்டாலும், பதில் தவறு!**
   - எடுத்துக்காட்டு: ஒலிப்பதிவு "உயர்ந்தது" என்று கூறினால், பயனரின் பதில் "குறைந்தது" என்றால் → **தவறு!**
   - எடுத்துக்காட்டு: ஒலிப்பதிவு "முன்னேற்றம்" என்று கூறினால், பயனரின் பதில் "தோல்வி" என்றால் → **தவறு!**
   - **🚨 மிக முக்கியமானது**: ஒலிப்பதிவு "ஏழைகள் ஏழையாகவே" / "ஏழங்க இன்னும் ஏழை ஆயிட்டே இருக்காங்க" / "பணக்காரர்கள் மேலும் பணக்காரர்கள், ஏழைகள் இன்னும் ஏழைகள்" என்று கூறினால், பயனரின் பதில் "ஏழ்மை முழுசா ஒழிஞ்சிடுச்சு" / "ஏழ்மை ஒழிந்தது" / "ஏழைகள் செல்வந்தர்களாகி விட்டனர்" / "ஏழைகள் அனைவரும் செல்வந்தர்களாகி விட்டனர்" என்றால் → **தவறு! (முரண்பாடு! ஒலிப்பதிவு ஏழைகள் இன்னும் ஏழைகள் என்று கூறுகிறது, ஆனால் பயனர் ஏழ்மை ஒழிந்தது என்று கூறுகிறார் - இது முழுமையாக எதிரானது!)**
   - எடுத்துக்காட்டு: ஒலிப்பதிவு "62.5%" என்று கூறினால், பயனரின் பதில் "100%" என்றால் → **தவறு! எண்கள் தவறாகக் கூறப்பட்டால் தவறு!**
   - எடுத்துக்காட்டு: ஒலிப்பதிவு "7-வது இடத்திலிருந்து 5-வது" என்று கூறினால், பயனரின் பதில் "1-வது" என்றால் → **தவறு! எண்கள் தவறாகக் கூறப்பட்டால் தவறு!**
   - **முக்கியமானது**: எண்கள் குறிப்பிடப்படாமல், உள்ளடக்கம் மட்டும் குறிப்பிடப்பட்டால் (உயர்ந்தது, முன்னேற்றம்) → **சரியானது**
   - **முக்கியமானது**: எண்கள் குறிப்பிடப்பட்டால், அவை சரியாக இருக்க வேண்டும்! தவறான எண்கள் → **தவறு!**
   - **முக்கியமானது**: உள்ளடக்கமே எதிரானதாக இருந்தால் (ஏழ்மை ஒழிந்தது vs ஏழைகள் ஏழையாகவே) → **தவறு!**

**மதிப்பீடு (CHECK IN THIS EXACT ORDER - DO NOT SKIP ANY STEP!):**
1. **முதலில் எதிர்மறை/முரண்பாடு சரிபார்ப்பு**: பயனரின் பதில் ஒலிப்பதிவுக்கு எதிரானதா? → **ஆம்** → **"is_correct": false (தவறு!) - STOP HERE!**
2. **அடுத்து எண்கள் சரிபார்ப்பு**: பயனரின் பதிலில் எண்கள் குறிப்பிடப்பட்டுள்ளனவா?
   - எண்கள் குறிப்பிடப்பட்டால், அவை சரியாக இருக்க வேண்டும்!
   - ஒலிப்பதிவு "62.5%" என்றால், பயனர் "100%" என்றால் → **"is_correct": false (தவறு!)**
   - ஒலிப்பதிவு "7-வது இடத்திலிருந்து 5-வது" என்றால், பயனர் "1-வது" என்றால் → **"is_correct": false (தவறு!)**
   - எண்கள் குறிப்பிடப்படாமல், உள்ளடக்கம் மட்டும் இருந்தால் → Step 3 க்கு செல்லுங்கள்
3. **அடுத்து 3 சாதனைகள் சரிபார்ப்பு**: பயனரின் பதில் குறைந்தது 3 சாதனைகளைக் குறிப்பிடுகிறதா?
   - ✓ ஆம் (3 அல்லது அதற்கு மேற்பட்டவை) → "is_correct": true
   - ✗ இல்லை (3 க்கும் குறைவானவை) → "is_correct": false

⚠️ **முக்கியமானது**: எண்கள் (62.5%, 7-வது, 5-வது) குறிப்பிடப்படாமல், உள்ளடக்கம் மட்டும் குறிப்பிடப்பட்டாலும் சரியானது!
⚠️ **முக்கியமானது**: எண்கள் தவறாகக் கூறப்பட்டால் (எ.கா. 100% instead of 62.5%, 1-வது instead of 7-5), அது தவறு! எண்கள் குறிப்பிடப்பட்டால், அவை சரியாக இருக்க வேண்டும்!

எடுத்துக்காட்டுகள்:
- ✓ சரியானது: "படித்தவர்களின் சதவீதம் உயர்ந்தது, பஞ்சம் மரணம் இல்லை, தொழில் தரவரிசை முன்னேற்றம்" (3 achievements, no numbers - OK!)
- ✓ சரியானது: "கல்வி விகிதம் உயர்ந்தது, பட்டினி மரணம் இல்லை, தொழில் முன்னேறியது" (3 achievements, no numbers - OK!)
- ✓ சரியானது: "படித்தவர்களின் சதவீதம் 62.5% ஆக உயர்ந்தது, பஞ்சம் இல்லை, தொழில் தரவரிசை 7-வது இடத்திலிருந்து 5-வது" (3 achievements, correct numbers - OK!)
- ✓ சரியானது: "படித்தவர்களின் சதவீதம் உயர்ந்தது, பஞ்சம் மரணம் இல்லை, தொழில் தரவரிசை முன்னேற்றம்" (3 achievements in one sentence, no numbers - OK!)
- ✗ தவறு: "படித்தவர்களின் விகிதம் 60% ஆக உயர்ந்தது, பஞ்சம் இல்லை, தொழில் தரவரிசை 8-வது இடத்திலிருந்து 6-வது" (3 achievements, but wrong numbers - WRONG!)
- ✗ தவறு: "படித்தவர்களின் சதவீதம் 100% ஆக உயர்ந்தது, தொழில் தரவரிசை 1-வது இடத்துக்கு முன்னேறியது, பஞ்சம் இல்லை" (3 achievements, but wrong numbers - WRONG!)
- ✗ தவறு: "படித்தவர்களின் விகிதம் உயர்ந்தது, பஞ்சம் இல்லை" (only 2 achievements, need 3)
- ✗ தவறு: "கல்வி விகிதம் குறைந்தது" (contradictory - says decreased instead of increased)
- ✗ தவறு: "ஏழ்மை முழுசா ஒழிஞ்சிடுச்சு" (contradictory - audio says "ஏழைகள் ஏழையாகவே", not eliminated!)
- ✗ தவறு: "ஏழைகள் அனைவரும் செல்வந்தர்களாகி விட்டனர்" (contradictory - audio says "ஏழைகள் இன்னும் ஏழைகள்"!)

பதில் JSON வடிவத்தில் மட்டும் கொடுக்கவும்:
{{
    "is_correct": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "காரணம் (Tamil) - 3 சாதனைகள் குறிப்பிடப்பட்டனவா, ஒலிப்பதிவுக்கு எதிரானதா என்பதை விளக்கவும்"
}}

JSON மட்டும்:"""
        else:
            # Standard prompt for other questions
            prompt = f"""நீங்கள் ஒரு தமிழ் மொழி கேள்வி-பதில் மதிப்பீட்டாளர். பயனரின் பதிலை மதிப்பீடு செய்யவும்.

🚨🚨🚨 மிக முக்கியமானது - முதலில் இதை சரிபாருங்க! 🚨🚨🚨

**எதிர்மறை vs நேர்மறை சரிபார்ப்பு (NEGATION CHECK - DO THIS FIRST!):**
- எதிர்பார்க்கப்படும் பதில் "செய்வார்" (will do) / "நல்லது செய்வார்" (will do good) என்றால்
- பயனரின் பதில் "செய்ய மாட்டார்கள்" (won't do) / "நன்மை செய்ய மாட்டார்கள்" (won't do good) / "எந்த நன்மையும் செய்ய மாட்டார்கள்" (won't do any good) என்றால்
→ **இது தவறு! "is_correct": false**

**நம்பிக்கை vs நினைத்து சரிபார்ப்பு (HOPE vs THINKING CHECK - DO THIS SECOND!):**
- எதிர்பார்க்கப்படும் பதில் "நம்பிக்கையால்" (with hope/trust) என்றால்
- பயனரின் பதில் "நினைத்து" (thinking) / "எண்ணத்தில்" (in thought) / "நினைத்தார்கள்" (they thought) / "நினைத்ததால்" (because they thought) என்றால்
→ **இது தவறு! "is_correct": false**

**🚨 மிக முக்கியமான எடுத்துக்காட்டு:**
- எதிர்பார்க்கப்படும்: "நல்லது செய்வார் என்ற நம்பிக்கையால்"
- பயனரின் பதில்: "எந்த நன்மையும் செய்ய மாட்டார்கள் என்று நினைத்ததால்"
→ **இது முழுமையாக எதிரானது! "மாட்டார்கள்" (won't) vs "செய்வார்" (will), "நினைத்ததால்" (because they thought) vs "நம்பிக்கையால்" (with hope)! "is_correct": false!**

⚠️ **விதிவிலக்கு (EXCEPTION)**: பயனரின் பதில் "நினைத்து" / "நினைச்சுத்தான்" என்றாலும், அது "நல்லது செய்யணும்" / "நல்லது நடக்கும்" / "ஏதாவது நல்லது செய்வார்கள்" போன்ற நேர்மறை எதிர்பார்ப்பை (positive expectation) வெளிப்படுத்தினால், அது "நம்பிக்கையால்" போன்றதே! இந்த வழக்கில் → **"is_correct": true**
- எடுத்துக்காட்டு: "நல்லது செய்யணும்னு நினைச்சுத்தான் வாக்களித்தாங்க" = "நம்பிக்கையால் ஓட்டு போடுகிறார்கள்" (இரண்டும் ஒரே கருத்து!)

⚠️ முக்கியமானது: சொற்களின் ஒற்றுமை (word similarity) அல்ல, தருக்கரீதியான கருத்து (logical meaning) மட்டுமே முக்கியம்!

⚠️ முக்கியமானது: வார்த்தை வரிசை (word order) மாறுபட்டாலும், அதே கருத்தை வெளிப்படுத்தினால் அது சரியானது! எடுத்துக்காட்டு: "குழாய் உடைந்து தண்ணீர் நிரம்பியது" = "தண்ணீர் நிரம்பியது; காரணம் குழாய் உடைந்தது" (இரண்டும் ஒரே கருத்து!)

கேள்வி: {question_text if question_text else "கேள்வி வழங்கப்படவில்லை"}
{key_ideas_text}

எதிர்பார்க்கப்படும் சரியான பதில்:
{correct_answer}

பயனரின் பதில்:
{user_answer}

கண்டிப்பான மதிப்பீட்டு வழிமுறைகள்:
1. **கேள்விக்கு பொருத்தமானதா? (Relevance)**: பயனரின் பதில் கேள்விக்கு பொருத்தமானதா? கேள்வி கேட்கும் விஷயத்தை பயனர் பதிலளித்தாரா?
2. **கேள்வியை திருப்திப்படுத்துகிறதா? (Satisfies Question)**: பயனரின் பதில் கேள்வியை முழுமையாக திருப்திப்படுத்துகிறதா?
3. **சரியானது/உண்மையானது? (Correct/True)**: பயனரின் பதில் சரியானதா? உண்மையான தகவலை கொண்டுள்ளதா? **வார்த்தை வரிசை மாறுபட்டாலும், அதே கருத்தை வெளிப்படுத்தினால் சரியானது!**
4. **தருக்கரீதியான கருத்து சரிபார்ப்பு**: பயனரின் பதில் எதிர்பார்க்கப்படும் பதிலின் தருக்கரீதியான கருத்தை பிரதிபலிக்கிறதா? (சொற்கள் ஒரே மாதிரி இருந்தாலும், கருத்து எதிரானதாக இருந்தால் தவறு!)
5. **எதிர்மறை/நிராகரிப்பு சரிபார்ப்பு (CRITICAL - CHECK THIS FIRST!)**: 
   - எதிர்பார்க்கப்படும் பதில் நேர்மறை (positive) என்றால், பயனரின் பதில் எதிர்மறை (negative) இருந்தால் தவறு!
   - எதிர்பார்க்கப்படும் பதில் எதிர்மறை என்றால், பயனரின் பதில் நேர்மறை இருந்தால் தவறு!
   - எடுத்துக்காட்டு: "செய்வார்" (will do) vs "செய்ய மாட்டார்" (won't do) - இது தவறு!
   - எடுத்துக்காட்டு: "நன்மை செய்வார்" (will do good) vs "நன்மை செய்ய மாட்டார்கள்" (won't do good) - இது தவறு!
   - எடுத்துக்காட்டு: "எந்த நன்மையும் செய்ய மாட்டார்கள்" (won't do any good) vs "நல்லது செய்வார்" (will do good) - இது தவறு!
6. **நம்பிக்கை vs நினைத்து/எண்ணம் (CRITICAL - CHECK THIS SECOND!)**: 
   - "நம்பிக்கையால்" (with hope/trust) vs "நினைத்து/எண்ணத்தில்/நினைத்தார்கள்" (thinking/thought) - இவை எதிரான கருத்துக்கள்!
   - எதிர்பார்க்கப்படும் பதில் "நம்பிக்கையால்" என்றால், பயனரின் பதில் "நினைத்து/எண்ணத்தில்" இருந்தால் தவறு!
   - **ஆனால் விதிவிலக்கு**: பயனரின் பதில் "நினைத்து" என்றாலும், அது "நல்லது செய்யணும்" / "நல்லது நடக்கும்" / "ஏதாவது நல்லது செய்வார்கள்" போன்ற நேர்மறை எதிர்பார்ப்பை வெளிப்படுத்தினால், அது "நம்பிக்கையால்" போன்றதே! இந்த வழக்கில் சரியானது!
   - எடுத்துக்காட்டு: "நம்பிக்கையால் ஓட்டு போடுகிறார்கள்" vs "நினைத்து வாக்களித்தனர்" (எதிர்மறை கருத்துடன்) - இது தவறு!
   - எடுத்துக்காட்டு: "நம்பிக்கையால் ஓட்டு போடுகிறார்கள்" vs "நல்லது செய்யணும்னு நினைச்சுத்தான் வாக்களித்தாங்க" (நேர்மறை எதிர்பார்ப்புடன்) - இது சரியானது!
7. **முக்கிய கருத்துக்கள்**: முக்கிய கருத்துக்கள் (key ideas) பயனரின் பதிலில் உள்ளனவா?
8. **ஒரு சொல் மாற்றம்**: பதில் 95% ஒரே மாதிரி இருந்தாலும், ஒரு சொல் மட்டும் மாறி முழு கருத்தையும் எதிராக மாற்றினால், அது தவறு!

**மதிப்பீடு (CHECK IN THIS ORDER):**
1. **முதலில் எதிர்மறை/நிராகரிப்பு சரிபார்ப்பு**: எதிர்பார்க்கப்படும் பதில் நேர்மறை என்றால், பயனரின் பதில் எதிர்மறை இருந்தால் → "is_correct": false (தவறு!)
2. **அடுத்து நம்பிக்கை vs நினைத்து சரிபார்ப்பு**: எதிர்பார்க்கப்படும் பதில் "நம்பிக்கையால்" என்றால், பயனரின் பதில் "நினைத்து/எண்ணத்தில்" இருந்தால் → "is_correct": false (தவறு!)
3. **பிறகு மூன்றும் (Relevance + Satisfies + Correct)**: மூன்றும் சரியாக இருந்தால் → "is_correct": true
- எந்த ஒன்று தவறாக இருந்தாலும் "is_correct": false
- **வார்த்தை வரிசை மாறுபட்டாலும், அதே கருத்தை வெளிப்படுத்தினால் சரியானது!**
- **பயனரின் பதில் எதிர்பார்க்கப்படும் பதிலை விட முழுமையாக இருந்தாலும் (கூடுதல் விவரங்கள் சேர்த்தாலும்), அது சரியானது!**
- **ஆனால் எதிர்மறை vs நேர்மறை, நம்பிக்கை vs நினைத்து - இவை எதிரான கருத்துக்கள், தவறு!**

எடுத்துக்காட்டுகள்:
- சரியானது: "மக்கள் நம்பிக்கையால் ஓட்டு போடுகிறார்கள்" (Relevant + Satisfies + Correct)
- சரியானது: "குழாய் உடைந்து தண்ணீர் நிரம்பியது" = "தண்ணீர் நிரம்பியது; காரணம் குழாய் உடைந்தது" (வார்த்தை வரிசை வேறு, ஆனால் ஒரே கருத்து!)
- சரியானது: "குழாய் உடைந்து தண்ணீர் நிரம்பியது" = "குழாய் பழுதால் தண்ணீர் நிரம்பியதுதான் அவர் சோகமாக இருந்ததற்கான காரணம்" (முழுமையான பதில் - கேள்விக்கு நேரடியாக பதிலளிக்கிறது!)
- **தவறு**: "அவர்கள் நமக்கு நல்லது செய்ய மாட்டார்கள் என்ற எண்ணத்தில் வாக்களித்தார்கள்" (Relevant + Satisfies, ஆனால் Correct இல்லை - எதிர்மறை "மாட்டார்கள்" vs நேர்மறை "செய்வார்", மற்றும் "எண்ணத்தில்" vs "நம்பிக்கையால்"!)
- **தவறு**: "அவர்கள் நமக்கு எந்த நன்மையும் செய்ய மாட்டார்கள் என்று நினைத்து வாக்களித்தனர்" (Relevant + Satisfies, ஆனால் Correct இல்லை - எதிர்மறை "மாட்டார்கள்" vs நேர்மறை "செய்வார்", மற்றும் "நினைத்து" vs "நம்பிக்கையால்"!)
  → **இந்த பதில் எதிர்பார்க்கப்படும் பதிலுக்கு எதிரானது! "is_correct": false**
- **சரியானது**: "நமக்கு ஏதாவது நல்லது செய்யணும்னு நினைச்சுத்தான் அவங்க வாக்களித்தாங்க" (Relevant + Satisfies + Correct - "நல்லது செய்யணும்" என்ற நேர்மறை எதிர்பார்ப்பு, "நினைச்சுத்தான்" என்றாலும் நம்பிக்கையை வெளிப்படுத்துகிறது!)
- தவறு: "மக்கள் நம்பிக்கை இல்லாமல் ஓட்டு போடுகிறார்கள்" (Relevant + Satisfies, ஆனால் Correct இல்லை - எதிர்மறை!)
- தவறு: "மக்கள் நினைத்தார்கள் ஓட்டு போடுவார்கள்" (Relevant, ஆனால் Correct இல்லை - சந்தேகம் vs நம்பிக்கை!)

பதில் JSON வடிவத்தில் மட்டும் கொடுக்கவும்:
{{
    "is_correct": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "காரணம் (Tamil) - Relevance, Satisfies Question, Correctness ஆகியவற்றை விளக்கவும்"
}}

JSON மட்டும்:"""

        if LLM_JUDGE_TYPE == 'ollama':
            # Use Ollama API
            response = requests.post(
                f"{LLM_JUDGE_URL}/api/generate",
                json={
                    "model": LLM_JUDGE_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Low temperature for consistent evaluation
                        "num_predict": 500
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                llm_response = result.get('response', '').strip()
            else:
                # Don't spam errors - only log once per session
                if response.status_code == 404:
                    # Mark LLM as unavailable to prevent further calls
                    LLM_JUDGE_AVAILABLE = False
                    print(f"Ollama API not available (404). Falling back to semantic similarity.")
                else:
                    print(f"Ollama API error: {response.status_code}")
                return False, 0.0, "api_error"
        
        elif LLM_JUDGE_TYPE == 'openai':
            # Use OpenAI API
            import os
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                return False, 0.0, "no_api_key"
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": LLM_JUDGE_MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a Tamil language answer evaluator. Respond ONLY with valid JSON."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.1,
                    "max_tokens": 500
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                llm_response = result['choices'][0]['message']['content'].strip()
            else:
                print(f"OpenAI API error: {response.status_code}")
                return False, 0.0, "api_error"
        else:
            return False, 0.0, "unknown_type"
        
        # Parse JSON response
        # Try to extract JSON from response (in case LLM adds extra text)
        import re
        json_match = re.search(r'\{[^{}]*"is_correct"[^{}]*\}', llm_response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
        else:
            # Try to find JSON block
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', llm_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = llm_response
        
        try:
            result = json.loads(json_str)
            is_correct = bool(result.get('is_correct', False))
            confidence = float(result.get('confidence', 0.5))
            reasoning = str(result.get('reasoning', 'No reasoning provided'))
            
            # Clamp confidence to [0, 1]
            confidence = max(0.0, min(1.0, confidence))
            
            return is_correct, confidence, reasoning
        except json.JSONDecodeError as e:
            print(f"LLM Judge JSON parse error: {e}")
            print(f"LLM response: {llm_response[:200]}")
            return False, 0.0, "json_parse_error"
    
    except Exception as e:
        print(f"LLM Judge error: {e}")
        import traceback
        traceback.print_exc()
        return False, 0.0, f"error: {str(e)}"


def _compute_semantic_similarity(text1: str, text2: str) -> float:
    """
    Compute semantic similarity between two texts using sentence embeddings.
    Returns similarity score between 0 and 1.
    Level 3 ONLY - ML/DL component.
    """
    model = _load_level3_model()
    if not model:
        return 0.0
    
    try:
        if not NUMPY_AVAILABLE:
            return 0.0
        
        embeddings = model.encode([text1, text2], convert_to_numpy=True)
        # Compute cosine similarity
        dot_product = np.dot(embeddings[0], embeddings[1])
        norm1 = np.linalg.norm(embeddings[0])
        norm2 = np.linalg.norm(embeddings[1])
        similarity = dot_product / (norm1 * norm2) if (norm1 * norm2) > 0 else 0.0
        return float(similarity)
    except Exception as e:
        print(f"Error computing semantic similarity: {e}")
        return 0.0


def _ml_answer_correctness_classifier(
    user_answer: str,
    correct_answer: str,
    semantic_similarity: float,
    question_type: str
) -> Tuple[bool, float]:
    """
    ML-based answer correctness classifier for ambiguous short answers.
    Level 3 ONLY - ML/DL component.
    
    Returns: (is_correct, confidence_score)
    """
    if not ML_AVAILABLE:
        return False, 0.0
    
    # Rule-based features
    normalized_user = normalize_text(user_answer)
    normalized_correct = normalize_text(correct_answer)
    exact_match = normalized_user == normalized_correct
    
    # Keyword matching
    correct_words = normalized_correct.split()
    keyword_match_ratio = sum(1 for word in correct_words if word in normalized_user) / len(correct_words) if correct_words else 0.0
    
    # ML decision logic
    confidence = 0.0
    is_correct = False
    
    if exact_match:
        is_correct = True
        confidence = 1.0
    elif semantic_similarity > 0.85:
        # High semantic similarity - likely correct
        is_correct = True
        confidence = semantic_similarity
    elif semantic_similarity > 0.70 and keyword_match_ratio >= 0.6:
        # Moderate similarity with good keyword coverage
        is_correct = True
        confidence = (semantic_similarity + keyword_match_ratio) / 2
    elif semantic_similarity > 0.75:
        # High similarity alone
        is_correct = True
        confidence = semantic_similarity
    else:
        # Low similarity - likely incorrect
        is_correct = False
        confidence = semantic_similarity
    
    return is_correct, confidence


def _ml_proficiency_classifier(
    accuracy: float,
    avg_semantic_similarity: float,
    time_taken: Optional[float] = None
) -> Dict[str, any]:
    """
    ML Proficiency Classifier for Level 3.
    Predicts: Intermediate vs Advanced proficiency.
    Level 3 ONLY - ML/DL component.
    
    Returns:
        {
            'proficiency': 'Advanced' | 'Intermediate',
            'confidence': float,
            'features': dict
        }
    """
    # Feature engineering
    features = {
        'accuracy': accuracy,
        'semantic_similarity': avg_semantic_similarity,
        'time_efficiency': 1.0 if (time_taken and time_taken < 300) else 0.5  # < 5 min is efficient
    }
    
    # Weighted scoring
    accuracy_weight = 0.4
    similarity_weight = 0.3
    time_weight = 0.3
    
    proficiency_score = (
        (features['accuracy'] / 100) * accuracy_weight +
        features['semantic_similarity'] * similarity_weight +
        features['time_efficiency'] * time_weight
    )
    
    # Classification threshold
    if proficiency_score >= 0.75:
        proficiency = 'Advanced'
        confidence = proficiency_score
    else:
        proficiency = 'Intermediate'
        confidence = 1.0 - proficiency_score
    
    return {
        'proficiency': proficiency,
        'confidence': round(confidence, 3),
        'features': features,
        'proficiency_score': round(proficiency_score, 3)
    }


def evaluate_level3(
    user_responses: Dict[str, str],
    reference_questions: List[Dict],
    audio_transcript: str = "",
    time_taken: Optional[float] = None
) -> Dict:
    """
    Advanced evaluation for Level 3 ONLY.
    Uses ML/DL components: semantic similarity, answer correctness classifier, proficiency classifier.
    
    Question types handled:
    - Emotion MCQ: Exact matching
    - Conversation topic (short_answer): Keyword + semantic similarity
    - Dialogue ending (short_answer): Exact + semantic similarity
    - Order events (ordering): Sequence matching
    - Fill missing phrase (fill_blank): Semantic validation
    
    Args:
        user_responses: Dictionary mapping question_id to user_answer
        reference_questions: List of question dictionaries
        time_taken: Optional time taken in seconds
    
    Returns:
        dict: {
            'score': int,
            'total': int,
            'accuracy': float,
            'details': {
                question_id: {
                    'correct': bool,
                    'user_answer': str,
                    'correct_answer': str,
                    'semantic_similarity': float,
                    'method': str,
                    'confidence': float
                }
            },
            'proficiency': {
                'proficiency': 'Advanced' | 'Intermediate',
                'confidence': float,
                'features': dict
            },
            'avg_semantic_similarity': float
        }
    """
    details = {}
    score = 0
    total = len(reference_questions)
    semantic_similarities = []
    
    for question in reference_questions:
        question_id = question.get('id')
        user_answer = user_responses.get(question_id, '').strip()
        correct_answer = question.get('answer') or question.get('correctAnswer', '')
        question_type = question.get('type', '')
        
        is_correct = False
        method = 'rule-based'
        confidence = 0.0
        semantic_similarity = 0.0
        
        # ====================================================================
        # RULE-BASED NLP EVALUATION (Level 3)
        # ====================================================================
        
        # 1. Emotion MCQ: Exact matching (normalized)
        if question_type == 'mcq':
            user_normalized = normalize_text(user_answer)
            correct_normalized = normalize_text(correct_answer)
            
            if user_normalized == correct_normalized:
                is_correct = True
                method = 'exact_match'
                confidence = 1.0
            else:
                # Check alternatives
                alternatives = question.get('alternatives', [])
                for alt in alternatives:
                    alt_normalized = normalize_text(str(alt))
                    if user_normalized == alt_normalized:
                        is_correct = True
                        method = 'exact_match_alternative'
                        confidence = 1.0
                        break
        
        # 2. Dialogue ending identification: Exact + semantic similarity
        elif question_type == 'short_answer' and 'கடைசி' in question.get('question', ''):
            user_normalized = normalize_text(user_answer)
            correct_normalized = normalize_text(correct_answer)
            
            # Exact match first
            if user_normalized == correct_normalized:
                is_correct = True
                method = 'exact_match'
                confidence = 1.0
            else:
                # ML: Semantic similarity for dialogue ending
                semantic_similarity = _compute_semantic_similarity(user_answer, correct_answer)
                semantic_similarities.append(semantic_similarity)
                
                is_correct, confidence = _ml_answer_correctness_classifier(
                    user_answer, correct_answer, semantic_similarity, question_type
                )
                method = 'ml_semantic' if semantic_similarity > 0.7 else 'rule_based'
        
        # 3. Generic short_answer (including Q1 - why people vote): Semantic similarity + logical checking
        elif question_type == 'short_answer':
            user_normalized = normalize_text(user_answer)
            correct_normalized = normalize_text(correct_answer)
            question_text = question.get('question_text_tamil', '') or question.get('question', '')
            
            # For Q1, use ONLY LLM judge FIRST - check logical opposition before exact match
            if question_id == '1':
                # Pre-check: Rule-based contradiction detection BEFORE LLM
                user_lower = user_answer.lower()
                correct_lower = correct_answer.lower()
                
                # Check for negation mismatch
                negation_words = ['மாட்டார்கள்', 'மாட்டார்', 'மாட்டான்', 'மாட்டாள்', 'இல்லை', 'செய்யாது', 'செய்யார்']
                positive_words = ['செய்வார்', 'செய்வார்கள்', 'செய்வான்', 'செய்வாள்', 'செய்யும்', 'செய்கிறார்கள்']
                
                user_has_negation = any(neg in user_answer for neg in negation_words)
                correct_has_positive = any(pos in correct_answer for pos in positive_words)
                
                # Check for hope vs thinking mismatch
                hope_words = ['நம்பிக்கை', 'நம்பிக்கையால்', 'நம்புகிறார்கள்']
                thinking_words = ['நினைத்து', 'நினைத்தார்கள்', 'நினைத்ததால்', 'எண்ணத்தில்', 'சந்தேகம்']
                
                user_has_thinking = any(think in user_answer for think in thinking_words)
                correct_has_hope = any(hope in correct_answer for hope in hope_words)
                
                # If user has negation AND correct has positive → WRONG
                if user_has_negation and correct_has_positive:
                    print(f"   [RULE-BASED Q1] Detected negation mismatch: user has negation, correct has positive → WRONG")
                    is_correct = False
                    method = 'rule_based_negation_mismatch'
                    confidence = 0.0
                # If user has thinking AND correct has hope → WRONG (unless user also has positive expectation)
                elif user_has_thinking and correct_has_hope:
                    # Exception: if user says "நல்லது செய்யணும்" with "நினைத்து", it's OK
                    positive_expectation_words = ['நல்லது செய்யணும்', 'நல்லது நடக்கும்', 'ஏதாவது நல்லது']
                    user_has_positive_expectation = any(exp in user_answer for exp in positive_expectation_words)
                    
                    if not user_has_positive_expectation:
                        print(f"   [RULE-BASED Q1] Detected hope vs thinking mismatch: user has thinking, correct has hope → WRONG")
                        is_correct = False
                        method = 'rule_based_hope_thinking_mismatch'
                        confidence = 0.0
                    else:
                        print(f"   [RULE-BASED Q1] Exception: user has thinking but with positive expectation → proceed to LLM")
                        # Continue to LLM check
                else:
                    print(f"   [RULE-BASED Q1] No obvious contradiction detected → proceed to LLM")
                    # Continue to LLM check
                
                # If rule-based check didn't mark as wrong, proceed to LLM
                # Only proceed if is_correct is None (not checked yet) OR if it's True
                # Do NOT proceed if rule-based check marked it as wrong
                if is_correct is None or (is_correct is not False) or (method not in ['rule_based_negation_mismatch', 'rule_based_hope_thinking_mismatch']):
                    # But skip if rule-based already marked as wrong
                    if method in ['rule_based_negation_mismatch', 'rule_based_hope_thinking_mismatch']:
                        print(f"   [RULE-BASED Q1] Skipping LLM - already marked as WRONG by rule-based check")
                    else:
                        print(f"   [LLM JUDGE Q1] Evaluating with LLM judge (ONLY METHOD - Ollama required)...")
                    
                    # Ensure Ollama is running
                    _init_llm_judge()
                    
                    if not LLM_JUDGE_AVAILABLE:
                        print(f"   [ERROR] Ollama is not available! Please ensure Ollama is running.")
                        print(f"   [ERROR] Start Ollama with: ollama serve")
                        print(f"   [ERROR] Or set OLLAMA_URL environment variable if running on different host/port")
                        is_correct = False
                        method = 'llm_unavailable_error'
                        confidence = 0.0
                    else:
                        key_ideas = question.get('key_ideas', [])
                        llm_correct, llm_confidence, llm_reasoning = _llm_judge_logical_correctness(
                            user_answer=user_answer,
                            correct_answer=correct_answer,
                            question_text=question_text,
                            key_ideas=key_ideas
                        )
                    
                    if llm_reasoning != "llm_unavailable" and llm_reasoning != "api_error":
                        print(f"   [LLM JUDGE Q1] Result: {'CORRECT' if llm_correct else 'WRONG'} (confidence: {llm_confidence:.3f})")
                        print(f"   [LLM JUDGE Q1] Reasoning: {llm_reasoning[:150]}...")
                        
                        # For Q1, LLM judge is ONLY method - use its judgment
                        # Even if exact match exists, LLM judge can override if logically wrong
                        if llm_confidence >= 0.5:  # Lower threshold for Q1
                            is_correct = llm_correct
                            method = f'llm_judge_q1_{"correct" if llm_correct else "wrong"}'
                            confidence = llm_confidence
                            print(f"   [LLM JUDGE Q1] Applied LLM judgment (confidence >= 0.5)")
                        else:
                            # Low confidence - mark as wrong
                            is_correct = False
                            method = 'llm_judge_q1_low_confidence'
                            confidence = llm_confidence
                            print(f"   [LLM JUDGE Q1] Low confidence ({llm_confidence:.3f}), marking as wrong")
                    else:
                        # LLM API error
                        print(f"   [ERROR] Ollama API error: {llm_reasoning}")
                        print(f"   [ERROR] Please check that Ollama is running and the model is available")
                        is_correct = False
                        method = 'llm_api_error'
                        confidence = 0.0
            else:
                # For other short_answer questions, check exact match first
                # Check exact match first
                if user_normalized == correct_normalized:
                    is_correct = True
                    method = 'exact_match'
                    confidence = 1.0
                else:
                    # Check alternatives for exact match
                    alternatives = question.get('alternatives', [])
                    alt_exact_match = False
                    for alt in alternatives:
                        alt_normalized = normalize_text(str(alt))
                        if user_normalized == alt_normalized:
                            is_correct = True
                            method = 'exact_match_alternative'
                            confidence = 1.0
                            alt_exact_match = True
                            break
                    
                    if not alt_exact_match:
                        # ML: Semantic similarity
                        semantic_similarity = _compute_semantic_similarity(user_answer, correct_answer)
                        semantic_similarities.append(semantic_similarity)
                        
                        # Check alternatives for semantic similarity
                        alt_semantic_similarity = 0.0
                        for alt in alternatives:
                            alt_sim = _compute_semantic_similarity(user_answer, str(alt))
                            if alt_sim > alt_semantic_similarity:
                                alt_semantic_similarity = alt_sim
                        
                        max_semantic_similarity = max(semantic_similarity, alt_semantic_similarity)
                        
                        # For other short_answer questions, use semantic similarity with threshold
                        is_correct, confidence = _ml_answer_correctness_classifier(
                            user_answer, correct_answer, max_semantic_similarity, question_type
                        )
                        method = 'ml_semantic' if max_semantic_similarity > 0.7 else 'rule_based'
                        # ALWAYS use LLM judge for logical correctness check (even high similarity)
                        # This catches cases where 95% similarity but one word changes meaning
                        print(f"   [LLM JUDGE Q{question_id}] Checking logical correctness (similarity: {max_semantic_similarity:.3f})")
                        key_ideas = question.get('key_ideas', [])
                        llm_correct, llm_confidence, llm_reasoning = _llm_judge_logical_correctness(
                            user_answer=user_answer,
                            correct_answer=correct_answer,
                            question_text=question_text,
                            key_ideas=key_ideas
                        )
                        
                        if llm_reasoning != "llm_unavailable" and llm_reasoning != "api_error":
                            print(f"   [LLM JUDGE] Result: {'CORRECT' if llm_correct else 'WRONG'} (confidence: {llm_confidence:.3f})")
                            print(f"   [LLM JUDGE] Reasoning: {llm_reasoning[:150]}...")
                            
                            # LLM judge can override semantic similarity
                            # If LLM says wrong, it's wrong (even if similarity is high)
                            if not llm_correct:
                                is_correct = False
                                method = 'llm_judge_logical_wrong'
                                confidence = 1.0 - llm_confidence  # Invert confidence for wrong answer
                                print(f"   [LLM JUDGE] Overriding high similarity ({max_semantic_similarity:.3f}) - logical meaning is wrong!")
                            # If LLM says correct and confidence is good, accept
                            elif llm_confidence >= 0.6:
                                is_correct = True
                                method = 'llm_judge_logical_correct'
                                confidence = llm_confidence
                            # If LLM confidence is low, use semantic similarity as fallback
                            else:
                                # Fallback to semantic similarity
                                if max_semantic_similarity >= 0.75:
                                    is_correct = True
                                    method = 'semantic_high_fallback'
                                    confidence = max_semantic_similarity
                                elif max_semantic_similarity >= 0.65:
                                    is_correct = True
                                    method = 'semantic_medium_fallback'
                                    confidence = max_semantic_similarity
                                else:
                                    is_correct = False
                                    method = 'semantic_low'
                                    confidence = max_semantic_similarity
                        else:
                            # LLM unavailable - use semantic similarity as fallback
                            print(f"   [LLM JUDGE] Unavailable, using semantic similarity fallback")
                            if max_semantic_similarity >= 0.75:
                                is_correct = True
                                method = 'semantic_high'
                                confidence = max_semantic_similarity
                            elif max_semantic_similarity >= 0.65:
                                is_correct = True
                                method = 'semantic_medium'
                                confidence = max_semantic_similarity
                            else:
                                is_correct, confidence = _ml_answer_correctness_classifier(
                                    user_answer, correct_answer, max_semantic_similarity, question_type
                                )
                                method = 'ml_classifier'
        
        # 4. Order events (3-4 actions): Sequence matching
        elif question_type == 'ordering':
            correct_order = question.get('answer', [])
            if isinstance(correct_order, str):
                correct_order = [item.strip() for item in correct_order.split(',')]
            
            user_order = [normalize_text(item.strip()) for item in user_answer.split(',') if item.strip()]
            correct_order_normalized = [normalize_text(str(item)) for item in correct_order]
            
            # Sequence matching: check if order matches
            if len(user_order) == len(correct_order_normalized):
                matches = sum(1 for i in range(len(user_order)) 
                            if user_order[i] == correct_order_normalized[i])
                match_ratio = matches / len(user_order) if user_order else 0
                
                if match_ratio == 1.0:
                    is_correct = True
                    method = 'sequence_match'
                    confidence = 1.0
                elif match_ratio >= 0.75:  # 75% sequence match
                    is_correct = True
                    method = 'sequence_match_partial'
                    confidence = match_ratio
            else:
                is_correct = False
                method = 'sequence_mismatch'
                confidence = 0.0
        
        # 5. Fill missing phrase / number (1-2 words): Semantic/strict validation
        elif question_type in ['fill_blank', 'fill-missing-word', 'fill_missing_phrase']:
            user_normalized = normalize_text(user_answer)
            correct_normalized = normalize_text(correct_answer)
            
            # Exact match first
            if user_normalized == correct_normalized:
                is_correct = True
                method = 'exact_match'
                confidence = 1.0
            else:
                # Check alternatives
                alternatives = question.get('alternatives', [])
                alt_match = False
                for alt in alternatives:
                    alt_normalized = normalize_text(str(alt))
                    if user_normalized == alt_normalized:
                        is_correct = True
                        method = 'exact_match_alternative'
                        confidence = 1.0
                        alt_match = True
                        break
                
                if not alt_match:
                    # If numeric-only is expected, try strict numeric compare
                    if question.get('numeric_only'):
                        try:
                            user_num = float(user_answer)
                            correct_num = float(str(correct_answer))
                            if abs(user_num - correct_num) < 1e-6:
                                is_correct = True
                                method = 'numeric_exact'
                                confidence = 1.0
                        except Exception:
                            pass
                    if not is_correct:
                        # ML: Semantic similarity for phrase validation
                        semantic_similarity = _compute_semantic_similarity(user_answer, correct_answer)
                        semantic_similarities.append(semantic_similarity)
                        
                        is_correct, confidence = _ml_answer_correctness_classifier(
                            user_answer, correct_answer, semantic_similarity, question_type
                        )
                        method = 'ml_semantic' if semantic_similarity > 0.7 else 'rule_based'
        
        # 6. Long answer: use semantic similarity + key ideas + logical content checking
        elif question_type == 'long_answer':
            user_norm = normalize_text(user_answer)
            correct_norm = normalize_text(correct_answer)
            
            print(f"\n[DEBUG Q{question_id}] Evaluating long_answer")
            print(f"   User answer length: {len(user_answer)} chars")
            print(f"   Correct answer length: {len(correct_answer)} chars")
            
            # Reject answers that are too short (likely invalid/spam)
            # For long_answer questions, minimum reasonable length is 10 characters
            if len(user_answer.strip()) < 10:
                print(f"   [REJECTED] Answer too short ({len(user_answer)} chars) - minimum 10 chars required for long_answer")
                is_correct = False
                method = 'too_short_rejected'
                confidence = 0.0
                semantic_similarities.append(0.0)
                continue  # Skip to next question
            
            # Initialize all variables first to avoid reference errors
            logical_opposition = False
            key_ideas = question.get('key_ideas', [])
            alternatives = question.get('alternatives', [])
            keyword_hits = 0
            semantic_key_idea_hits = 0
            total_key_idea_hits = 0
            semantic_similarity = 0.0
            alt_semantic_similarity = 0.0
            max_semantic_similarity = 0.0
            
            # ============================================================
            # LOGICAL CONTENT CHECKING - Check for semantic opposition
            # ============================================================
            
            # 1. Check for negation/opposition in Tamil
            negation_words = ['மாட்டார்கள்', 'மாட்டார்', 'மாட்டான்', 'மாட்டாள்', 
                            'இல்லை', 'அல்ல', 'வேண்டாம்', 'செய்யாது', 'செய்யார்',
                            'செய்யவில்லை', 'செய்யாத', 'இல்லாத', 'வராது', 'வரார்',
                            'செய்யமாட்டார்கள்', 'செய்யமாட்டார்', 'செய்யமாட்டான்',
                            'முன்னேற்றம் இல்லை', 'மாற்றம் இல்லை', 'முன்னேறவில்லை']
            
            # Positive action/achievement words
            positive_action_words = ['செய்வார்', 'செய்வார்கள்', 'செய்வான்', 'செய்வாள்',
                                   'செய்யும்', 'செய்கிறார்கள்', 'செய்கிறார்', 'செய்கிறான்',
                                   'வரும்', 'வருவார்', 'வருவார்கள்', 'வருகிறார்கள்',
                                   'முன்னேற்றம்', 'முன்னேறியது', 'உயர்ந்தது', 'வந்தது',
                                   'சாதித்தார்', 'பெற்றார்', 'ஏற்பட்டது', 'நடந்தது']
            
            user_has_negation = any(neg_word in user_answer for neg_word in negation_words)
            correct_has_negation = any(neg_word in correct_answer for neg_word in negation_words)
            user_has_positive_action = any(pos_word in user_answer for pos_word in positive_action_words)
            correct_has_positive_action = any(pos_word in correct_answer for pos_word in positive_action_words)
            
            # 2. Check for key concept words that indicate opposite meanings
            # Hope/Trust vs Doubt/Thought/Despair
            hope_words = ['நம்பிக்கை', 'நம்புகிறார்கள்', 'நம்புவார்கள்', 'நம்புகிறார்', 'நம்பிக்கையால்']
            doubt_words = ['நினைத்தார்கள்', 'நினைத்தார்', 'சந்தேகம்', 'ஐயம்', 'எண்ணம்',
                          'நம்பிக்கை இழந்தார்கள்', 'நம்பிக்கை இல்லை']
            # Note: 'ஏமாற்றம்' (disappointment) removed - it can appear with hope (hope but disappointment)
            
            user_has_hope = any(word in user_answer for word in hope_words)
            correct_has_hope = any(word in correct_answer for word in hope_words)
            user_has_doubt = any(word in user_answer for word in doubt_words)
            correct_has_doubt = any(word in correct_answer for word in doubt_words)
            
            # 3. Check for achievement vs failure indicators (for Q4 specifically)
            achievement_words = ['முன்னேற்றம்', 'உயர்ந்தது', 'வந்தது', 'சாதித்தார்', 
                               'பெற்றார்', 'ஏற்பட்டது', 'நடந்தது', 'வளர்ச்சி', 'முன்னேறியது']
            failure_words = ['தோல்வி', 'வீழ்ச்சி', 'குறைந்தது', 'இழந்தார்கள்', 'இல்லை', 
                           'செய்யவில்லை', 'நடக்கவில்லை', 'ஏற்படவில்லை']
            
            user_has_achievement = any(word in user_answer for word in achievement_words)
            correct_has_achievement = any(word in correct_answer for word in achievement_words)
            user_has_failure = any(word in user_answer for word in failure_words)
            correct_has_failure = any(word in correct_answer for word in failure_words)
            
            # 4. Logical opposition detection
            # Rule: If user has negation AND correct has positive action, they're opposite
            # Rule: If user has positive action AND correct has negation, they're opposite
            # Rule: If user has doubt/thought AND correct has hope/trust (BUT NOT if both have hope), they're opposite
            # Rule: If user has failure AND correct has achievement (for Q4), they're opposite
            # Rule: If user has achievement AND correct has failure (for Q4), they're opposite
            # IMPORTANT: Don't flag as opposite if both have the same sentiment (e.g., both mention hope and disappointment)
            
            # Check if both have hope - if so, they're likely saying the same thing (hope but disappointment)
            both_have_hope = user_has_hope and correct_has_hope
            both_have_negation = user_has_negation and correct_has_negation
            
            if user_has_negation and correct_has_positive_action and not both_have_negation:
                logical_opposition = True
            elif user_has_positive_action and correct_has_negation and not both_have_negation:
                logical_opposition = True
            elif user_has_doubt and correct_has_hope and not both_have_hope:
                logical_opposition = True
            elif user_has_hope and correct_has_doubt and not both_have_hope:
                logical_opposition = True
            elif question_id == '4' and user_has_failure and correct_has_achievement:
                logical_opposition = True
            elif question_id == '4' and user_has_achievement and correct_has_failure:
                logical_opposition = True
            # Only flag negation mismatch if one has negation and the other has positive action (not if both have negation)
            elif user_has_negation != correct_has_negation and (user_has_positive_action or correct_has_positive_action):
                logical_opposition = True
            
            # If logically opposite, reject immediately
            # BUT: Skip logical opposition check for Q4 (audio summary) - users can write understanding/opinion
            if logical_opposition and question_id != '4':
                print(f"   [OPPOSITION] LOGICAL OPPOSITION DETECTED!")
                print(f"      User negation: {user_has_negation}, Correct negation: {correct_has_negation}")
                print(f"      User positive: {user_has_positive_action}, Correct positive: {correct_has_positive_action}")
                print(f"      User hope: {user_has_hope}, Correct hope: {correct_has_hope}")
                print(f"      User doubt: {user_has_doubt}, Correct doubt: {correct_has_doubt}")
                is_correct = False
                method = 'logical_opposition_detected'
                confidence = 0.0
                semantic_similarity = _compute_semantic_similarity(user_answer, correct_answer)
                semantic_similarities.append(semantic_similarity)
                print(f"   [RESULT] Marked as WRONG due to logical opposition")
                # Don't proceed to semantic similarity checks - answer is wrong
            elif logical_opposition and question_id == '4':
                # For Q4, skip logical opposition check - let LLM judge handle it
                print(f"   [Q4] Skipping logical opposition check - using LLM judge only")
                logical_opposition = False  # Reset for Q4
            else:
                # Gather key ideas (Tamil/English)
                key_terms = []
                key_idea_texts = []  # Store full key idea texts for semantic matching
                for idea in key_ideas:
                    if isinstance(idea, dict):
                        tamil_text = str(idea.get('tamil', ''))
                        english_text = str(idea.get('english', ''))
                        if tamil_text:
                            key_terms.append(normalize_text(tamil_text))
                            key_idea_texts.append(tamil_text)
                        if english_text:
                            key_terms.append(normalize_text(english_text))
                    else:
                        idea_str = str(idea)
                        key_terms.append(normalize_text(idea_str))
                        key_idea_texts.append(idea_str)
                key_terms = [t for t in key_terms if t]
                
                # Improved keyword hit counting: check for normalized substrings AND semantic similarity
                keyword_hits = 0
                semantic_key_idea_hits = 0  # Count key ideas matched via semantic similarity
                
                for i, idea in enumerate(key_ideas):
                    idea_matched = False
                    if isinstance(idea, dict):
                        tamil_text = str(idea.get('tamil', ''))
                        if tamil_text:
                            tamil_norm = normalize_text(tamil_text)
                            # Check for exact substring match
                            if tamil_norm and tamil_norm in user_norm:
                                keyword_hits += 1
                                idea_matched = True
                            # Also check semantic similarity for synonyms
                            elif tamil_text and not idea_matched:
                                idea_similarity = _compute_semantic_similarity(user_answer, tamil_text)
                                if idea_similarity >= 0.7:  # High semantic similarity for key idea
                                    semantic_key_idea_hits += 1
                                    idea_matched = True
                    else:
                        idea_str = str(idea)
                        idea_norm = normalize_text(idea_str)
                        if idea_norm and idea_norm in user_norm:
                            keyword_hits += 1
                            idea_matched = True
                        elif idea_str and not idea_matched:
                            idea_similarity = _compute_semantic_similarity(user_answer, idea_str)
                            if idea_similarity >= 0.7:
                                semantic_key_idea_hits += 1
                                idea_matched = True
            
                # Total key idea hits (exact + semantic)
                total_key_idea_hits = keyword_hits + semantic_key_idea_hits
                
                # Semantic similarity with correct answer
                if correct_answer:
                    semantic_similarity = _compute_semantic_similarity(user_answer, correct_answer)
                    semantic_similarities.append(semantic_similarity)
                else:
                    semantic_similarity = 0.0
                
                # Check alternatives for semantic similarity
                alt_semantic_similarity = 0.0
                for alt in alternatives:
                    alt_sim = _compute_semantic_similarity(user_answer, str(alt))
                    if alt_sim > alt_semantic_similarity:
                        alt_semantic_similarity = alt_sim
                
                # Use the higher of answer or alternative similarity
                max_semantic_similarity = max(semantic_similarity, alt_semantic_similarity)
            
            # Decision rules - more lenient for Level 3 Q4 (achievements)
            # Note: logical_opposition check already happened above
            question_id = question.get('id')
            is_q4 = (question_id == '4')
            
            # Skip semantic similarity checks for Q4 - it uses ONLY LLM judge
            # For Q3 and other long_answer questions, still use semantic similarity as fallback
            if question_id != '4':
                # For Q5 (if exists): accept if 2+ key ideas are present - only if not logically opposite
                if not logical_opposition and question_id == '5' and total_key_idea_hits >= 2:
                    is_correct = True
                    method = 'keyword_pair_semantic' if semantic_key_idea_hits > 0 else 'keyword_pair'
                    confidence = 0.8
                # General: accept if enough key ideas matched - only if not logically opposite
                if not is_correct and not logical_opposition and total_key_idea_hits >= max(2, len(key_ideas) // 2):
                    is_correct = True
                    method = 'keyword_match_semantic' if semantic_key_idea_hits > 0 else 'keyword_match'
                    confidence = 0.8
                # High semantic similarity with answer or alternatives (only if not logically opposite)
                if not is_correct and not logical_opposition and max_semantic_similarity >= 0.8:
                    is_correct = True
                    method = 'semantic_high'
                    confidence = max_semantic_similarity
                # Medium semantic similarity with at least 1 key idea (only if not logically opposite)
                if not is_correct and not logical_opposition and max_semantic_similarity >= 0.65 and total_key_idea_hits >= 1:
                    is_correct = True
                    method = 'semantic_with_keywords'
                    confidence = max_semantic_similarity
                # For Q3: Special check - both words must be present AND "பஞ்சம்" must come BEFORE "பட்டினி"/"பட்ணி"
                if not is_correct and question_id == '3':
                    # Check for both required words
                    has_pancham = 'பஞ்சம்' in user_answer
                    has_pattini = 'பட்டினி' in user_answer or 'பட்ணி' in user_answer
                    
                    if has_pancham and has_pattini:
                        # Check order: "பஞ்சம்" must come BEFORE "பட்டினி"/"பட்ணி"
                        pancham_index = user_answer.find('பஞ்சம்')
                        # Find the earliest occurrence of either spelling
                        pattini_index = -1
                        if 'பட்டினி' in user_answer:
                            pattini_index = user_answer.find('பட்டினி')
                        if 'பட்ணி' in user_answer:
                            pattini_index_alt = user_answer.find('பட்ணி')
                            if pattini_index == -1 or (pattini_index_alt != -1 and pattini_index_alt < pattini_index):
                                pattini_index = pattini_index_alt
                        
                        if pancham_index != -1 and pattini_index != -1 and pancham_index < pattini_index:
                            print(f"   [Q3 EXACT PHRASE] Both words detected in correct order: பஞ்சம் ({pancham_index}) before பட்டினி/பட்ணி ({pattini_index}) → CORRECT")
                            is_correct = True
                            method = 'q3_exact_phrase_both_words_correct_order'
                            confidence = 1.0
                        else:
                            print(f"   [Q3 EXACT PHRASE] Both words present but wrong order - பஞ்சம் index: {pancham_index}, பட்டினி/பட்ணி index: {pattini_index} → WRONG")
                            is_correct = False
                            method = 'q3_wrong_order'
                            confidence = 0.0
                    else:
                        print(f"   [Q3 EXACT PHRASE] Missing words - பஞ்சம்: {has_pancham}, பட்டினி/பட்ணி: {has_pattini}")
                        # Fallback to semantic similarity if both words not present
                        if not logical_opposition and max_semantic_similarity >= 0.7 and total_key_idea_hits >= 2:
                            is_correct = True
                            method = 'semantic_q3_lenient'
                            confidence = max_semantic_similarity
            
            # ============================================================
            # LLM-AS-A-JUDGE: For Level 3 Q4 (3 Achievements) - ONLY METHOD
            # ============================================================
            # For Q4 (3 achievements), use ONLY LLM judge - content-based checking, no semantic similarity
            if question_id == '4':
                question_text = question.get('question_text_tamil', '') or question.get('question_text_english', '')
                
                # Pre-check: Count achievements FIRST - if 3+ things mentioned, mark as CORRECT (ignore wrong numbers and contradictions)
                # Check if answer mentions at least 3 achievements/points (content-based, not number-based)
                achievement_keywords = [
                    ['படித்தவர்கள்', 'சதவீதம்', 'விகிதம்', 'உயர்ந்தது', 'கல்வி', 'சதவிதம்'],  # Literacy achievement
                    ['பஞ்சம்', 'பட்டினி', 'மரணம்', 'இல்லை'],  # No famine achievement
                    ['தொழில்', 'தரவரிசை', 'முன்னேற்றம்', 'முன்னேறியது', 'இடத்துக்கு', 'இடத்திலிருந்து', 'வந்திருக்கு'],  # Industry achievement
                    ['ஏழ்மை', 'ஏழைகள்', 'வாழ்க்கைத்தரம்', 'முன்னேற்றம்']  # Additional points (even if contradictory, count as a point)
                ]
                
                achievement_count = 0
                for keywords in achievement_keywords:
                    if any(keyword in user_answer for keyword in keywords):
                        achievement_count += 1
                
                # Also check for comma-separated points (if answer has multiple clauses separated by commas)
                import re
                # Count clauses separated by commas
                clauses = re.split(r',\s*', user_answer)
                clause_count = len([c for c in clauses if len(c.strip()) > 15])  # Count meaningful clauses (at least 15 chars)
                
                # Use the higher count (keyword-based or clause-based)
                # If answer has 3+ comma-separated clauses, it likely mentions 3 things
                final_count = max(achievement_count, clause_count)
                
                print(f"   [RULE-BASED Q4] Achievement count: {achievement_count}/3, Clause count: {clause_count}, Final: {final_count}")
                
                # If 3+ things mentioned, check numbers (if mentioned) before marking as CORRECT
                if final_count >= 3:
                    print(f"   [RULE-BASED Q4] 3+ points detected → checking numbers...")
                    
                    # Check for wrong numbers (if numbers are mentioned, they must be correct)
                    has_wrong_numbers = False
                    
                    # Check for 100% (should be 62.5%)
                    if re.search(r'100\s*%|100\s*சதவீத|100\s*சதவித', user_answer, re.IGNORECASE):
                        print(f"   [RULE-BASED Q4] Wrong number detected: 100% (should be 62.5%) → WRONG")
                        has_wrong_numbers = True
                    
                    # Check for 1-வது (should be 7-5)
                    if re.search(r'1\s*[-]?வது|1\s*[-]?ம்\s*இட', user_answer, re.IGNORECASE):
                        print(f"   [RULE-BASED Q4] Wrong number detected: 1-வது (should be 7-5) → WRONG")
                        has_wrong_numbers = True
                    
                    if has_wrong_numbers:
                        # 3+ clauses but wrong numbers → WRONG
                        is_correct = False
                        method = 'rule_based_wrong_numbers'
                        confidence = 0.0
                        print(f"   [RULE-BASED Q4] 3+ clauses detected BUT wrong numbers → WRONG")
                    else:
                        # 3+ clauses and no wrong numbers (or no numbers mentioned) → CORRECT
                        is_correct = True
                        method = 'rule_based_3_achievements'
                        confidence = 0.8
                        print(f"   [RULE-BASED Q4] 3+ points detected + no wrong numbers → CORRECT")
                else:
                    print(f"   [RULE-BASED Q4] Only {final_count} points detected → proceed to LLM for detailed check")
                    # Continue to LLM check
                
                # If rule-based check already marked as correct/wrong, skip LLM
                # Otherwise, proceed to LLM for detailed evaluation
                if method == 'rule_based_3_achievements':
                    print(f"   [RULE-BASED Q4] Skipping LLM - already marked as CORRECT (3+ achievements, no wrong numbers)")
                elif method == 'rule_based_wrong_numbers':
                    print(f"   [RULE-BASED Q4] Skipping LLM - already marked as WRONG (wrong numbers detected)")
                else:
                    print(f"   [LLM JUDGE Q4] Evaluating 3 achievements with LLM judge (ONLY METHOD - Ollama required)...")
                    
                    # Use audio transcript passed from app.py
                    # audio_transcript is now passed as a parameter to evaluate_level3
                    
                    # Ensure Ollama is running
                    _init_llm_judge()
                    
                    if not LLM_JUDGE_AVAILABLE:
                        print(f"   [ERROR] Ollama is not available! Please ensure Ollama is running.")
                        print(f"   [ERROR] Start Ollama with: ollama serve")
                        print(f"   [ERROR] Or set OLLAMA_URL environment variable if running on different host/port")
                        is_correct = False
                        method = 'llm_unavailable_error'
                        confidence = 0.0
                    else:
                        llm_correct, llm_confidence, llm_reasoning = _llm_judge_logical_correctness(
                            user_answer=user_answer,
                            correct_answer=correct_answer,
                            question_text=question_text,
                            key_ideas=key_ideas,
                            audio_transcript=audio_transcript
                        )
                        
                        if llm_reasoning != "llm_unavailable" and llm_reasoning != "api_error":
                            print(f"   [LLM JUDGE Q4] Result: {'CORRECT' if llm_correct else 'WRONG'} (confidence: {llm_confidence:.3f})")
                            print(f"   [LLM JUDGE Q4] Reasoning: {llm_reasoning[:200]}...")
                            
                            # For Q4, LLM judge is ONLY method - use its judgment
                            # CRITICAL: If LLM says WRONG (due to contradictions), ALWAYS mark as wrong, regardless of confidence
                            # If LLM says CORRECT AND confidence >= 20%, mark as correct
                            if not llm_correct:
                                # LLM detected contradictions or wrong content - ALWAYS mark as wrong
                                is_correct = False
                                method = f'llm_judge_q4_wrong_contradiction'
                                confidence = llm_confidence
                                print(f"   [LLM JUDGE Q4] LLM detected contradictions/wrong content - marking as WRONG")
                                print(f"   [LLM JUDGE Q4] Reasoning: {llm_reasoning[:200]}...")
                            elif llm_confidence >= 0.2:  # 20% relevance threshold
                                is_correct = True
                                method = f'llm_judge_q4_correct'
                                confidence = llm_confidence
                                print(f"   [LLM JUDGE Q4] Applied LLM judgment (confidence >= 0.2, 20% relevance threshold)")
                                print(f"   [LLM JUDGE Q4] Result: CORRECT - Relevance (20%) met, no contradictions")
                            else:
                                # Extremely low confidence - mark as wrong
                                is_correct = False
                                method = 'llm_judge_q4_low_confidence'
                                confidence = llm_confidence
                                print(f"   [LLM JUDGE Q4] Very low confidence ({llm_confidence:.3f}), marking as wrong")
                        else:
                            # LLM API error
                            print(f"   [ERROR] Ollama API error: {llm_reasoning}")
                            print(f"   [ERROR] Please check that Ollama is running and the model is available")
                            is_correct = False
                            method = 'llm_api_error'
                            confidence = 0.0
            
            # ============================================================
            # LLM-AS-A-JUDGE: For other long_answer questions (Q3) - Check logical correctness
            # ============================================================
            # Use LLM judge to check logical correctness even for high similarity
            # This catches cases where 95% similarity but one word changes meaning
            elif not logical_opposition and max_semantic_similarity > 0.0:
                # Check with LLM judge for logical correctness (even if already marked correct by similarity)
                # This ensures we catch cases where high similarity but wrong logical meaning
                question_text = question.get('question_text_tamil', '') or question.get('question_text_english', '')
                print(f"   [LLM JUDGE Q{question_id}] Checking logical correctness (similarity: {max_semantic_similarity:.3f}, current: {'CORRECT' if is_correct else 'WRONG'})")
                
                llm_correct, llm_confidence, llm_reasoning = _llm_judge_logical_correctness(
                    user_answer=user_answer,
                    correct_answer=correct_answer,
                    question_text=question_text,
                    key_ideas=key_ideas
                )
                
                if llm_reasoning != "llm_unavailable" and llm_reasoning != "api_error":
                    print(f"   [LLM JUDGE] Result: {'CORRECT' if llm_correct else 'WRONG'} (confidence: {llm_confidence:.3f})")
                    print(f"   [LLM JUDGE] Reasoning: {llm_reasoning[:150]}...")
                    
                    # LLM judge can OVERRIDE semantic similarity results
                    # If LLM says wrong, it's wrong (even if similarity was high)
                    if not llm_correct:
                        is_correct = False
                        method = 'llm_judge_logical_wrong_override'
                        confidence = 1.0 - llm_confidence
                        print(f"   [LLM JUDGE] ⚠️ OVERRIDING - Logical meaning is wrong despite similarity {max_semantic_similarity:.3f}!")
                    # If LLM says correct and confidence is good, accept (or keep if already correct)
                    elif llm_confidence >= 0.6:
                        is_correct = True
                        method = 'llm_judge_logical_correct'
                        confidence = llm_confidence
                        print(f"   [LLM JUDGE] ✓ Logical correctness confirmed")
                    # If LLM confidence is low, keep existing result but lower confidence
                    else:
                        print(f"   [LLM JUDGE] Low confidence ({llm_confidence:.3f}), keeping existing evaluation")
                        # Keep is_correct as is, but method indicates LLM was consulted
                        if is_correct:
                            method = method + '_llm_checked'
                else:
                    print(f"   [LLM JUDGE] Unavailable, using existing evaluation")
            
            # Check alternatives for exact match (only if not logically opposite)
            if not is_correct and not logical_opposition:
                for alt in alternatives:
                    alt_norm = normalize_text(str(alt))
                    if user_norm and alt_norm and user_norm == alt_norm:
                        is_correct = True
                        method = 'exact_match_alternative'
                        confidence = 1.0
                        break
            
            # Fallback exact match with correct answer (only if not logically opposite)
            if not is_correct and not logical_opposition and user_norm and correct_norm and user_norm == correct_norm:
                is_correct = True
                method = 'exact_match'
                confidence = 1.0
            
            # Final safeguard: if logical opposition was detected, ensure it's marked wrong
            # BUT: for Q4 (audio content), we allow opinion/understanding even if sentiment differs,
            # so we DO NOT force it to wrong here.
            if logical_opposition and question_id != '4':
                is_correct = False
                method = 'logical_opposition_final_check'
                confidence = 0.0
            
            # Debug output for long answers
            if question_type == 'long_answer':
                print(f"[Q{question_id}] Final result: {'CORRECT' if is_correct else 'WRONG'} (method: {method}, confidence: {confidence:.3f})")
                if not is_correct:
                    print(f"   Logical opposition: {logical_opposition}")
                    print(f"   Total key idea hits: {total_key_idea_hits}")
                    print(f"   Max semantic similarity: {max_semantic_similarity:.3f}")
        
        # 7. Short answer (general fallback): allow semantic similarity if provided
        elif question_type == 'short_answer':
            user_normalized = normalize_text(user_answer)
            correct_normalized = normalize_text(correct_answer)
            
            # Check for exact match first
            if user_normalized == correct_normalized:
                is_correct = True
                method = 'exact_match'
                confidence = 1.0
            else:
                # Initialize logical opposition flag
                logical_opposition = False
                
                # Check alternatives for exact match
                alternatives = question.get('alternatives', [])
                alt_match = False
                for alt in alternatives:
                    alt_normalized = normalize_text(str(alt))
                    if user_normalized == alt_normalized:
                        is_correct = True
                        method = 'exact_match_alternative'
                        confidence = 1.0
                        alt_match = True
                        break
                
                if not alt_match:
                    # ============================================================
                    # LOGICAL CONTENT CHECKING - Check for semantic opposition
                    # ============================================================
                    
                    print(f"\n[DEBUG Q{question_id}] Evaluating short_answer")
                    print(f"   User answer length: {len(user_answer)} chars")
                    print(f"   Correct answer length: {len(correct_answer)} chars")
                    
                    # 1. Check for negation/opposition in Tamil
                    negation_words = ['மாட்டார்கள்', 'மாட்டார்', 'மாட்டான்', 'மாட்டாள்', 
                                    'இல்லை', 'அல்ல', 'வேண்டாம்', 'செய்யாது', 'செய்யார்',
                                    'செய்யவில்லை', 'செய்யாத', 'இல்லாத', 'வராது', 'வரார்',
                                    'செய்யமாட்டார்கள்', 'செய்யமாட்டார்', 'செய்யமாட்டான்']
                    
                    # Positive action words (should be present in correct answer)
                    positive_action_words = ['செய்வார்', 'செய்வார்கள்', 'செய்வான்', 'செய்வாள்',
                                           'செய்யும்', 'செய்கிறார்கள்', 'செய்கிறார்', 'செய்கிறான்',
                                           'வரும்', 'வருவார்', 'வருவார்கள்', 'வருகிறார்கள்']
                    
                    user_has_negation = any(neg_word in user_answer for neg_word in negation_words)
                    correct_has_negation = any(neg_word in correct_answer for neg_word in negation_words)
                    user_has_positive_action = any(pos_word in user_answer for pos_word in positive_action_words)
                    correct_has_positive_action = any(pos_word in correct_answer for pos_word in positive_action_words)
                    
                    # 2. Check for key concept words that indicate opposite meanings
                    # Hope/Trust vs Doubt/Thought
                    hope_words = ['நம்பிக்கை', 'நம்புகிறார்கள்', 'நம்புவார்கள்', 'நம்புகிறார்']
                    doubt_words = ['நினைத்தார்கள்', 'நினைத்தார்', 'சந்தேகம்', 'ஐயம்', 'எண்ணம்']
                    
                    user_has_hope = any(word in user_answer for word in hope_words)
                    correct_has_hope = any(word in correct_answer for word in hope_words)
                    user_has_doubt = any(word in user_answer for word in doubt_words)
                    correct_has_doubt = any(word in correct_answer for word in doubt_words)
                    
                    # 3. Logical opposition detection
                    # Rule: If user has negation AND correct has positive action, they're opposite
                    # Rule: If user has doubt/thought AND correct has hope/trust, they're opposite
                    logical_opposition = False
                    
                    if user_has_negation and correct_has_positive_action:
                        logical_opposition = True
                    elif user_has_positive_action and correct_has_negation:
                        logical_opposition = True
                    elif user_has_doubt and correct_has_hope:
                        logical_opposition = True
                    elif user_has_hope and correct_has_doubt:
                        logical_opposition = True
                    elif user_has_negation != correct_has_negation:
                        logical_opposition = True
                    
                    # If logically opposite, reject immediately
                    if logical_opposition:
                        print(f"   [OPPOSITION] LOGICAL OPPOSITION DETECTED!")
                        print(f"      User negation: {user_has_negation}, Correct negation: {correct_has_negation}")
                        print(f"      User positive: {user_has_positive_action}, Correct positive: {correct_has_positive_action}")
                        print(f"      User hope: {user_has_hope}, Correct hope: {correct_has_hope}")
                        print(f"      User doubt: {user_has_doubt}, Correct doubt: {correct_has_doubt}")
                        is_correct = False
                        method = 'logical_opposition_detected'
                        confidence = 0.0
                        semantic_similarity = _compute_semantic_similarity(user_answer, correct_answer)
                        semantic_similarities.append(semantic_similarity)
                        print(f"   [RESULT] Marked as WRONG due to logical opposition")
                        # Don't proceed to semantic similarity checks - answer is wrong
                    else:
                        # 4. Check alternatives with semantic similarity (only if not logically opposite)
                        max_alt_similarity = 0.0
                        best_alt_match = None
                        for alt in alternatives:
                            alt_text = str(alt)
                            # Check for logical opposition in alternatives too
                            alt_has_negation = any(neg_word in alt_text for neg_word in negation_words)
                            alt_has_positive = any(pos_word in alt_text for pos_word in positive_action_words)
                            alt_has_hope = any(word in alt_text for word in hope_words)
                            alt_has_doubt = any(word in alt_text for word in doubt_words)
                            
                            # Skip alternatives that are logically opposite
                            alt_opposite = False
                            if user_has_negation and alt_has_positive:
                                alt_opposite = True
                            elif user_has_positive_action and alt_has_negation:
                                alt_opposite = True
                            elif user_has_doubt and alt_has_hope:
                                alt_opposite = True
                            elif user_has_hope and alt_has_doubt:
                                alt_opposite = True
                            
                            if not alt_opposite:
                                alt_sim = _compute_semantic_similarity(user_answer, alt_text)
                                if alt_sim > max_alt_similarity:
                                    max_alt_similarity = alt_sim
                                    best_alt_match = alt_text
                        
                        # Compute semantic similarity with correct answer
                        semantic_similarity = _compute_semantic_similarity(user_answer, correct_answer)
                        semantic_similarities.append(semantic_similarity)
                        
                        # Use the higher of correct answer similarity or best alternative similarity
                        best_similarity = max(semantic_similarity, max_alt_similarity)
                        
                        # 5. Key concept validation for Q1 specifically
                        # Q1 should contain: நம்பிக்கை (hope), ஓட்டு போடுகிறார்கள் (voting), நல்லது செய்வார் (will do good)
                        key_concepts_q1 = ['நம்பிக்கை', 'ஓட்டு', 'போடுகிறார்கள்', 'வாக்களிக்கிறார்கள்', 
                                         'நல்லது', 'செய்வார்', 'செய்வார்கள்', 'முதல்வர்', 'தேர்தல்']
                        user_has_key_concepts = sum(1 for concept in key_concepts_q1 if concept in user_answer)
                        correct_has_key_concepts = sum(1 for concept in key_concepts_q1 if concept in correct_answer)
                        
                        # Require at least 3 key concepts to be present for Q1
                        if question_id == '1' and user_has_key_concepts < 3:
                            is_correct = False
                            method = 'insufficient_key_concepts'
                            confidence = semantic_similarity
                        # Stricter threshold for short answers to avoid false positives
                        # Require higher similarity (0.78 instead of 0.7) AND key concepts
                        elif best_similarity >= 0.78:
                            # Additional validation: check key concepts
                            if question_id == '1':
                                if user_has_key_concepts >= 3 and user_has_hope:
                                    is_correct = True
                                    method = 'ml_semantic_with_concepts'
                                    confidence = best_similarity
                                else:
                                    is_correct = False
                                    method = 'semantic_high_but_missing_concepts'
                                    confidence = best_similarity
                            else:
                                is_correct = True
                                method = 'ml_semantic'
                                confidence = best_similarity
                        elif semantic_similarity >= 0.7:
                            # Also check if key positive words match (to avoid false positives)
                            key_positive_words = ['நம்பிக்கை', 'நல்லது', 'ஓட்டு', 'வாக்களிக்கிறார்கள்', 
                                                'போடுகிறார்கள்', 'போடுவார்கள்', 'செய்வார்', 'செய்வார்கள்']
                            user_has_key_words = any(word in user_answer for word in key_positive_words)
                            
                            if user_has_key_words and (question_id != '1' or user_has_hope):
                                is_correct = True
                                method = 'ml_semantic_with_keywords'
                                confidence = semantic_similarity
                            else:
                                is_correct = False
                                method = 'semantic_low_keywords'
                                confidence = semantic_similarity
                        else:
                            is_correct = False
                            method = 'rule_based'
                            confidence = semantic_similarity
                            
                            # Final fallback: try ML classifier (but only if no logical opposition)
                            # CRITICAL: Never override logical opposition detection
                            if not logical_opposition and semantic_similarity > 0.5:
                                is_correct_check, confidence_check = _ml_answer_correctness_classifier(
                                    user_answer, correct_answer, semantic_similarity, question_type
                                )
                                # Only accept if classifier is confident AND no logical opposition AND has key concepts
                                if (is_correct_check and confidence_check >= 0.75 and 
                                    (question_id != '1' or (user_has_key_concepts >= 2 and user_has_hope))):
                                    is_correct = True
                                    method = 'ml_classifier'
                                    confidence = confidence_check
                            elif logical_opposition and question_id != '4':
                                # Double-check: if logical opposition was detected, ensure it's marked wrong
                                # (Skip this for Q4, where we only care about relevance to audio.)
                                is_correct = False
                                method = 'logical_opposition_final_check'
                                confidence = 0.0
        
        # Default: fallback to rule-based
        else:
            user_normalized = normalize_text(user_answer)
            correct_normalized = normalize_text(correct_answer)
            
            if user_normalized == correct_normalized:
                is_correct = True
                method = 'exact_match'
                confidence = 1.0
        
        # Store detailed information
        details[question_id] = {
            'correct': is_correct,
            'user_answer': user_answer,
            'correct_answer': correct_answer,
            'semantic_similarity': round(semantic_similarity, 3),
            'method': method,
            'confidence': round(confidence, 3)
        }
        
        print(f"[Q{question_id}] Final result: {'CORRECT' if is_correct else 'WRONG'} (method: {method}, confidence: {confidence:.3f})")
        
        if is_correct:
            score += 1
    
    # Calculate accuracy
    accuracy = (score / total * 100) if total > 0 else 0.0
    
    # Calculate average semantic similarity
    avg_semantic_similarity = sum(semantic_similarities) / len(semantic_similarities) if semantic_similarities else 0.0
    
    # ML Proficiency Classifier (Level 3 ONLY)
    proficiency_result = _ml_proficiency_classifier(
        accuracy=accuracy,
        avg_semantic_similarity=avg_semantic_similarity,
        time_taken=time_taken
    )
    
    return {
        'score': score,
        'total': total,
        'accuracy': round(accuracy, 2),
        'details': details,
        'proficiency': proficiency_result,
        'avg_semantic_similarity': round(avg_semantic_similarity, 3)
    }

