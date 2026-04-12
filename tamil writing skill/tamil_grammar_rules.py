#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tamil Grammar Rules — Step 0: Sentence Type Detection (prevents false positives)
                         Step 1: Agreement Features & Verb Suffix Mapping
                         Step 2: Subject Detection (Rule-Based)
                         Step 3: Verb Feature Extraction
                         Step 4: Agreement Check Logic
                         Step 5: Tamil-Specific Edge Cases
                         Step 6: Rule Priority (workflow optimization)
Level 1 Grammar backbone. All grammar rule checking uses these definitions.
"""

from typing import List, Dict, Any, Optional, Tuple

# =============================================================================
# STEP 0: SENTENCE TYPE DETECTION (prevents false positives)
# Detect sentence type BEFORE applying subject-verb agreement rules.
# =============================================================================

# Sentence type constants
SENTENCE_TYPE_FINITE_VERB: str = "FINITE_VERB"        # Normal verb sentence (apply agreement)
SENTENCE_TYPE_NOMINAL: str = "NOMINAL"                # Noun-ending sentence (skip agreement)
SENTENCE_TYPE_EXISTENTIAL: str = "EXISTENTIAL"        # உள்ளது/இல்லை type (skip agreement)
SENTENCE_TYPE_MODAL: str = "MODAL"                    # infinitive + வேண்டும் (skip agreement)
SENTENCE_TYPE_INVALID: str = "INVALID"                # Unknown/invalid (may flag error)

# Existential verb markers (these sentences don't follow normal subject-verb agreement)
EXISTENTIAL_MARKERS: Tuple[str, ...] = ("உள்ளது", "உள்ளன", "இல்லை", "இருந்தது", "இருக்கும்", "உண்டு", "இல்லாது")

# Modal verb markers (infinitive + modal)
MODAL_MARKERS: Tuple[str, ...] = ("வேண்டும்", "கூடாது", "லாம்", "மாட்டேன்", "மாட்டான்", "மாட்டாள்")

# Infinitive suffixes (used with modal வேண்டும்)
INFINITIVE_SUFFIXES: Tuple[str, ...] = ("க்க", "த்த", "ட்ட", "ந்த", "ய", "வ")

# =============================================================================
# NOMINAL SENTENCE WHITELISTS (Zero-Copula Support)
# Sentences starting with these phrases do NOT require a finite verb.
# =============================================================================

# Core noun phrases that expect a noun complement (Subject/Possessive)
ALLOWED_NOMINAL_SUBJECTS: Tuple[str, ...] = (
    "என் பெயர்", "அவன் பெயர்", "அவள் பெயர்", "அவர் பெயர்", "இவர் பெயர்",
    "எனது பெயர்", "அவனது பெயர்", "அவளது பெயர்",
    "என் தொழில்", "அவன் தொழில்", "அவள் தொழில்", "அவர் தொழில்", "இவர் தொழில்",
    "என் வயது", "அவன் வயது", "அவள் வயது", "அவர் வயது", "இவர் வயது",
    "என் ஊர்", "அவன் ஊர்", "அவள் ஊர்",
    "என் ஊரின் பெயர்", 
    "என் பள்ளி", "என் கல்லூரி", 
    "என் பள்ளியின் பெயர்", "என் கல்லூரியின் பெயர்",
    "என் துறை", "என் படிப்பு",
    "என் கல்வி", "என் அடையாளம்", "என் கனவு", "என் லட்சியம்",
    # Generic copular subjects
    "இது", "அது", "இவர்", "அவர்", "இவள்", "அவள்",
    "இவை", "அவை",
    # Pronouns that can start nominals (e.g. நான் ஒரு மாணவர்)
    "நான்", "நீ", "நாங்கள்", "நாம்", "நீங்கள்",
)

# Predicate phrases that can end a sentence without a verb (Descriptive nouns)
ALLOWED_NOMINAL_PREDICATES: Tuple[str, ...] = (
    "மாணவர்", "மாணவன்", "மாணவி",
    "ஆசிரியர்", "ஆசிரியை",
    "மருத்துவர்", "பொறியாளர்",
    "விவசாயி", "தொழிலாளர்",
    "கலைஞர்", "படைப்பாளி",
    "ஊர்", "நகரம்", "கிராமம்",
    "பள்ளி", "கல்லூரி",
    # Common descriptors
    "அழகு", "நன்று", "சிறப்பு", "பெரிது", "சிறிது",
    "உயரம்", "குள்ளம்", "கருப்பு", "சிவப்பு",
    # Copular predicate compounds that should be treated as valid sentence endings
    "பகுதிகளாகும்",
    "அவசியமாகும்",
    "முக்கியமானதாகும்",
)


# Copular verb predicates (ஆகும்/ஆனது family) that often appear as
# "X ஆகும்", "அது முக்கியமானதாகும்", "இது அவசியமாகும்" etc.
# These should NOT trigger "verb form missing" even if they don't match
# the finite-verb suffix table, because they function as valid copular predicates.
COPULAR_PREDICATES: Tuple[str, ...] = (
    # Core forms (must-have per user requirement)
    "ஆகும்",
    "ஆனது",
    "ஆகின்றது",
    # Common variants used in school compositions
    "ஆகிறது",      # present copular
    "ஆகிவிட்டது",  # perfective copular
    "ஆகியிருக்கிறது",
    "ஆகியிருக்கும்",
    "ஆகியிருந்தது",
)


def is_copular_predicate(word: str) -> bool:
    """
    True if the word is (or ends with) a copular predicate like:
    - "ஆகும்"           → e.g. "அது அவசியமாகும்"
    - "ஆனது"           → e.g. "இது முக்கியமானதானது"
    - "ஆகின்றது"/"ஆகிறது" → present-state copular
    Also returns True for compounds ending with these, e.g.:
    - "பகுதிகளாகும்", "அவசியமாகும்", "முக்கியமானதாகும்"
    """
    if not word or len(word.strip()) < 2:
        return False
    w = word.strip()
    if w in COPULAR_PREDICATES:
        return True
    # Allow compounds like "பகுதிகளாகும்", "அவசியமாகும்"
    return any(w.endswith(root) for root in COPULAR_PREDICATES)


def detect_sentence_type(sentence: str, tokens: List[str]) -> str:
    """
    STEP 0 (MANDATORY): Detect sentence type before applying agreement rules.
    This prevents false positives on valid Tamil sentence constructions.
    
    Returns: FINITE_VERB, NOMINAL, EXISTENTIAL, MODAL, or INVALID
    """
    if not tokens or len(tokens) == 0:
        return SENTENCE_TYPE_INVALID
    
    last_token = tokens[-1].strip() if tokens else ""
    
    # Check for existential: contains உள்ளது, இல்லை, இருந்தது, இருக்கும்
    for marker in EXISTENTIAL_MARKERS:
        if marker in sentence or last_token == marker:
            return SENTENCE_TYPE_EXISTENTIAL
    
    # Check for modal: infinitive + வேண்டும் pattern
    for modal in MODAL_MARKERS:
        if modal in sentence or last_token == modal:
            # Check if there's an infinitive before the modal
            for i, tok in enumerate(tokens):
                if tok == modal and i > 0:
                    prev: str = tokens[i - 1]  # Type annotation for Pyre
                    # pyre-fixme[16]: Pyre false positive on endswith method
                    suffixes = tuple(INFINITIVE_SUFFIXES)  # Explicit tuple cast for Pyre
                    if any(prev.endswith(suf) for suf in suffixes):
                        return SENTENCE_TYPE_MODAL
            # Even without infinitive, if modal is present, treat as modal type
            if modal == last_token or modal in sentence:
                return SENTENCE_TYPE_MODAL
    
    # Check for finite verb: has any verb suffix from our mapping
    # Note: get_verb_features_from_suffix is defined later in this module
    for tok in tokens:
        features = get_verb_features_from_suffix(tok)  # Function defined below
        if features is not None:
            return SENTENCE_TYPE_FINITE_VERB
    
    # Check for nominal: sentence ends with noun (no verb suffix detected)
    # Simple heuristic: if last token is not a verb and doesn't end with verb suffix
    if last_token and get_verb_features_from_suffix(last_token) is None:
        # Could be nominal sentence
        return SENTENCE_TYPE_NOMINAL
    
    return SENTENCE_TYPE_INVALID


def should_skip_agreement_check(sentence_type: str) -> bool:
    """Return True if this sentence type should skip subject-verb agreement checks."""
    return sentence_type in (SENTENCE_TYPE_NOMINAL, SENTENCE_TYPE_EXISTENTIAL, SENTENCE_TYPE_MODAL)

# =============================================================================
# STEP 1: SUBJECT FEATURES (Agreement Features)
# =============================================================================

# Person: 1 = first, 2 = second, 3 = third
PERSON_VALUES: Tuple[int, ...] = (1, 2, 3)

# Number: Singular, Plural
NUMBER_SINGULAR: str = "SINGULAR"
NUMBER_PLURAL: str = "PLURAL"
NUMBER_VALUES: Tuple[str, ...] = (NUMBER_SINGULAR, NUMBER_PLURAL)

# Class: Male, Female, Rational (e.g. 3rd plural "they"), Irrational (e.g. "it", "they" for things)
CLASS_MALE: str = "MALE"
CLASS_FEMALE: str = "FEMALE"
CLASS_RATIONAL: str = "RATIONAL"
CLASS_IRRATIONAL: str = "IRRATIONAL"
CLASS_VALUES: Tuple[str, ...] = (CLASS_MALE, CLASS_FEMALE, CLASS_RATIONAL, CLASS_IRRATIONAL)

# Structured view of subject features (for docs / validation)
AGREEMENT_FEATURES: Dict[str, Any] = {
    "Person": list(PERSON_VALUES),
    "Number": list(NUMBER_VALUES),
    "Class": list(CLASS_VALUES),
}


def is_allowed_nominal_sentence(sentence: str) -> bool:
    """
    Check if sentence matches the allowed nominal patterns (Zero-Copula).
    Returns True if:
      1. Starts with an allowed subject (e.g. "என் பெயர்")
      2. OR Ends with an allowed predicate (e.g. "ஆசிரியர்")
    """
    if not sentence:
        return False
    
    s = sentence.strip()
    
    # Check starts with allowed subject
    for subj in ALLOWED_NOMINAL_SUBJECTS:
        if s.startswith(subj):
            return True
            
    # Check ends with allowed predicate
    for pred in ALLOWED_NOMINAL_PREDICATES:
        if s.endswith(pred):
            return True
            
    return False

# =============================================================================
# VERB SUFFIX → FEATURE MAPPING (CRITICAL — grammar engine backbone)
# Present and past endings; same agreement features apply.
# =============================================================================

# Each entry: list of suffix strings (verb ending) → person, number, class.
# Class is None where it does not apply (e.g. 1st/2nd person).
# Order: longer suffixes first when matching (e.g. கிறீர்கள் before கிறாய்).
VERB_SUFFIX_FEATURE_MAP: List[Dict[str, Any]] = [
    # 1st person singular: -கிறேன் / -த்தேன் (present / past)
    {"suffixes": ["கிறேன்", "த்தேன்", "ந்தேன்", "ட்டேன்"], "person": 1, "number": NUMBER_SINGULAR, "class": None},
    # 1st person plural: -கிறோம் / -த்தோம்
    {"suffixes": ["கிறோம்", "த்தோம்", "ந்தோம்", "ட்டோம்"], "person": 1, "number": NUMBER_PLURAL, "class": None},
    # 2nd person singular: -கிறாய் / -த்தாய்
    {"suffixes": ["கிறாய்", "த்தாய்", "ந்தாய்", "ட்டாய்"], "person": 2, "number": NUMBER_SINGULAR, "class": None},
    # 2nd person plural: -கிறீர்கள் / -த்தீர்கள்
    {"suffixes": ["கிறீர்கள்", "த்தீர்கள்", "ந்தீர்கள்", "ட்டீர்கள்"], "person": 2, "number": NUMBER_PLURAL, "class": None},
    # 3rd person singular masculine: -கிறான் / -த்தான்
    {"suffixes": ["கிறான்", "த்தான்", "ந்தான்", "ட்டான்"], "person": 3, "number": NUMBER_SINGULAR, "class": CLASS_MALE},
    # 3rd person singular feminine: -கிறாள் / -த்தாள்
    {"suffixes": ["கிறாள்", "த்தாள்", "ந்தாள்", "ட்டாள்"], "person": 3, "number": NUMBER_SINGULAR, "class": CLASS_FEMALE},
    # 3rd person plural (rational): -கிறார்கள் / -த்தார்கள்
    {"suffixes": ["கிறார்கள்", "த்தார்கள்", "ந்தார்கள்", "ட்டார்கள்"], "person": 3, "number": NUMBER_PLURAL, "class": CLASS_RATIONAL},
    # 3rd person singular (irrational): -கிறது / -த்தது
    {"suffixes": ["கிறது", "த்தது", "ந்தது", "ட்டது"], "person": 3, "number": NUMBER_SINGULAR, "class": CLASS_IRRATIONAL},
    # 3rd person plural (irrational): -கின்றன / -த்தன
    {"suffixes": ["கின்றன", "த்தன", "ந்தன", "ட்டன"], "person": 3, "number": NUMBER_PLURAL, "class": CLASS_IRRATIONAL},
]

# Flatten: all suffixes that indicate a finite verb (for quick lookup)
ALL_VERB_SUFFIXES: Tuple[str, ...] = tuple(
    s
    for entry in VERB_SUFFIX_FEATURE_MAP
    for s in entry["suffixes"]
)

# =============================================================================
# STEP 3: VERB FEATURE EXTRACTION (pure suffix matching — grammar backbone)
# Algorithm:
#   1. Identify the finite verb (usually sentence-final)
#   2. Strip tense markers (suffix table already has present/past endings)
#   3. Match ending with suffix table (VERB_SUFFIX_FEATURE_MAP)
#   4. Extract: Person, Number, Class
#   5. If no valid suffix → grammar error (incomplete verb)
# =============================================================================

# Error code when no word matches the suffix table (incomplete verb)
VERB_ERROR_INCOMPLETE: str = "INCOMPLETE_VERB"


def get_verb_features_from_suffix(verb_word: str) -> Optional[Dict[str, Any]]:
    """
    Given a verb form (e.g. படிக்கிறேன்), return agreement features if suffix matches.
    Match longest suffix first. Returns None if no match (→ incomplete verb).
    """
    if not verb_word or len(verb_word) < 2:
        return None
    word = verb_word.strip()
    # Build (suffix, entry) and sort by suffix length descending so longest match wins
    pairs: List[Tuple[str, Dict[str, Any]]] = []
    for entry in VERB_SUFFIX_FEATURE_MAP:
        for suf in entry["suffixes"]:
            pairs.append((suf, entry))
    pairs.sort(key=lambda p: len(p[0]), reverse=True)
    for suf, entry in pairs:
        if word.endswith(suf):
            return {
                "person": entry["person"],
                "number": entry["number"],
                "class": entry["class"],
            }
    return None


def extract_verb_features(verb_word: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Step 3: Verb feature extraction (pure suffix matching).
    Returns (features, error_code). If suffix matches table → (features, None).
    If no valid suffix (word non-empty but no match) → (None, VERB_ERROR_INCOMPLETE).
    """
    if not verb_word or len(verb_word.strip()) < 2:
        return (None, VERB_ERROR_INCOMPLETE)
    word = verb_word.strip()
    features = get_verb_features_from_suffix(word)
    if features is not None:
        return (features, None)
    return (None, VERB_ERROR_INCOMPLETE)


def list_all_suffixes_for_docs() -> List[Dict[str, Any]]:
    """Return a simple list of suffix → meaning for documentation."""
    meanings = [
        "1st person singular",
        "1st person plural",
        "2nd person singular",
        "2nd person plural",
        "3rd person singular masculine",
        "3rd person singular feminine",
        "3rd person plural (rational)",
        "3rd person singular (irrational)",
        "3rd person plural (irrational)",
    ]
    return [
        {"suffixes": e["suffixes"], "meaning": meanings[i], **{k: v for k, v in e.items() if k != "suffixes"}}
        for i, e in enumerate(VERB_SUFFIX_FEATURE_MAP)
    ]


# =============================================================================
# STEP 2: SUBJECT DETECTION (Rule-Based)
# Tamil subjects: pronouns (நான், நீ, அவன், ...) or nominative nouns (no case suffix).
# =============================================================================

# Case markers that indicate NOT subject — ignore words ending with these
# (accusative -ஐ, dative -க்கு, comitative -உடன், instrumental -ஆல்)
NOT_SUBJECT_CASE_MARKERS: Tuple[str, ...] = (
    "ஐ", "யை",           # accusative
    "க்கு", "யக்கு", "களுக்கு", "ங்களுக்கு",  # dative (longer first when used in code)
    "உடன்", "யுடன்", "ஓடு", "யோடு",       # comitative
    "ஆல்", "யால்", "களால்", "ங்களால்",     # instrumental
)

# Pronoun → feature mapping (person, number, class)
# Prefer pronouns for subject extraction.
PRONOUN_SUBJECT_FEATURES: Dict[str, Dict[str, Any]] = {
    # 1st person singular
    "நான்": {"person": 1, "number": NUMBER_SINGULAR, "class": None},
    # 1st person plural
    "நாம்": {"person": 1, "number": NUMBER_PLURAL, "class": None},
    "நாங்கள்": {"person": 1, "number": NUMBER_PLURAL, "class": None},
    "நாங்க": {"person": 1, "number": NUMBER_PLURAL, "class": None},
    # 2nd person singular
    "நீ": {"person": 2, "number": NUMBER_SINGULAR, "class": None},
    # 2nd person plural
    "நீங்கள்": {"person": 2, "number": NUMBER_PLURAL, "class": None},
    "நீங்க": {"person": 2, "number": NUMBER_PLURAL, "class": None},
    # 3rd person singular male
    "அவன்": {"person": 3, "number": NUMBER_SINGULAR, "class": CLASS_MALE},
    "இவன்": {"person": 3, "number": NUMBER_SINGULAR, "class": CLASS_MALE},
    # 3rd person singular female
    "அவள்": {"person": 3, "number": NUMBER_SINGULAR, "class": CLASS_FEMALE},
    "இவள்": {"person": 3, "number": NUMBER_SINGULAR, "class": CLASS_FEMALE},
    # 3rd person plural rational
    "அவர்கள்": {"person": 3, "number": NUMBER_PLURAL, "class": CLASS_RATIONAL},
    "இவர்கள்": {"person": 3, "number": NUMBER_PLURAL, "class": CLASS_RATIONAL},
    "எவர்கள்": {"person": 3, "number": NUMBER_PLURAL, "class": CLASS_RATIONAL},
    # 3rd person singular irrational
    "அது": {"person": 3, "number": NUMBER_SINGULAR, "class": CLASS_IRRATIONAL},
    "இது": {"person": 3, "number": NUMBER_SINGULAR, "class": CLASS_IRRATIONAL},
    "எது": {"person": 3, "number": NUMBER_SINGULAR, "class": CLASS_IRRATIONAL},
    # 3rd person plural irrational
    "அவை": {"person": 3, "number": NUMBER_PLURAL, "class": CLASS_IRRATIONAL},
    "இவை": {"person": 3, "number": NUMBER_PLURAL, "class": CLASS_IRRATIONAL},
}

# All known subject pronouns (for quick "is pronoun?" check)
SUBJECT_PRONOUNS: Tuple[str, ...] = tuple(PRONOUN_SUBJECT_FEATURES.keys())


def word_ends_with_not_subject_marker(word: str) -> bool:
    """
    True if word ends with a case marker that indicates it is NOT a subject
    (accusative -ஐ, dative -க்கு, comitative -உடன், instrumental -ஆல்).
    """
    if not word or len(word) < 2:
        return False
    w = word.strip()
    for suf in NOT_SUBJECT_CASE_MARKERS:
        if w.endswith(suf):
            return True
    return False


def get_subject_features_from_pronoun(word: str) -> Optional[Dict[str, Any]]:
    """
    If word is a known subject pronoun, return {person, number, class}.
    Otherwise return None. Use for subject detection (prefer pronouns).
    """
    if not word:
        return None
    w = word.strip()
    return PRONOUN_SUBJECT_FEATURES.get(w)


def word_can_be_subject(word: str) -> bool:
    """
    Simple subject extraction rule: word can be subject if
    (1) it does NOT end with accusative/dative/comitative/instrumental marker, and
    (2) it is a known pronoun OR a nominative noun (no case suffix).
    """
    if not word or len(word) < 2:
        return False
    w = word.strip()
    if word_ends_with_not_subject_marker(w):
        return False
    return True


def is_subject_pronoun(word: str) -> bool:
    """True if word is a known subject pronoun."""
    if not word:
        return False
    return word.strip() in PRONOUN_SUBJECT_FEATURES


# =============================================================================
# STEP 4: AGREEMENT CHECK LOGIC
# Rule: IF subject.person != verb.person OR subject.number != verb.number
#       OR subject.class != verb.class → SUBJECT_VERB_AGREEMENT_ERROR
# =============================================================================

AGREEMENT_ERROR_RULE: str = "SUBJECT_VERB_AGREEMENT_ERROR"


def agreement_check(
    subject_features: Dict[str, Any], verb_features: Dict[str, Any]
) -> Tuple[bool, Optional[str]]:
    """
    Step 4: Agreement check. Subject and verb must match on person, number, and class.
    Returns (True, None) if they agree; (False, AGREEMENT_ERROR_RULE) if not.
    Rule: IF subject.person != verb.person OR subject.number != verb.number
          OR subject.class != verb.class → SUBJECT_VERB_AGREEMENT_ERROR
    Class: only compared when both have a class value (3rd person); 1st/2nd person have class=None.
    """
    if subject_features.get("person") != verb_features.get("person"):
        return (False, AGREEMENT_ERROR_RULE)
    if subject_features.get("number") != verb_features.get("number"):
        return (False, AGREEMENT_ERROR_RULE)
    sub_class = subject_features.get("class")
    verb_class = verb_features.get("class")
    if sub_class is not None and verb_class is not None and sub_class != verb_class:
        return (False, AGREEMENT_ERROR_RULE)
    return (True, None)


# =============================================================================
# STEP 5: TAMIL-SPECIFIC EDGE CASES (first priority to these rules)
# =============================================================================
#
# 1. Dropped subject: If verb is 1st/2nd person → implicit subject allowed. Do NOT flag error.
# 2. Honorific plural (நீங்கள்): If subject == நீங்கள், allow plural verb only (already enforced by number).
# 3. Collective nouns (irrational): If noun is irrational → verb must be irrational form.
# =============================================================================

# Subject pronouns that take plural verb only (honorific); agreement already enforces number=PLURAL.
HONORIFIC_PLURAL_SUBJECTS: Tuple[str, ...] = ("நீங்கள்", "நீங்க")

# Irrational collective nouns — subject is 3rd singular irrational; verb must be irrational form (e.g. -கிறது, -த்தது).
# கூட்டம் வந்தார்கள் ❌ (rational plural verb); கூட்டம் வந்தது ✅ (irrational verb).
IRRATIONAL_COLLECTIVE_NOUNS: Tuple[str, ...] = (
    "கூட்டம்", "குழு", "கூடு", "அணி", "கட்சி", "சங்கம்", "மன்றம்",
    "குழுமம்", "கழகம்", "அமைப்பு", "நிறுவனம்", "அரசு", "மாநாடு",
)


def implicit_subject_allowed(verb_features: Dict[str, Any]) -> bool:
    """
    Step 5 edge case 1: If verb is 1st/2nd person → implicit subject allowed. Do NOT flag error.
    """
    if not verb_features:
        return False
    person = verb_features.get("person")
    return person == 1 or person == 2


def get_subject_features_for_irrational_noun(noun: str) -> Optional[Dict[str, Any]]:
    """
    Step 5 edge case 3: If noun is irrational (collective) → return subject features
    (person=3, number=SINGULAR, class=IRRATIONAL). Verb must then be irrational form.
    """
    if not noun:
        return None
    w = noun.strip()
    if w in IRRATIONAL_COLLECTIVE_NOUNS:
        return {"person": 3, "number": NUMBER_SINGULAR, "class": CLASS_IRRATIONAL}
    return None


def is_irrational_collective_noun(word: str) -> bool:
    """True if word is an irrational collective noun (verb must be irrational form)."""
    if not word:
        return False
    return word.strip() in IRRATIONAL_COLLECTIVE_NOUNS


# =============================================================================
# GRAMMAR RULE 2: TENSE CONSISTENCY
# Tamil tense consistency depends on three signals:
#   1. Time markers (explicit) — beat verb form
#   2. Verb tense suffixes (implicit)
#   3. Clause boundaries (scope) — reset rules
# =============================================================================

# Tense values
TENSE_PAST: str = "PAST"
TENSE_PRESENT: str = "PRESENT"
TENSE_FUTURE: str = "FUTURE"
TENSE_UNKNOWN: str = "UNKNOWN"

# STEP 2: Time Marker Table (Backbone) — explicit time markers beat verb tense
# Expanded with 90%+ coverage of common time markers students use
TIME_MARKER_TABLE: Dict[str, str] = {
    # PAST markers
    "நேற்று": TENSE_PAST,
    "நேற்றுமுன்தினம்": TENSE_PAST,
    "நேற்று முன்தினம்": TENSE_PAST,
    "முன்தினம்": TENSE_PAST,
    "முன்பு": TENSE_PAST,
    "முன்னர்": TENSE_PAST,
    "முன்னதாக": TENSE_PAST,
    "முற்காலத்தில்": TENSE_PAST,
    "ஒருகாலத்தில்": TENSE_PAST,
    "அன்று": TENSE_PAST,
    "அப்போது": TENSE_PAST,
    "பழைய": TENSE_PAST,
    "பழைய காலம்": TENSE_PAST,
    "கடந்த": TENSE_PAST,
    "கடந்த வாரம்": TENSE_PAST,
    "கடந்த மாதம்": TENSE_PAST,
    "கடந்த வருடம்": TENSE_PAST,
    "கடந்த ஆண்டு": TENSE_PAST,
    "முந்தைய": TENSE_PAST,
    "முந்தைய நாள்": TENSE_PAST,
    "முன் வருடம்": TENSE_PAST,
    "சென்ற": TENSE_PAST,
    "சென்ற வாரம்": TENSE_PAST,
    "சென்ற மாதம்": TENSE_PAST,
    "சென்ற வருடம்": TENSE_PAST,
    "இறந்த காலம்": TENSE_PAST,
    
    # PRESENT markers
    "இன்று": TENSE_PRESENT,
    "இப்போது": TENSE_PRESENT,
    "இப்பொழுது": TENSE_PRESENT,
    "தற்போது": TENSE_PRESENT,
    "தற்சமயம்": TENSE_PRESENT,
    "இப்பொழுதைக்கு": TENSE_PRESENT,
    "இன்றைக்கு": TENSE_PRESENT,
    "தற்காலம்": TENSE_PRESENT,
    "தற்காலத்தில்": TENSE_PRESENT,
    "இந்த நேரம்": TENSE_PRESENT,
    "இந்த காலம்": TENSE_PRESENT,
    "தற்போதைய": TENSE_PRESENT,
    "நடப்பு": TENSE_PRESENT,
    "நடப்பில்": TENSE_PRESENT,
    "நிகழ்காலம்": TENSE_PRESENT,
    "நிகழ்காலத்தில்": TENSE_PRESENT,
    "இப்பொழுதெல்லாம்": TENSE_PRESENT,
    "இன்றைய": TENSE_PRESENT,
    "இப்போதெல்லாம்": TENSE_PRESENT,
    "தற்போதெல்லாம்": TENSE_PRESENT,
    
    # FUTURE markers
    "நாளை": TENSE_FUTURE,
    "நாளைமறுநாள்": TENSE_FUTURE,
    "நாளை மறுநாள்": TENSE_FUTURE,
    "மறுநாள்": TENSE_FUTURE,
    "நாளைக்கு": TENSE_FUTURE,
    "எதிர்காலம்": TENSE_FUTURE,
    "எதிர்காலத்தில்": TENSE_FUTURE,
    "எதிர்காலத்திற்கு": TENSE_FUTURE,
    "வரும்": TENSE_FUTURE,
    "வரும் வாரம்": TENSE_FUTURE,
    "வரும் மாதம்": TENSE_FUTURE,
    "வரும் வருடம்": TENSE_FUTURE,
    "வரும் ஆண்டு": TENSE_FUTURE,
    "அடுத்த": TENSE_FUTURE,
    "அடுத்த நாள்": TENSE_FUTURE,
    "அடுத்த வாரம்": TENSE_FUTURE,
    "அடுத்த மாதம்": TENSE_FUTURE,
    "அடுத்த வருடம்": TENSE_FUTURE,
    "பிறகு": TENSE_FUTURE,
    "பின்னர்": TENSE_FUTURE,
    "பின்பு": TENSE_FUTURE,
    "எதிர்வரும்": TENSE_FUTURE,
    "எதிர்வரும் காலம்": TENSE_FUTURE,
}

# All time marker words (for quick lookup)
TIME_MARKERS: Tuple[str, ...] = tuple(TIME_MARKER_TABLE.keys())


def detect_explicit_time_marker(sentence: str) -> Optional[str]:
    """
    Detect explicit time marker in sentence. Time marker beats verb form.
    Returns TENSE_PAST, TENSE_PRESENT, TENSE_FUTURE, or None if no marker found.
    """
    if not sentence:
        return None
    for marker, tense in TIME_MARKER_TABLE.items():
        if marker in sentence:
            return tense
    return None


# Verb tense suffixes (implicit tense from verb form) — EXPANDED for 90%+ coverage
# STEP 4: Verb Suffix → Tense Table (last tense-bearing morpheme only)
VERB_TENSE_PAST_SUFFIXES: Tuple[str, ...] = (
    # த் series (most common)
    "த்தேன்", "த்தாய்", "த்தான்", "த்தாள்", "த்தார்", "த்தது",
    "த்தோம்", "த்தீர்கள்", "த்தார்கள்", "த்தன",
    # த series (without doubling — செய்தான், போனான், etc.)
    "தேன்", "தாய்", "தான்", "தாள்", "தார்", "தது",
    "தோம்", "தீர்கள்", "தார்கள்", "தன",
    # ந் series
    "ந்தேன்", "ந்தாய்", "ந்தான்", "ந்தாள்", "ந்தார்", "ந்தது",
    "ந்தோம்", "ந்தீர்கள்", "ந்தார்கள்", "ந்தன",
    # ன் series (வந்தான், சென்றான், etc.)
    "ன்றேன்", "ன்றாய்", "ன்றான்", "ன்றாள்", "ன்றார்", "ன்றது",
    "ன்றோம்", "ன்றீர்கள்", "ன்றார்கள்", "ன்றன",
    # ட் series
    "ட்டேன்", "ட்டாய்", "ட்டான்", "ட்டாள்", "ட்டார்", "ட்டது",
    "ட்டோம்", "ட்டீர்கள்", "ட்டார்கள்", "ட்டன",
    # ற் series (சென்றான், etc.)
    "ற்றேன்", "ற்றாய்", "ற்றான்", "ற்றாள்", "ற்றார்", "ற்றது",
    "ற்றோம்", "ற்றீர்கள்", "ற்றார்கள்", "ற்றன",
    # ன series (simple — வந்தான் variation)
    "னேன்", "னாய்", "னான்", "னாள்", "னார்", "னது",
    "னோம்", "னீர்கள்", "னார்கள்", "னன",
)

VERB_TENSE_PRESENT_SUFFIXES: Tuple[str, ...] = (
    # கிற series (most common present)
    "கிறேன்", "கிறாய்", "கிறான்", "கிறாள்", "கிறார்", "கிறது",
    "கிறோம்", "கிறீர்கள்", "கிறார்கள்", "கின்றன",
    # க்கிற series (doubled)
    "க்கிறேன்", "க்கிறாய்", "க்கிறான்", "க்கிறாள்", "க்கிறார்", "க்கிறது",
    "க்கிறோம்", "க்கிறீர்கள்", "க்கிறார்கள்", "க்கின்றன",
)

VERB_TENSE_FUTURE_SUFFIXES: Tuple[str, ...] = (
    # வ series (simple future)
    "வேன்", "வாய்", "வான்", "வாள்", "வார்", "வது",
    "வோம்", "வீர்கள்", "வார்கள்", "வன",
    # ப்ப series (doubled future)
    "ப்பேன்", "ப்பாய்", "ப்பான்", "ப்பாள்", "ப்பார்", "ப்பது",
    "ப்போம்", "ப்பீர்கள்", "ப்பார்கள்", "ப்பன",
    # க்க series (another future form)
    "க்கேன்", "க்காய்", "க்கான்", "க்காள்", "க்கார்", "க்கது",
    "க்கோம்", "க்கீர்கள்", "க்கார்கள்", "க்கன",
    # ள் series (இருப்பேன் type)
    "ள்ளேன்", "ள்ளாய்", "ள்ளான்", "ள்ளாள்", "ள்ளார்", "ள்ளது",
    "ள்ளோம்", "ள்ளீர்கள்", "ள்ளார்கள்", "ள்ளன",
)

# -------------------------------------------------------------------------
# RULE 3: Finite verb suffix copies (for dedicated Rule-3 logic)
# These are simple aliases to the main tense-suffix tables and state-verbs,
# so Rule-3 can evolve separately without touching the core backbone.
# -------------------------------------------------------------------------

# Whitelisted finite state verbs that should still participate in tense consistency
# (Moved here to avoid forward reference error)
FINITE_STATE_VERBS: Tuple[str, ...] = (
    "உள்ளது",
    "இருந்தது",
    "இருக்கும்",
    "ஆகும்",
    "ஆனது",
)

RULE3_FINITE_PAST_SUFFIXES: Tuple[str, ...] = VERB_TENSE_PAST_SUFFIXES
RULE3_FINITE_PRESENT_SUFFIXES: Tuple[str, ...] = VERB_TENSE_PRESENT_SUFFIXES
RULE3_FINITE_FUTURE_SUFFIXES: Tuple[str, ...] = VERB_TENSE_FUTURE_SUFFIXES
RULE3_FINITE_STATE_VERBS: Tuple[str, ...] = FINITE_STATE_VERBS

# Simple state-verb → tense mapping (for existential/state forms without clear suffix)
STATE_VERB_TENSE_MAP: Dict[str, str] = {
    "உள்ளது": TENSE_PRESENT,
    "இருந்தது": TENSE_PAST,
    "இருக்கும்": TENSE_FUTURE,
    "ஆகும்": TENSE_FUTURE,
    "ஆனது": TENSE_PAST,
}


def detect_verb_tense_from_suffix(verb_word: str) -> Optional[str]:
    """
    Detect tense from verb suffix (implicit tense).
    Returns TENSE_PAST, TENSE_PRESENT, TENSE_FUTURE, or None.
    """
    if not verb_word or len(verb_word) < 2:
        return None
    
    word = verb_word.strip()
    
    # Direct mapping for simple state/existential verbs
    if word in STATE_VERB_TENSE_MAP:
        return STATE_VERB_TENSE_MAP[word]
    
    # Check past (longest suffixes first)
    for suf in sorted(VERB_TENSE_PAST_SUFFIXES, key=len, reverse=True):
        if word.endswith(suf):
            return TENSE_PAST
    
    # Check present
    for suf in sorted(VERB_TENSE_PRESENT_SUFFIXES, key=len, reverse=True):
        if word.endswith(suf):
            return TENSE_PRESENT
    
    # Check future
    for suf in sorted(VERB_TENSE_FUTURE_SUFFIXES, key=len, reverse=True):
        if word.endswith(suf):
            return TENSE_FUTURE
    
    return None


def detect_sentence_tense(sentence: str, verb_word: Optional[str] = None) -> str:
    """
    Detect sentence tense using time markers (priority) or verb suffix.
    Rule: Time marker beats verb form.
    Returns TENSE_PAST, TENSE_PRESENT, TENSE_FUTURE, or TENSE_UNKNOWN.
    """
    # Priority 1: Explicit time marker (beats verb form)
    explicit_tense = detect_explicit_time_marker(sentence)
    if explicit_tense:
        return explicit_tense
    
    # Priority 2: Verb tense suffix (implicit)
    if verb_word:
        verb_tense = detect_verb_tense_from_suffix(verb_word)
        if verb_tense:
            return verb_tense
    
    return TENSE_UNKNOWN


def should_check_tense_consistency(sentence: str) -> bool:
    """
    Rule: IF no time marker in clause → DO NOT run tense consistency rule.
    This prevents mass false positives (many valid paragraphs don't use time markers).
    Returns True only if sentence has an explicit time marker.
    """
    return detect_explicit_time_marker(sentence) is not None


# =============================================================================
# STEP 3: Detect Finite Verbs (for tense consistency)
# Ignore nominalized, infinitives, modals, existentials — these don't participate in tense consistency.
# =============================================================================

# Nominalized verb suffixes (verbal nouns — ignore for tense)
NOMINALIZED_VERB_SUFFIXES: Tuple[str, ...] = ("வது", "தல்", "கை", "பு", "வு")

# Infinitive suffixes (ignore for tense)
INFINITIVE_VERB_SUFFIXES: Tuple[str, ...] = ("அ", "க்க", "ய", "வ")

# Modal markers (ignore for tense consistency)
MODAL_VERB_MARKERS: Tuple[str, ...] = ("வேண்டும்", "கூடாது", "லாம்", "மாட்டேன்", "மாட்டான்", "மாட்டாள்")

# Existential markers (ignore for tense consistency)
EXISTENTIAL_VERB_MARKERS: Tuple[str, ...] = ("உள்ளது", "இல்லை", "இருந்தது", "இருக்கும்", "உண்டு", "இல்லாது")


def is_finite_verb_for_tense(verb_word: str, sentence: str) -> bool:
    """
    Check if verb is finite (participates in tense consistency).
    Ignore: nominalized (-வது), infinitives (-அ), modals (வேண்டும்), existentials (உள்ளது).
    Returns True only if verb is a true finite verb (conjugated with person/number).
    """
    if not verb_word or len(verb_word) < 2:
        return False
    
    word = verb_word.strip()
    
    # Whitelist simple state verbs as finite (even though they are existential)
    if word in FINITE_STATE_VERBS:
        return True
    
    # Ignore nominalized verbs
    if any(word.endswith(suf) for suf in NOMINALIZED_VERB_SUFFIXES):
        return False
    
    # Ignore infinitives
    if any(word.endswith(suf) for suf in INFINITIVE_VERB_SUFFIXES):
        return False
    
    # Ignore modals
    if any(modal in word or modal in sentence for modal in MODAL_VERB_MARKERS):
        return False
    
    # Ignore existentials
    if any(exist in word or exist in sentence for exist in EXISTENTIAL_VERB_MARKERS):
        return False
    
    # Check if verb has finite suffix (from our mapping)
    if get_verb_features_from_suffix(word) is not None:
        return True
    
    return False


# =============================================================================
# RULE 3 — VERB ANCHORING (Phase 2)
# Step 2.1: Locate the finite verb index. This verb is the anchor.
# Uses RULE3_* finite suffix/state lists only.
# =============================================================================

# Step 3.1: Case markers (Rule-3 only)
# Hardcoded minimal set of case markers we care about for Rule-3 word-order logic.
# Anything with one of these markers is "safe" after the verb (role is explicit).
CASE_MARKERS: Tuple[str, ...] = (
    # Accusative (object) - various forms with euphonic changes
    "ஐ",        # accusative (direct form)
    "யை",       # accusative (after vowel)
    "த்தை",     # accusative (after consonant)
    "ஆய்",      # accusative (variant)
    "வை",       # accusative (variant)
    "னை",       # accusative (variant)
    
    # Dative (to/for)
    "க்கு",     # dative (direct form)
    "உக்கு",    # dative (after vowel)
    "க்கு",     # dative (standard)
    
    # Locative (in/at)
    "இல்",      # locative
    "யில்",     # locative (after vowel)
    "இடம்",     # locative (place)
    
    # Comitative (with)
    "உடன்",     # comitative
    "ஓடு",      # comitative (variant)
    
    # Instrumental (by/with)
    "ஆல்",      # instrumental
    "ஆலே",      # instrumental (variant)
    
    # Ablative (from)
    "இருந்து",  # ablative
    "இல் இருந்து",  # ablative (from in)
)


def get_case_marker(word: str) -> Optional[str]:
    """
    Return the case marker suffix if the word ends with one of Rule-3 CASE_MARKERS,
    else return None.
    """
    if not word or len(word) < 2:
        return None
    w = word.strip()
    for suf in sorted(CASE_MARKERS, key=len, reverse=True):
        if w.endswith(suf):
            return suf
    return None


def word_has_case_marker(word: str) -> bool:
    """True if token ends with any Rule-3 CASE_MARKERS."""
    return get_case_marker(word) is not None


# =============================================================================
# STEP 3.3: IGNORE NON-NOUNS (adverbs, particles, conjunctions)
# Only nouns matter for word order checking after the verb.
# =============================================================================

# Tamil Adverbs — comprehensive list covering temporal, manner, degree, and frequency adverbs
# Temporal adverbs are already in TIME_MARKERS (lines 492), so we include them here too
TAMIL_ADVERBS: Tuple[str, ...] = (
    # Temporal adverbs (time-related)
    "நேற்று", "இன்று", "நாளை", "இப்போது", "இப்பொழுது", "தற்போது",
    "முன்பு", "பின்பு", "பிறகு", "பின்னர்", "முன்னர்", "அப்போது",
    "எப்போது", "எப்பொழுது", "எப்போதும்", "எப்பொழுதும்",
    "அடிக்கடி", "எப்பொழுதாவது", "சில நேரம்", "சில வேளை",
    "தினமும்", "தினந்தோறும்", "நாள்தோறும்", "வாரந்தோறும்",
    "மாதந்தோறும்", "ஆண்டுதோறும்", "எப்போதாவது",
    "இடையிடையே", "அவ்வப்போது", "சில சமயம்",
    
    # Manner adverbs (how something is done)
    "மெதுவாக", "விரைவாக", "வேகமாக", "நன்றாக", "நன்கு",
    "சரியாக", "தவறாக", "நேர்மையாக", "உண்மையாக",
    "கவனமாக", "கவனத்துடன்", "எளிதாக", "கடினமாக",
    "அழகாக", "அமைதியாக", "சத்தமாக", "மெல்ல", "வேகமாய்",
    "திடீரென்று", "திடீரென", "மெதுவாய்", "வேகமாய்",
    "உடனடியாக", "உடனே", "உடன்", "தாமதமாக",
    
    # Degree adverbs (intensity/extent)
    "மிகவும்", "மிக", "மிகுதியாக", "மிகையாக", "அதிகமாக",
    "குறைவாக", "சற்று", "சிறிது", "கொஞ்சம்", "நிறைய",
    "மிகுதியாய்", "அளவுக்கு", "அதிகம்", "குறைவு",
    "முழுமையாக", "முழுவதுமாக", "பகுதியாக", "ஓரளவு",
    "போதுமான", "போதும்", "மட்டும்", "மட்டுமே",
    
    # Frequency adverbs (how often)
    "எப்போதும்", "எப்பொழுதும்", "அடிக்கடி", "எப்போதாவது",
    "அரிதாக", "எப்போதுமே", "ஒருபோதும்", "ஒருபோதுமே",
    "சில நேரங்களில்", "பெரும்பாலும்", "பொதுவாக",
    "வழக்கமாக", "சாதாரணமாக", "இயல்பாக",
    
    # Locative adverbs (where/direction - but not nouns)
    "இங்கே", "அங்கே", "எங்கே", "எங்கும்", "எல்லாம்",
    "மேலே", "கீழே", "உள்ளே", "வெளியே", "முன்னே", "பின்னே",
    "அருகே", "தூரத்தில்", "அருகில்", "பக்கத்தில்",
)

# Tamil Conjunctions — comprehensive list covering coordinating and subordinating conjunctions
# Many are already in CLAUSE_BOUNDARY_MARKERS (lines 880-935), included here for completeness
TAMIL_CONJUNCTIONS: Tuple[str, ...] = (
    # Coordinating conjunctions (connect equal elements)
    "மற்றும்", "அல்லது", "ஆனால்", "ஆனாலும்",
    "அத்துடன்", "மேலும்", "கூட", "உம்",
    
    # Subordinating conjunctions (cause, reason, condition, contrast)
    "ஏனெனில்", "ஏனென்றால்", "எனவே", "ஆகையால்", "ஆதலால்",
    "அதனால்", "அதால்", "அதனால்தான்", "அதற்காக", "அதற்கென",
    "என்றாலும்", "இருந்தாலும்", "இருப்பினும்", "எனினும்",
    "ஆயினும்", "ஆயின்", "என்றால்", "எனில்",
    
    # Quotative/reported speech markers
    "என்று", "என்றார்", "என்றான்", "என்றாள்", "என்றனர்",
    "என்பது", "என்பதால்", "என்பதையும்",
    
    # Sequential/temporal conjunctions
    "பிறகு", "பின்னர்", "பின்பு", "அதன்பின்", "அதன்பிறகு",
    "அதன்பின்னர்", "அப்போது", "முன்பு", "முன்னர்",
    
    # Additive conjunctions
    "மட்டுமல்ல", "மட்டுமல்லாமல்", "மட்டுமின்றி",
    
    # Contrastive conjunctions
    "ஆனால்", "ஆனாலும்", "என்றாலும்", "இருந்தாலும்",
)

# Tamil Particles — question, emphasis, and negative particles
TAMIL_PARTICLES: Tuple[str, ...] = (
    # Question particles
    "ஆ", "ஏ", "ஓ", "அ",
    
    # Emphasis particles
    "தான்", "தானே", "அல்லவா", "அல்லவோ",
    "தானா", "ஏ", "ஓ", "ஆ",
    "கூட", "மட்டும்", "மட்டுமே", "மட்டுமல்ல",
    "என்று", "என", "எனும்",
    
    # Negative particles
    "இல்லை", "அல்ல", "இல்லாமல்", "அல்லாமல்",
    "இல்லாது", "அல்லாது", "இல்லாத", "அல்லாத",
    "இன்றி", "அன்றி", "அற்ற", "இல்லா",
)


def is_tamil_adverb(word: str) -> bool:
    """
    Step 3.3: Check if word is a Tamil adverb.
    Returns True if word is in TAMIL_ADVERBS or TIME_MARKERS.
    """
    if not word:
        return False
    w = word.strip()
    # Check against comprehensive adverb list
    if w in TAMIL_ADVERBS:
        return True
    # Also check against TIME_MARKERS (temporal adverbs)
    if w in TIME_MARKERS:
        return True
    return False


def is_tamil_conjunction(word: str) -> bool:
    """
    Step 3.3: Check if word is a Tamil conjunction.
    Returns True if word is in TAMIL_CONJUNCTIONS or CLAUSE_BOUNDARY_MARKERS.
    """
    if not word:
        return False
    w = word.strip()
    # Check against comprehensive conjunction list
    if w in TAMIL_CONJUNCTIONS:
        return True
    # Also check against CLAUSE_BOUNDARY_MARKERS
    if w in CLAUSE_BOUNDARY_MARKERS:
        return True
    return False


def is_tamil_particle(word: str) -> bool:
    """
    Step 3.3: Check if word is a Tamil particle.
    Returns True if word is in TAMIL_PARTICLES.
    """
    if not word:
        return False
    w = word.strip()
    return w in TAMIL_PARTICLES


def is_noun_candidate(word: str) -> bool:
    """
    Step 3.3: Determine if a word could be a noun (after filtering out non-nouns).
    
    Returns False if word is:
    - An adverb (temporal, manner, degree, frequency)
    - A conjunction (coordinating, subordinating)
    - A particle (question, emphasis, negative)
    - A pronoun (already defined in SUBJECT_PRONOUNS)
    - A verb (has verb suffix from VERB_SUFFIX_FEATURE_MAP)
    
    Returns True otherwise (potential noun candidate).
    """
    if not word or len(word) < 2:
        return False
    
    w = word.strip()
    
    # Step 3.3 Rule: IF T is ADVERB → CONTINUE (return False)
    if is_tamil_adverb(w):
        return False
    
    # Step 3.3 Rule: IF T is PARTICLE / CONJUNCTION → CONTINUE (return False)
    if is_tamil_conjunction(w):
        return False
    if is_tamil_particle(w):
        return False
    
    # Additional filtering: pronouns are not nouns for word order purposes
    if is_subject_pronoun(w):
        return False
    
    # Additional filtering: words with verb suffixes are not nouns
    if get_verb_features_from_suffix(w) is not None:
        return False
    
    # Step 3.3 Rule: IF T is NOT a NOUN → CONTINUE
    # At this point, if it's not an adverb, conjunction, particle, pronoun, or verb,
    # we consider it a potential noun candidate
    return True


def is_finite_verb_for_rule3(verb_word: str, sentence: str) -> bool:
    """
    True if token is a finite verb for Rule-3 (uses RULE3_* suffix/state lists).
    Excludes nominalized (-வது), infinitives (-அ), modals (வேண்டும்).
    """
    if not verb_word or len(verb_word) < 2:
        return False
    word = verb_word.strip()

    # State-verb whitelist for Rule-3
    if word in RULE3_FINITE_STATE_VERBS:
        return True

    # Exclude nominalized
    if any(word.endswith(suf) for suf in NOMINALIZED_VERB_SUFFIXES):
        return False
    # Exclude infinitives
    if any(word.endswith(suf) for suf in INFINITIVE_VERB_SUFFIXES):
        return False
    # Exclude modals
    if any(modal in word or modal in sentence for modal in MODAL_VERB_MARKERS):
        return False

    # Match any Rule-3 finite suffix (past / present / future)
    for suf in sorted(RULE3_FINITE_PAST_SUFFIXES, key=len, reverse=True):
        if word.endswith(suf):
            return True
    for suf in sorted(RULE3_FINITE_PRESENT_SUFFIXES, key=len, reverse=True):
        if word.endswith(suf):
            return True
    for suf in sorted(RULE3_FINITE_FUTURE_SUFFIXES, key=len, reverse=True):
        if word.endswith(suf):
            return True
    return False


def locate_finite_verb_index(tokens: List[str], sentence: str) -> Tuple[Optional[int], Optional[str]]:
    """
    Step 2.1: Locate the finite verb index. The verb is the anchor.
    Returns (verb_index, verb_word) when there is exactly one finite verb in the token list;
    otherwise returns (None, None).
    """
    if not tokens or not sentence:
        return (None, None)
    sentence_str = sentence.strip() if isinstance(sentence, str) else ""
    indices: List[int] = []
    verb_word_at: Optional[str] = None
    for i, tok in enumerate(tokens):
        clean = tok.strip(".,!?।:;") if tok else ""
        if not clean:
            continue
        if is_finite_verb_for_rule3(clean, sentence_str):
            indices.append(i)
            verb_word_at = clean
    if len(indices) != 1:
        return (None, None)
    return (indices[0], verb_word_at)


def check_post_verb_word_order(tokens: List[str], verb_index: int, sentence: str) -> List[Dict]:
    """
    Rule-3 core logic: Check word order for tokens AFTER the finite verb.
    
    In Tamil, the finite verb closes the sentence.
    Anything that comes after the verb must have its grammatical role clearly marked.
    
    Algorithm:
        START checking from the token immediately AFTER the finite verb
        IGNORE all tokens before the verb
        FOR each token T in tokens[verb_index + 1 : end]:
            Step 3.3: IF T is NOT a noun → CONTINUE (skip non-nouns)
            Step 3.4: IF T is NOUN AND T has NO case marker:
                RAISE WORD_ORDER_VIOLATION
                STOP processing sentence (one violation is enough)
    
    Args:
        tokens: Tokenized sentence
        verb_index: Index of the finite verb (the anchor)
        sentence: Full sentence string (for context)
    
    Returns:
        List of error dictionaries for word order violations (max 1 error)
    """
    errors: List[Dict] = []
    
    if not tokens or verb_index is None or verb_index < 0:
        return errors
    
    # Core rule: START checking from the token immediately AFTER the finite verb
    # IGNORE all tokens before the verb
    for i in range(verb_index + 1, len(tokens)):
        token = tokens[i]
        if not token:
            continue
        
        clean_token = token.strip(".,!?।:;")
        if not clean_token:
            continue
        
        # =============================================================================
        # STEP 3.3: IGNORE NON-NOUNS
        # IF T is ADVERB → CONTINUE
        # IF T is PARTICLE / CONJUNCTION → CONTINUE
        # IF T is NOT a NOUN → CONTINUE
        # Only nouns matter for word order checking.
        # =============================================================================
        
        # Step 3.3: Filter out non-nouns (adverbs, conjunctions, particles)
        if not is_noun_candidate(clean_token):
            # Token is an adverb, conjunction, particle, pronoun, or verb → SKIP
            continue
        
        # =============================================================================
        # STEP 3.4: CORE VIOLATION CHECK (THIS IS THE RULE)
        # IF T is NOUN
        # AND T has NO case marker:
        #     RAISE WORD_ORDER_VIOLATION
        #     STOP processing sentence
        # 
        # One violation is enough. Do not continue scanning.
        # =============================================================================
        
        # At this point, token is a NOUN candidate (Step 3.3 passed)
        # Check if this post-verb noun has a clear grammatical role marker
        if word_has_case_marker(clean_token):
            # Token has case marker → grammatical role is explicit → SAFE
            # Continue checking next tokens
            continue
        
        # Step 3.4: Token is a NOUN without case marker after verb
        # This is a WORD_ORDER_VIOLATION in Tamil
        # STOP processing immediately (one violation is enough)
        
        # =============================================================================
        # PHASE 4: ERROR RAISING
        # Step 4.1: Error payload with required fields
        # Step 4.2: Anchor choice - Primary: noun, Secondary: verb
        # =============================================================================
        
        errors.append({
            # Core error identification
            "rule": "WORD_ORDER_VIOLATION",
            "error_type": "GRAMMAR",
            
            # Phase 4.1: Simplified error payload
            "offending_noun": clean_token,
            "finite_verb": tokens[verb_index] if verb_index < len(tokens) else "",
            "message": "Case-less noun appears after finite verb",
            
            # Phase 4.2: Anchor choice for highlighting
            "primary_highlight": clean_token,      # Primary → noun
            "secondary_highlight": tokens[verb_index] if verb_index < len(tokens) else "",  # Secondary → verb
            
            # Additional context (for backward compatibility and debugging)
            "description": (
                f"Word order violation: noun '{clean_token}' appears after finite verb "
                f"without case marker. In Tamil, nouns after the verb must "
                f"have explicit grammatical role markers (e.g., -ஐ, -க்கு, -இல், -உடன், -ஆல்)."
            ),
            "location": clean_token,
            "word": clean_token,
            "reason": "Unmarked noun in post-verb position (Step 3.4: Core violation check)",
            "severity": "MEDIUM",
            "sentence": sentence,
            "verb_word": tokens[verb_index] if verb_index < len(tokens) else "",
            "post_verb_position": i - verb_index,
        })
        
        # CRITICAL: STOP processing after first violation (Step 3.4 requirement)
        # Do not continue scanning for more violations
        return errors
    
    return errors


# =============================================================================
# STEP 5: CLAUSE BOUNDARY DETECTION (scope control for tense consistency)
# Golden Rule #3: Tense consistency is checked PER CLAUSE, not per sentence.
# Clause boundaries reset tense scope — each clause can have its own tense.
# =============================================================================

# Clause boundary markers — comprehensive list (avoid false positives by checking per clause)
# These markers separate independent clauses that can have different tenses.
# NOTE: These are DISTINCT from time markers (TIME_MARKER_TABLE) — no overlap/conflict.
# Time markers indicate WHEN (temporal); clause markers indicate STRUCTURE (boundaries).
CLAUSE_BOUNDARY_MARKERS: Tuple[str, ...] = (
    # Conjunctions (contrast, addition)
    "ஆனால்",        # but
    "ஆனாலும்",      # even though
    "ஆகையால்",      # therefore
    "ஆதலால்",       # therefore
    "ஏனெனில்",      # because
    "ஏனென்றால்",    # because
    "என்றாலும்",    # even if
    "இருந்தாலும்",   # even though
    "இருப்பினும்",   # nevertheless
    "எனினும்",      # nevertheless
    "எனவே",        # therefore
    "அதனால்",      # therefore
    "அதால்",       # because of that
    "அதனால்தான்",   # that's why
    
    # Quotative / reported speech markers
    "என்று",       # that (quotative)
    "என்றார்",     # said that
    "என்றான்",     # said that
    "என்றாள்",     # said that
    "என்றனர்",     # said that
    "என்பது",      # it is said
    "என்பதால்",    # because it is said
    "என்பதையும்",   # and the fact that
    
    # Conditional markers
    "என்றால்",     # if
    "ஆனால்",       # if/but
    "எனில்",       # if
    "ஆயின்",       # if
    
    # Addition / sequence
    "மற்றும்",      # and
    "அத்துடன்",     # moreover
    "மேலும்",       # moreover/and
    "பிறகு",        # then/after
    "பின்னர்",      # then/after
    "அதன்பின்",     # after that
    "அதன்பிறகு",    # after that
    
    # Contrast
    "ஆனால்",       # but (repeated for clarity)
    "ஆயினும்",      # however
    "என்றாலும்",    # even though
    
    # Purpose / reason
    "எனவே",        # so/therefore (repeated)
    "அதற்காக",     # for that
    "அதற்கென",     # for that purpose
    
    # Time-based clause boundaries (different from time markers)
    "அப்போது",      # then/at that time (can start new clause)
    "அதன்பின்னர்",   # after that
)

# All clause boundary markers (for quick lookup)
ALL_CLAUSE_BOUNDARIES: Tuple[str, ...] = CLAUSE_BOUNDARY_MARKERS


def split_into_clauses(sentence: str) -> List[str]:
    """
    Split sentence into clauses using clause boundary markers.
    Each clause can have its own tense (scope control).
    Returns list of clause strings.
    """
    if not sentence or len(sentence.strip()) < 2:
        return []
    
    clauses: List[str] = []
    current_clause: str = sentence  # Explicit type annotation for Pyre
    
    # Try to split by clause markers
    for marker in CLAUSE_BOUNDARY_MARKERS:
        marker_str: str = str(marker)  # Type assertion for Pyre
        # pyre-fixme[16]: Pyre false positive on string __contains__
        if marker_str in current_clause:
            # Split and keep both parts as separate clauses
            # pyre-fixme[16]: Pyre false positive on split method
            parts: List[str] = current_clause.split(marker_str, 1)
            if len(parts) == 2 and parts[0].strip():
                clauses.append(parts[0].strip())
                current_clause = parts[1].strip()
                break
    
    # Add remaining part
    if current_clause and current_clause.strip():
        clauses.append(current_clause.strip())
    
    # If no split happened, return original sentence as single clause
    if not clauses:
        clauses = [sentence.strip()]
    
    return clauses


def has_clause_boundary(sentence: str) -> bool:
    """Check if sentence contains any clause boundary marker."""
    if not sentence:
        return False
    return any(marker in sentence for marker in CLAUSE_BOUNDARY_MARKERS)
