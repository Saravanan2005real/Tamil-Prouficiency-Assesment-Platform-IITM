#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test integrated grammar detection"""

from tamil_grammar_detector import detect_grammar_errors

# Test 1: Unmarked noun after verb
print("Test 1: நான் படிக்கிறேன் புத்தகம்")
result1 = detect_grammar_errors('நான் படிக்கிறேன் புத்தகம்')
print(f"Errors: {result1['error_count']}")
for err in result1['grammar_errors']:
    print(f"  - {err['rule']}: {err.get('offending_noun', err.get('word'))}")
print()

# Test 2: Marked noun after verb (should be OK)
print("Test 2: நான் படிக்கிறேன் புத்தகத்தை")
result2 = detect_grammar_errors('நான் படிக்கிறேன் புத்தகத்தை')
print(f"Errors: {result2['error_count']}")
print()

# Test 3: Adverb after verb (should be OK)
print("Test 3: நான் படிக்கிறேன் இன்று")
result3 = detect_grammar_errors('நான் படிக்கிறேன் இன்று')
print(f"Errors: {result3['error_count']}")
print()

print("=" * 50)
print("Summary:")
print(f"Test 1 (unmarked noun): {result1['error_count']} error(s) - {'✓ PASS' if result1['error_count'] > 0 else '✗ FAIL'}")
print(f"Test 2 (marked noun): {result2['error_count']} error(s) - {'✓ PASS' if result2['error_count'] == 0 else '✗ FAIL'}")
print(f"Test 3 (adverb): {result3['error_count']} error(s) - {'✓ PASS' if result3['error_count'] == 0 else '✗ FAIL'}")
