#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test script for Step 3.4: Core violation check"""

import sys
sys.path.insert(0, '.')

from tamil_grammar_rules import check_post_verb_word_order

print("=" * 80)
print("Testing Step 3.4: Core Violation Check")
print("=" * 80)

# Test 1: Unmarked noun after verb (SHOULD flag error and STOP)
print("\n[Test 1] Unmarked noun after verb")
print("Sentence: நான் படிக்கிறேன் புத்தகம்")
tokens1 = ['நான்', 'படிக்கிறேன்', 'புத்தகம்']
result1 = check_post_verb_word_order(tokens1, 1, 'நான் படிக்கிறேன் புத்தகம்')
print(f"Expected: 1 error (unmarked noun 'புத்தகம்')")
print(f"Actual: {len(result1)} error(s)")
if result1:
    print(f"Error word: {result1[0]['word']}")
    print(f"Reason: {result1[0]['reason']}")
print(f"✓ PASS" if len(result1) == 1 else "✗ FAIL")

# Test 2: Marked noun after verb (should NOT flag error)
print("\n[Test 2] Marked noun after verb")
print("Sentence: நான் படிக்கிறேன் புத்தகத்தை")
tokens2 = ['நான்', 'படிக்கிறேன்', 'புத்தகத்தை']
result2 = check_post_verb_word_order(tokens2, 1, 'நான் படிக்கிறேன் புத்தகத்தை')
print(f"Expected: 0 errors (noun has case marker -ஐ)")
print(f"Actual: {len(result2)} error(s)")
print(f"✓ PASS" if len(result2) == 0 else "✗ FAIL")

# Test 3: Adverb after verb (should NOT flag error - Step 3.3 filters it)
print("\n[Test 3] Adverb after verb")
print("Sentence: நான் படிக்கிறேன் இன்று")
tokens3 = ['நான்', 'படிக்கிறேன்', 'இன்று']
result3 = check_post_verb_word_order(tokens3, 1, 'நான் படிக்கிறேன் இன்று')
print(f"Expected: 0 errors (adverb filtered by Step 3.3)")
print(f"Actual: {len(result3)} error(s)")
print(f"✓ PASS" if len(result3) == 0 else "✗ FAIL")

# Test 4: Multiple unmarked nouns (should STOP at first one - Step 3.4)
print("\n[Test 4] Multiple unmarked nouns after verb")
print("Sentence: நான் படிக்கிறேன் புத்தகம் பேனா")
tokens4 = ['நான்', 'படிக்கிறேன்', 'புத்தகம்', 'பேனா']
result4 = check_post_verb_word_order(tokens4, 1, 'நான் படிக்கிறேன் புத்தகம் பேனா')
print(f"Expected: 1 error (STOP at first unmarked noun 'புத்தகம்')")
print(f"Actual: {len(result4)} error(s)")
if result4:
    print(f"Error word: {result4[0]['word']}")
print(f"✓ PASS" if len(result4) == 1 and result4[0]['word'] == 'புத்தகம்' else "✗ FAIL")

# Test 5: Conjunction after verb (should NOT flag error)
print("\n[Test 5] Conjunction after verb")
print("Sentence: நான் படிக்கிறேன் மற்றும் எழுதுகிறேன்")
tokens5 = ['நான்', 'படிக்கிறேன்', 'மற்றும்', 'எழுதுகிறேன்']
result5 = check_post_verb_word_order(tokens5, 1, 'நான் படிக்கிறேன் மற்றும் எழுதுகிறேன்')
print(f"Expected: 0 errors (conjunction filtered by Step 3.3)")
print(f"Actual: {len(result5)} error(s)")
print(f"✓ PASS" if len(result5) == 0 else "✗ FAIL")

# Test 6: Mixed - adverb then unmarked noun (should flag only the noun)
print("\n[Test 6] Adverb then unmarked noun after verb")
print("Sentence: நான் படிக்கிறேன் இன்று புத்தகம்")
tokens6 = ['நான்', 'படிக்கிறேன்', 'இன்று', 'புத்தகம்']
result6 = check_post_verb_word_order(tokens6, 1, 'நான் படிக்கிறேன் இன்று புத்தகம்')
print(f"Expected: 1 error (skip adverb, flag unmarked noun 'புத்தகம்')")
print(f"Actual: {len(result6)} error(s)")
if result6:
    print(f"Error word: {result6[0]['word']}")
print(f"✓ PASS" if len(result6) == 1 and result6[0]['word'] == 'புத்தகம்' else "✗ FAIL")

print("\n" + "=" * 80)
print("Test Summary")
print("=" * 80)
print("All tests validate Step 3.4: Core violation check")
print("- Stops processing after first unmarked noun violation")
print("- Correctly filters non-nouns (Step 3.3)")
print("- Allows marked nouns to pass")
