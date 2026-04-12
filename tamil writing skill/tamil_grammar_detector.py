#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tamil Grammar Detector — Level 1
Uses tamil_grammar_rules (agreement features & verb suffix mapping) for all grammar checks.
"""

import re
import logging
from typing import List, Dict, Optional

from tamil_grammar_rules import (
    VERB_SUFFIX_FEATURE_MAP,
    get_verb_features_from_suffix,
    extract_verb_features,
    VERB_ERROR_INCOMPLETE,
    get_subject_features_from_pronoun,
    word_ends_with_not_subject_marker,
    word_can_be_subject,
    is_subject_pronoun,
    agreement_check,
    AGREEMENT_ERROR_RULE,
    implicit_subject_allowed,
    get_subject_features_for_irrational_noun,
    is_irrational_collective_noun,
    detect_sentence_type,
    should_skip_agreement_check,
    SENTENCE_TYPE_FINITE_VERB,
    SENTENCE_TYPE_NOMINAL,
    SENTENCE_TYPE_EXISTENTIAL,
    SENTENCE_TYPE_MODAL,
    SENTENCE_TYPE_INVALID,
    # Tense consistency (Grammar Rule 2)
    split_into_clauses,
    detect_explicit_time_marker,
    detect_verb_tense_from_suffix,
    should_check_tense_consistency,
    is_finite_verb_for_tense,
    TENSE_PAST,
    TENSE_PRESENT,
    TENSE_FUTURE,
    TENSE_UNKNOWN,
    AGREEMENT_FEATURES,
    PERSON_VALUES,
    NUMBER_SINGULAR,
    NUMBER_PLURAL,
    CLASS_MALE,
    CLASS_FEMALE,
    CLASS_RATIONAL,
    CLASS_IRRATIONAL,
    TIME_MARKERS,
    MODAL_MARKERS,
    EXISTENTIAL_MARKERS,
    # Word order checking (Grammar Rule 3)
    check_post_verb_word_order,
    is_allowed_nominal_sentence,
    # Copular predicates (ஆகும் / ஆனது etc.)
    is_copular_predicate,
)

logger = logging.getLogger(__name__)


class TamilGrammarDetector:
    """
    Grammar detector using the rule backbone from tamil_grammar_rules.
    All grammar rule checking uses the agreement features and verb suffix mapping.
    """

    def __init__(self, use_ollama: bool = False):
        self.use_ollama = use_ollama
        self.available = True  # Rules always available

    def detect_grammar_errors(self, text: str) -> Dict:
        """
        Detect grammar errors using tamil_grammar_rules.
        Checks:
          - Grammar Rule 1: Subject-verb agreement (Steps 0-6)
          - Grammar Rule 2: Tense consistency (per clause)
        Returns dict with grammar_errors, error_count, rule_based_errors, etc.
        """
        if not text or len(text.strip()) < 2:
            return {
                "grammar_errors": [],
                "error_count": 0,
                "rule_based_errors": [],
                "formatted_errors": [],
            }

        sentences = re.split(r"[.!?।]+", text)
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) >= 2]

        all_errors: List[Dict] = []

        # Grammar Rule 1: Subject-verb agreement (per sentence)
        for sentence in sentences:
            errors = self._check_sentence(sentence)
            for err in errors:
                err["sentence"] = sentence
                all_errors.append(err)

        # Grammar Rule 2: Tense consistency (per clause, across text)
        tense_errors = self._check_tense_consistency(text, sentences)
        all_errors.extend(tense_errors)

        # De-duplicate errors: same rule + location/word + description/reason + sentence
        seen = set()
        unique_errors: List[Dict] = []
        for err in all_errors:
            key = (
                err.get("rule"),
                err.get("location") or err.get("word"),
                err.get("description") or err.get("reason"),
                err.get("sentence", ""),
            )
            if key in seen:
                continue
            seen.add(key)
            unique_errors.append(err)

        return {
            "grammar_errors": unique_errors,
            "error_count": len(unique_errors),
            "rule_based_errors": unique_errors,
            "formatted_errors": unique_errors,
        }

    def _check_sentence(self, sentence: str) -> List[Dict]:
        """
        STEP 0 + STEP 6: Sentence Type Detection (prevent false positives) + Rule Priority (speed).
        
        Step 0 (MANDATORY): Detect sentence type BEFORE agreement:
          - FINITE_VERB: normal verb (apply agreement)
          - NOMINAL: noun-ending (skip agreement)
          - EXISTENTIAL: உள்ளது/இல்லை type (skip agreement)
          - MODAL: infinitive + வேண்டும் (skip agreement)
          - INVALID: unknown (may flag error)
        
        Step 6 workflow (when sentence type allows):
          1. Identify verb
          2. Decode verb agreement features
          3. Identify explicit subject (if exists)
          4. If no subject → allow implicit rule (1st/2nd person)
          5. Compare features
          6. Flag error
        """
        errors: List[Dict] = []
        words = sentence.split()
        if not words:
            return errors

        # Clean tokens (strip punctuation)
        tokens = [w.strip(".,!?।:;") for w in words if w.strip(".,!?।:;")]
        if not tokens:
            return errors

        # ===== STEP 0: Sentence Type Detection (MANDATORY — prevents false positives) =====
        sentence_type = detect_sentence_type(sentence, tokens)
        logger.debug(f"Sentence type: {sentence_type} — '{sentence[:50]}...'")
        
        # NOTE: We do NOT return early here anymore, because we still want to check
        # other rules (like Word Order Step 3.4) even for MODAL/EXISTENTIAL sentences.
        # We will skip only the AGREEMENT check step later.

        # ===== STEP 6.1: Identify finite verb and predicates (UNIFIED COMPLETENESS CHECK) =====
        # We no longer require "last word must be finite verb".
        # A sentence is considered COMPLETE if it has ANY of:
        #   - a finite action verb
        #   - a copular predicate (e.g. ஆகும், அவசியமானதாகும்)
        #   - an existential predicate (உள்ளது, உள்ளன, இல்லை, இருந்தது, இருக்கும், ...)
        #   - a nominal predicate (ends with allowed nominal predicate or last word is noun)

        verb_word = None
        verb_features = None
        verb_index = -1

        # 6.1.A: Standard Finite Verb Check (Suffix-based) — has_finite_action_verb
        for i in range(len(tokens) - 1, -1, -1):
            clean = tokens[i]
            if not clean:
                continue
            features, error_code = extract_verb_features(clean)
            if error_code == VERB_ERROR_INCOMPLETE:
                continue
            if features is not None:
                verb_word = clean
                verb_features = features
                verb_index = i
                break

        has_finite_action_verb = verb_word is not None and verb_features is not None

        # 6.1.B: Predicate detectors (copular + existential + nominal)
        # Copular: any token that is (or ends with) ஆகும் / ஆனது / ஆகின்றது / etc.
        has_copular_predicate = any(is_copular_predicate(tok) for tok in tokens)

        # Existential: any token exactly in EXISTENTIAL_MARKERS (includes உள்ளன now)
        has_existential_predicate = any(tok.strip() in EXISTENTIAL_MARKERS for tok in tokens if tok)

        # Nominal predicate: allowed nominal sentence (என் பெயர் தினேஷ்) OR last token looks like a noun
        last_word = tokens[-1] if tokens else ""
        from tamil_grammar_rules import is_noun_candidate  # local import to avoid circular issues
        has_nominal_predicate = False
        if sentence_type == SENTENCE_TYPE_NOMINAL and is_allowed_nominal_sentence(sentence):
            has_nominal_predicate = True
        elif last_word and is_noun_candidate(last_word):
            has_nominal_predicate = True

        # Unified completeness rule:
        # IF no finite verb AND no copular predicate AND no existential predicate AND no nominal predicate
        # THEN and ONLY THEN raise VERB_FORM_MISSING.
        if not (has_finite_action_verb or has_copular_predicate or has_existential_predicate or has_nominal_predicate):
            if last_word:
                errors.append({
                    "rule": "VERB_FORM_MISSING",
                    "error_type": "GRAMMAR",
                    "description": "Verb form or predicate missing. Sentence should have a finite verb, copular predicate, existential predicate, or nominal predicate.",
                    "location": last_word,
                    "word": last_word,
                    "reason": "No valid predicate found in sentence",
                    "severity": "HIGH",
                })
            return errors

        # ===== STEP 6.2: Decode verb agreement features (already done in 6.1) =====
        # verb_features now has: person, number, class

        # ===== STEP 6.3: Identify explicit subject (Step 2 — subject detection) =====
        # Prefer pronoun, else nominative noun (no -ஐ, -க்கு, -உடன், -ஆல்)
        subject_word = None
        subject_features = None
        # First pass: find pronoun before verb (prefer pronouns)
        for i in range(verb_index - 1, -1, -1):
            w = tokens[i]
            if not w or word_ends_with_not_subject_marker(w):
                continue
            if is_subject_pronoun(w):
                subject_word = w
                subject_features = get_subject_features_from_pronoun(w)
                break
        # Second pass: if no pronoun, take first word that can be subject (nominative noun)
        if subject_word is None:
            for i in range(verb_index - 1, -1, -1):
                w = tokens[i]
                if not w or word_ends_with_not_subject_marker(w):
                    continue
                if word_can_be_subject(w):
                    subject_word = w
                    break

        # ===== STEP 6.4: If no subject → allow implicit rule (Step 5 edge case 1) =====
        # If verb is 1st/2nd person → implicit subject allowed. Do NOT flag error.
        if subject_word is None and implicit_subject_allowed(verb_features):
            # Only return IF agreement check is required. If skipping agreement, continue to other checks.
            if not should_skip_agreement_check(sentence_type):
                return errors

        # Step 5 edge case 3: If subject is irrational collective noun → assign features (verb must be irrational).
        if subject_word is not None and subject_features is None and is_irrational_collective_noun(subject_word):
            subject_features = get_subject_features_for_irrational_noun(subject_word)

        # ===== STEP 6.5: Compare features (Step 4 — agreement check) =====
        # ONLY run this if explicit agreement checks are required for this sentence type.
        if not should_skip_agreement_check(sentence_type):
            # IF subject.person != verb.person OR subject.number != verb.number OR subject.class != verb.class
            # → SUBJECT_VERB_AGREEMENT_ERROR
            # Step 5 edge case 2: நீங்கள் → allow plural verb only (already enforced by number in pronoun table).
            if subject_features is not None and verb_features is not None:
                agrees, error_rule = agreement_check(subject_features, verb_features)
                
                # ===== STEP 6.6: Flag error =====
                if not agrees and error_rule == AGREEMENT_ERROR_RULE:
                    sub_p = subject_features.get("person")
                    sub_n = subject_features.get("number")
                    sub_c = subject_features.get("class")
                    verb_p = verb_features.get("person")
                    verb_n = verb_features.get("number")
                    verb_c = verb_features.get("class")
                    mismatches = []
                    if sub_p != verb_p:
                        mismatches.append("person")
                    if sub_n != verb_n:
                        mismatches.append("number")
                    if sub_c is not None and verb_c is not None and sub_c != verb_c:
                        mismatches.append("class")
                    errors.append({
                        "rule": AGREEMENT_ERROR_RULE,
                        "error_type": "GRAMMAR",
                        "description": (
                            f"Subject-verb agreement error: subject '{subject_word}' "
                            f"(person={sub_p}, number={sub_n}, class={sub_c}) does not match verb '{verb_word}' "
                            f"(person={verb_p}, number={verb_n}, class={verb_c}). Mismatch: {', '.join(mismatches)}."
                        ),
                        "location": verb_word,
                        "word": verb_word,
                        "reason": "Subject and verb do not agree in person, number, or class",
                        "severity": "HIGH",
                        "subject_word": subject_word,
                        "verb_word": verb_word,
                    })

        # ===== GRAMMAR RULE 3: Word Order Checking (Steps 3.3, 3.4, Phase 4) =====
        # Check for unmarked nouns after the finite verb
        # This must be done AFTER we've identified the verb (verb_index is available)
        if verb_word is not None and verb_index >= 0:
            word_order_errors = check_post_verb_word_order(tokens, verb_index, sentence)
            errors.extend(word_order_errors)

        return errors

    def _check_tense_consistency(self, text: str, sentences: List[str]) -> List[Dict]:
        """
        Grammar Rule 2: Tense Consistency Check (Step 6).
        FOR each clause:
          IF time_marker exists:
            EXPECTED_TENSE = marker_tense
            FOR each finite verb in clause:
              IF verb.tense != EXPECTED_TENSE:
                FLAG TENSE_INCONSISTENCY
        """
        errors: List[Dict] = []
        
        for sentence in sentences:
            # Split sentence into clauses (scope control — tense checked per clause)
            clauses = split_into_clauses(sentence)
            
            for clause_idx, clause in enumerate(clauses):
                if not clause or len(clause.strip()) < 2:
                    continue
                
                # Rule: IF no time marker in clause → DO NOT run tense consistency
                if not should_check_tense_consistency(clause):
                    continue
                
                # Get expected tense from time marker
                expected_tense = detect_explicit_time_marker(clause)
                if not expected_tense:
                    continue

                # Identify the concrete time marker word inside this clause (for UI highlighting)
                time_marker_word: Optional[str] = None
                for marker in TIME_MARKERS:
                    if marker in clause:
                        time_marker_word = marker
                        break
                
                # Find all finite verbs in clause
                tokens = clause.split()
                for tok in tokens:
                    clean = tok.strip(".,!?।:;")
                    if not clean:
                        continue
                    
                    # Check if this is a finite verb (ignore modals, infinitives, etc.)
                    if not is_finite_verb_for_tense(clean, clause):
                        continue
                    
                    # Get verb tense from suffix
                    verb_tense = detect_verb_tense_from_suffix(clean)
                    if not verb_tense:
                        continue
                    
                    # Compare: IF verb.tense != EXPECTED_TENSE → FLAG
                    if verb_tense != expected_tense:
                        # Primary error word: time marker; secondary: verb
                        primary_location = time_marker_word or clean
                        errors.append({
                            "rule": "TENSE_INCONSISTENCY",
                            "error_type": "GRAMMAR",
                            "description": (
                                f"Time marker '{time_marker_word}' indicates {expected_tense} tense, "
                                f"but verb '{clean}' is in {verb_tense} tense."
                            ),
                            "location": primary_location,
                            "word": clean,
                            "time_marker": time_marker_word,
                            "verb_word": clean,
                            "reason": (
                                f"Verb tense ({verb_tense}) conflicts with time marker "
                                f"'{time_marker_word}' ({expected_tense})."
                            ),
                            "severity": "MEDIUM",
                            "sentence": sentence,
                            "clause": clause,
                            "expected_tense": expected_tense,
                            "actual_tense": verb_tense,
                        })
        
        return errors


def detect_grammar_errors(text: str) -> Dict:
    """Convenience function using default detector."""
    detector = TamilGrammarDetector(use_ollama=False)
    return detector.detect_grammar_errors(text)
