"""
Test script for Level 2 Question 5 (L2_Q5) long answer evaluation.
Tests three scenarios:
1. Correct answer (pipe leakage + kitchen flooding) - Expected: Relevance >= 70%, Correct
2. Partially correct answer (only leakage) - Expected: Relevance ~50%, Correct  
3. Nonsense input - Expected: Relevance 0%, Wrong
"""

import requests
import json
import sys
import io

# Set UTF-8 encoding for stdout to handle Tamil text
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Backend endpoint
BACKEND_URL = "http://127.0.0.1:5001/evaluate"

# Test Case 1: Correct Tamil answer describing pipe leakage and kitchen flooding
test_case_1 = {
    "level": 2,
    "audio_id": "level2_dialogue_tamil",
    "responses": {
        "level2Answers": {
            "identify_speaker": "A. டெனன்",
            "dialogue_ordering": "ருவிகா, தண்ணீர் இல்லாமல் இன்று முழுக்க எப்படி மேனேஜ் செய்வீர்கள் என்று கேட்கிறார்., சேவாங், சமையலறையில் தண்ணீர் குழாய் லீக் ஆனதை விளக்குகிறார்., டெனன், சேவாங் கவலையாக இருப்பதை கவனித்து கேட்கிறார்., சேவாங், வீட்டின் உரிமையாளர் நாளைக்கு பிளம்பர் அனுப்புவதாக சொன்னார் என்று கூறுகிறார்., டெனன், ஆபிஸ் முடிந்த பிறகு உதவி செய்யலாம் என்று சொல்கிறார்., ருவிகா, மீட்டிங்குக்கு தாமதமாகிவிட்டதாக கூறி கிளம்பச் சொல்கிறார்.",
            "main_problem_discussed": "செல்வம்",
            "match_speaker_role": {
                "டெனன்": "உதவி செய்வதாகவும் நம்பிக்கை அளிப்பதாகவும் கூறுகிறார்",
                "ருவிகா": "பிரச்சனை குறித்து கேள்விகள் கேட்டு பேசுகிறார்",
                "சேவாங்": "வீட்டில் ஏற்பட்ட பிரச்சனையை விளக்குகிறார்"
            },
            "long_answers": {
                "L2_Q5": "சேவாங்கின் வீட்டில் தண்ணீர் குழாய் கசிவு ஏற்பட்டது. இதனால் சமையலறை முழுவதும் தண்ணீரால் நிரம்பியது. இந்த பிரச்சனை காரணமாக வீட்டில் பல சிரமங்கள் ஏற்பட்டன மற்றும் அன்றாட வேலைகள் பாதிக்கப்பட்டன."
            }
        }
    }
}

# Test Case 2: Partially correct answer mentioning only leakage
test_case_2 = {
    "level": 2,
    "audio_id": "level2_dialogue_tamil",
    "responses": {
        "level2Answers": {
            "identify_speaker": "A. டெனன்",
            "dialogue_ordering": "ருவிகா, தண்ணீர் இல்லாமல் இன்று முழுக்க எப்படி மேனேஜ் செய்வீர்கள் என்று கேட்கிறார்., சேவாங், சமையலறையில் தண்ணீர் குழாய் லீக் ஆனதை விளக்குகிறார்., டெனன், சேவாங் கவலையாக இருப்பதை கவனித்து கேட்கிறார்., சேவாங், வீட்டின் உரிமையாளர் நாளைக்கு பிளம்பர் அனுப்புவதாக சொன்னார் என்று கூறுகிறார்., டெனன், ஆபிஸ் முடிந்த பிறகு உதவி செய்யலாம் என்று சொல்கிறார்., ருவிகா, மீட்டிங்குக்கு தாமதமாகிவிட்டதாக கூறி கிளம்பச் சொல்கிறார்.",
            "main_problem_discussed": "செல்வம்",
            "match_speaker_role": {
                "டெனன்": "உதவி செய்வதாகவும் நம்பிக்கை அளிப்பதாகவும் கூறுகிறார்",
                "ருவிகா": "பிரச்சனை குறித்து கேள்விகள் கேட்டு பேசுகிறார்",
                "சேவாங்": "வீட்டில் ஏற்பட்ட பிரச்சனையை விளக்குகிறார்"
            },
            "long_answers": {
                "L2_Q5": "சேவாங்கின் வீட்டில் தண்ணீர் குழாய் கசிவு ஏற்பட்டது."
            }
        }
    }
}

# Test Case 3: Nonsense input
test_case_3 = {
    "level": 2,
    "audio_id": "level2_dialogue_tamil",
    "responses": {
        "level2Answers": {
            "identify_speaker": "A. டெனன்",
            "dialogue_ordering": "ருவிகா, தண்ணீர் இல்லாமல் இன்று முழுக்க எப்படி மேனேஜ் செய்வீர்கள் என்று கேட்கிறார்., சேவாங், சமையலறையில் தண்ணீர் குழாய் லீக் ஆனதை விளக்குகிறார்., டெனன், சேவாங் கவலையாக இருப்பதை கவனித்து கேட்கிறார்., சேவாங், வீட்டின் உரிமையாளர் நாளைக்கு பிளம்பர் அனுப்புவதாக சொன்னார் என்று கூறுகிறார்., டெனன், ஆபிஸ் முடிந்த பிறகு உதவி செய்யலாம் என்று சொல்கிறார்., ருவிகா, மீட்டிங்குக்கு தாமதமாகிவிட்டதாக கூறி கிளம்பச் சொல்கிறார்.",
            "main_problem_discussed": "செல்வம்",
            "match_speaker_role": {
                "டெனன்": "உதவி செய்வதாகவும் நம்பிக்கை அளிப்பதாகவும் கூறுகிறார்",
                "ருவிகா": "பிரச்சனை குறித்து கேள்விகள் கேட்டு பேசுகிறார்",
                "சேவாங்": "வீட்டில் ஏற்பட்ட பிரச்சனையை விளக்குகிறார்"
            },
            "long_answers": {
                "L2_Q5": "இஇஊஊ"
            }
        }
    }
}


def test_level2_q5(test_case, case_number, expected_relevance_min=None, expected_relevance_max=None, expected_correct=None):
    """Test Level 2 Question 5 evaluation with a given test case."""
    print(f"\n{'='*80}")
    print(f"TEST CASE {case_number}")
    print(f"{'='*80}")
    
    # Print test input
    print(f"\nTest Input:")
    long_answer = test_case["responses"]["level2Answers"]["long_answers"]["L2_Q5"]
    print(f"   Answer: {long_answer}")
    print(f"   Length: {len(long_answer)} characters")
    
    try:
        # Send POST request
        response = requests.post(BACKEND_URL, json=test_case, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        # Extract L2_Q5 evaluation results
        long_answers = result.get("details", {}).get("long_answers", {})
        q5_key = "long_answer_L2_Q5"
        if q5_key not in long_answers:
            q5_key = "long_answer_5"
        
        q5_result = long_answers.get(q5_key, {})
        
        # Extract metrics
        relevance = q5_result.get("answer_relevance")
        covered_count = q5_result.get("covered_count", 0)
        total_key_ideas = q5_result.get("total_key_ideas", 0)
        is_correct = q5_result.get("correct", False)
        is_evaluated = q5_result.get("evaluated", False)
        
        print(f"\nResults:")
        print(f"   Evaluated: {is_evaluated}")
        print(f"   Correct: {is_correct}")
        print(f"   Answer Relevance: {relevance}%" if relevance is not None else "   Answer Relevance: N/A")
        print(f"   Key Ideas Covered: {covered_count}/{total_key_ideas}")
        
        # Check expectations
        print(f"\nValidation:")
        all_passed = True
        
        if expected_relevance_min is not None and relevance is not None:
            passed = relevance >= expected_relevance_min
            status = "[PASS]" if passed else "[FAIL]"
            print(f"   {status} Relevance >= {expected_relevance_min}%: {relevance}%")
            if not passed:
                all_passed = False
        
        if expected_relevance_max is not None and relevance is not None:
            passed = relevance <= expected_relevance_max
            status = "[PASS]" if passed else "[FAIL]"
            print(f"   {status} Relevance <= {expected_relevance_max}%: {relevance}%")
            if not passed:
                all_passed = False
        
        if expected_correct is not None:
            passed = is_correct == expected_correct
            status = "[PASS]" if passed else "[FAIL]"
            print(f"   {status} Correct == {expected_correct}: {is_correct}")
            if not passed:
                all_passed = False
        
        if all_passed:
            print(f"\n[PASS] TEST CASE {case_number} PASSED")
        else:
            print(f"\n[FAIL] TEST CASE {case_number} FAILED")
        
        return all_passed
        
    except requests.exceptions.RequestException as e:
        print(f"\n[ERROR] Error making request: {e}")
        return False
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Testing Level 2 Question 5 (L2_Q5) Evaluation")
    print("=" * 80)
    
    # Check if backend is running
    try:
        response = requests.get("http://127.0.0.1:5001/", timeout=5)
        print("[OK] Backend is running")
    except:
        print("[ERROR] Backend is not running. Please start it first:")
        print("   cd Backend && python app.py")
        print("   OR")
        print("   Double-click START_BACKEND.bat")
        exit(1)
    
    # Run test cases
    results = []
    
    # Test Case 1: Correct answer - Expected: Relevance ≥ 70%, Correct
    results.append(test_level2_q5(
        test_case_1, 
        case_number=1,
        expected_relevance_min=70,
        expected_correct=True
    ))
    
    # Test Case 2: Partially correct - Expected: Relevance ~50%, Correct (matched_key_ideas >= 2)
    results.append(test_level2_q5(
        test_case_2,
        case_number=2,
        expected_relevance_min=40,
        expected_relevance_max=60,
        expected_correct=True  # Should be correct if matched_key_ideas >= 2
    ))
    
    # Test Case 3: Nonsense input - Expected: Relevance 0%, Wrong
    results.append(test_level2_q5(
        test_case_3,
        case_number=3,
        expected_relevance_min=0,
        expected_relevance_max=0,
        expected_correct=False
    ))
    
    # Summary
    print(f"\n{'='*80}")
    print(f"TEST SUMMARY")
    print(f"{'='*80}")
    passed_count = sum(results)
    total_count = len(results)
    print(f"Passed: {passed_count}/{total_count}")
    
    if all(results):
        print("[SUCCESS] ALL TESTS PASSED")
        exit(0)
    else:
        print("[FAILURE] SOME TESTS FAILED")
        exit(1)

