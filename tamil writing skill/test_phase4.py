#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test Phase 4 error payload structure"""

import sys
sys.path.insert(0, '.')

from tamil_grammar_rules import check_post_verb_word_order

# Test error payload structure
tokens = ['நான்', 'படிக்கிறேன்', 'புத்தகம்']
result = check_post_verb_word_order(tokens, 1, 'நான் படிக்கிறேன் புத்தகம்')

if result:
    error = result[0]
    print("Phase 4 Error Payload Structure:")
    print("=" * 50)
    print(f"rule: {error.get('rule')}")
    print(f"offending_noun: {error.get('offending_noun')}")
    print(f"finite_verb: {error.get('finite_verb')}")
    print(f"message: {error.get('message')}")
    print(f"primary_highlight: {error.get('primary_highlight')}")
    print(f"secondary_highlight: {error.get('secondary_highlight')}")
    print("=" * 50)
    print("\nVerification:")
    print(f"✓ Has 'offending_noun': {error.get('offending_noun') == 'புத்தகம்'}")
    print(f"✓ Has 'finite_verb': {error.get('finite_verb') == 'படிக்கிறேன்'}")
    print(f"✓ Has 'message': {error.get('message') is not None}")
    print(f"✓ Primary highlight is noun: {error.get('primary_highlight') == 'புத்தகம்'}")
    print(f"✓ Secondary highlight is verb: {error.get('secondary_highlight') == 'படிக்கிறேன்'}")
else:
    print("ERROR: No violation detected!")
