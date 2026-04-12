#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tamil Vocabulary Detector
Checks semantic compatibility between verbs and nouns
"""

import re
from typing import List, Dict, Set, Optional, Tuple


class TamilVocabularyDetector:
    """
    Vocabulary Detection based on Semantic Classes
    Checks if verbs and nouns are semantically compatible
    """
    
    # Verb suffix patterns (finite verbs) - Rule-based detection
    # IMPORTANT: Order matters - longer suffixes first for proper matching
    VERB_SUFFIXES = [
        # Past tense (longer forms first)
        "த்தேன்", "த்தான்", "த்தாள்", "த்தோம்", "த்தார்கள்",
        "ட்டேன்", "ட்டான்", "ட்டாள்", "ட்டோம்", "ட்டார்கள்",
        "ந்தேன்", "ந்தான்", "ந்தாள்", "ந்தோம்", "ந்தார்கள்",
        
        # Present tense (longer forms first)
        "க்கிறேன்", "க்கிறான்", "க்கிறாள்", "க்கிறோம்", "க்கிறார்கள்",
        "கிறேன்", "கிறான்", "கிறாள்", "கிறோம்", "கிறார்கள்",
        
        # Future tense
        "வேன்", "வான்", "வாள்", "வோம்", "வார்கள்",
        
        # Neuter / generic
        "க்கிறது", "த்தது", "ந்தது", "து",
    ]
    
    def __init__(self):
        """Initialize vocabulary detector with semantic classes"""
        
        # Verb → semantic class mapping
        self.VERB_CLASSES = {
            # CONSUMPTION verbs
            "சாப்பிடு": "CONSUMPTION",
            "சாப்பிட": "CONSUMPTION",
            "சாப்பிடுகிறேன்": "CONSUMPTION",
            "சாப்பிடுகிறான்": "CONSUMPTION",
            "சாப்பிட்டேன்": "CONSUMPTION",
            "சாப்பிட்டான்": "CONSUMPTION",
            "சாப்பிட்டாள்": "CONSUMPTION",
            "சாப்பிட்டோம்": "CONSUMPTION",
            "சாப்பிட்டார்கள்": "CONSUMPTION",
            "சாப்பி": "CONSUMPTION",  # Normalized form from சாப்பிட்டேன்
            "உண்ணு": "CONSUMPTION",
            "உண்ண": "CONSUMPTION",
            "உண்ணுகிறேன்": "CONSUMPTION",
            "உண்ணுகிறான்": "CONSUMPTION",
            "உண்டேன்": "CONSUMPTION",
            "குடி": "CONSUMPTION",
            "குடிக்கிறேன்": "CONSUMPTION",
            "குடிக்கிறான்": "CONSUMPTION",
            "குடித்தேன்": "CONSUMPTION",
            "தின்": "CONSUMPTION",
            "தின்கிறேன்": "CONSUMPTION",
            "தின்கிறான்": "CONSUMPTION",
            "தின்றேன்": "CONSUMPTION",
            
            # PERCEPTION verbs
            "பார்": "PERCEPTION",
            "பார்த்தேன்": "PERCEPTION",
            "பார்த்தான்": "PERCEPTION",
            "பார்க்கிறேன்": "PERCEPTION",
            "பார்க்கிறான்": "PERCEPTION",
            "காண்": "PERCEPTION",
            "கண்டேன்": "PERCEPTION",
            "கண்டான்": "PERCEPTION",
            "காண்கிறேன்": "PERCEPTION",
            "காண்கிறான்": "PERCEPTION",
            "கேள்": "PERCEPTION",
            "கேட்டேன்": "PERCEPTION",
            "கேட்டான்": "PERCEPTION",
            "கேட்கிறேன்": "PERCEPTION",
            "கேட்கிறான்": "PERCEPTION",
            "படி": "PERCEPTION",
            "படித்தேன்": "PERCEPTION",
            "படித்தான்": "PERCEPTION",
            "படிக்கிறேன்": "PERCEPTION",
            "படிக்கிறான்": "PERCEPTION",
            "வாசி": "PERCEPTION",
            "வாசித்தேன்": "PERCEPTION",
            "வாசிக்கிறேன்": "PERCEPTION",
            "பட": "PERCEPTION",
            "படுகிறேன்": "PERCEPTION",
            "படுகிறான்": "PERCEPTION",
            
            # COGNITIVE verbs
            "நினை": "COGNITIVE",
            "நினைத்தேன்": "COGNITIVE",
            "நினைத்தான்": "COGNITIVE",
            "நினைக்கிறேன்": "COGNITIVE",
            "நினைக்கிறான்": "COGNITIVE",
            "கற்று": "COGNITIVE",
            "கற்றேன்": "COGNITIVE",
            "கற்றான்": "COGNITIVE",
            "கற்கிறேன்": "COGNITIVE",
            "கற்கிறான்": "COGNITIVE",
            "கற்பி": "COGNITIVE",
            "கற்பித்தேன்": "COGNITIVE",
            "கற்பிக்கிறேன்": "COGNITIVE",
            "பயில்": "COGNITIVE",
            "பயின்றேன்": "COGNITIVE",
            "பயில்கிறேன்": "COGNITIVE",
            "ஆராய்": "COGNITIVE",
            "ஆராய்ந்தேன்": "COGNITIVE",
            "ஆராய்கிறேன்": "COGNITIVE",
            
            # ACTION verbs
            "செய்": "ACTION",
            "செய்தேன்": "ACTION",
            "செய்தான்": "ACTION",
            "செய்கிறேன்": "ACTION",
            "செய்கிறான்": "ACTION",
            "விளையாடு": "ACTION",
            "விளையாடினேன்": "ACTION",
            "விளையாடுகிறேன்": "ACTION",
            "ஓடு": "ACTION",
            "ஓடினேன்": "ACTION",
            "ஓடுகிறேன்": "ACTION",
            "நட": "ACTION",
            "நடந்தேன்": "ACTION",
            "நடக்கிறேன்": "ACTION",
            "வா": "ACTION",
            "வந்தேன்": "ACTION",
            "வருகிறேன்": "ACTION",
            "போ": "ACTION",
            "போனேன்": "ACTION",
            "போகிறேன்": "ACTION",
            "செல்": "ACTION",
            "சென்றேன்": "ACTION",
            "செல்கிறேன்": "ACTION",
        }
        
        # Noun → allowed verb classes mapping
        self.NOUN_CLASSES = {
            # PERCEPTION nouns
            "படம்": ["PERCEPTION"],
            "படங்கள்": ["PERCEPTION"],
            "பாடல்": ["PERCEPTION"],
            "பாடல்கள்": ["PERCEPTION"],
            "புத்தகம்": ["PERCEPTION", "COGNITIVE"],
            "புத்தகங்கள்": ["PERCEPTION", "COGNITIVE"],
            "கதை": ["PERCEPTION", "COGNITIVE"],
            "கதைகள்": ["PERCEPTION", "COGNITIVE"],
            "சினிமா": ["PERCEPTION"],
            "திரைப்படம்": ["PERCEPTION"],
            "திரைப்படங்கள்": ["PERCEPTION"],
            "சங்கீதம்": ["PERCEPTION"],
            "இசை": ["PERCEPTION"],
            
            # CONSUMPTION nouns
            "உணவு": ["CONSUMPTION"],
            "உணவுகள்": ["CONSUMPTION"],
            "தண்ணீர்": ["CONSUMPTION"],
            "பால்": ["CONSUMPTION"],
            "சோறு": ["CONSUMPTION"],
            "சாதம்": ["CONSUMPTION"],
            "தோசை": ["CONSUMPTION"],
            "இட்லி": ["CONSUMPTION"],
            "வடை": ["CONSUMPTION"],
            "காபி": ["CONSUMPTION"],
            "தேநீர்": ["CONSUMPTION"],
            "பழம்": ["CONSUMPTION"],
            "பழங்கள்": ["CONSUMPTION"],
            "மாம்பழம்": ["CONSUMPTION"],
            "வாழைப்பழம்": ["CONSUMPTION"],
            
            # COGNITIVE nouns
            "பாடம்": ["COGNITIVE", "PERCEPTION"],
            "பாடங்கள்": ["COGNITIVE", "PERCEPTION"],
            "கல்வி": ["COGNITIVE"],
            "அறிவு": ["COGNITIVE"],
            "எண்ணம்": ["COGNITIVE"],
            "யோசனை": ["COGNITIVE"],
            
            # ACTION nouns
            "விளையாட்டு": ["ACTION"],
            "விளையாட்டுகள்": ["ACTION"],
            "பயிற்சி": ["ACTION"],
            "நடைபயிற்சி": ["ACTION"],
            "ஓட்டம்": ["ACTION"],
        }
        
        # Build reverse mapping for faster lookup
        self._build_reverse_mappings()
    
    def _build_reverse_mappings(self):
        """Build reverse mappings for efficient lookup"""
        # Verb roots to classes
        self.verb_roots_to_class = {}
        for verb, v_class in self.VERB_CLASSES.items():
            # Extract root (remove common suffixes)
            root = self._extract_verb_root(verb)
            if root:
                if root not in self.verb_roots_to_class:
                    self.verb_roots_to_class[root] = set()
                self.verb_roots_to_class[root].add(v_class)
        
        # Noun roots to classes
        self.noun_roots_to_class = {}
        for noun, n_classes in self.NOUN_CLASSES.items():
            root = self._extract_noun_root(noun)
            if root:
                if root not in self.noun_roots_to_class:
                    self.noun_roots_to_class[root] = set()
                for n_class in n_classes:
                    self.noun_roots_to_class[root].add(n_class)
    
    def _extract_verb_root(self, verb: str) -> Optional[str]:
        """
        Extract verb root by removing common suffixes
        Comprehensive list of Tamil verb suffixes for better accuracy
        """
        # Comprehensive verb suffixes (sorted by length - longest first for proper matching)
        suffixes = [
            # Present tense - first person plural (with 'க்' infix)
            'க்கிறோம்', 'க்கிறார்கள்', 'க்கிறீர்கள்',
            # Present tense - first person singular (with 'க்' infix)
            'க்கிறேன்',
            # Present tense - third person (with 'க்' infix)
            'க்கிறான்', 'க்கிறாள்', 'க்கிறது', 'க்கிறார்',
            # Present tense - first person plural
            'கிறோம்', 'கிறார்கள்', 'கிறீர்கள்',
            # Present tense - first person singular
            'கிறேன்',
            # Present tense - third person
            'கிறான்', 'கிறாள்', 'கிறது', 'கிறார்',
            # Past tense - plural
            'த்தோம்', 'த்தார்கள்', 'ந்தோம்', 'ந்தார்கள்',
            'த்தீர்கள்', 'ந்தீர்கள்',
            # Past tense - singular
            'த்தேன்', 'த்தான்', 'த்தாள்', 'த்தது',
            'ந்தேன்', 'ந்தான்', 'ந்தாள்', 'ந்தது',
            'த்தார்', 'ந்தார்',
            # Special past forms (irregular verbs)
            'வந்தேன்', 'வந்தான்', 'வந்தாள்',  # வா -> வந்த
            'போனேன்', 'போனான்', 'போனாள்',    # போ -> போன
            'சென்றேன்', 'சென்றான்', 'சென்றாள்', # செல் -> சென்ற
            'எழுதினேன்', 'எழுதினான்', 'எழுதினாள்', # எழுது -> எழுதின
            # Future tense
            'வேன்', 'வான்', 'வாள்', 'வோம்', 'வார்கள்',
            'வீர்கள்', 'வீர்', 'வீர்கள்',
            # Imperative
            'ப்பான்', 'ப்பாள்', 'ப்பது', 'ப்பார்', 'ப்பீர்கள்',
            'ப்போம்', 'ப்பீர்கள்',
            # Infinitive/Participle forms
            'த்து', 'ந்து', 'க்க', 'க்கும்', 'த்தும்', 'ந்தும்',
            'த்தல்', 'ந்தல்', 'க்கல்',
            # Gerund forms
            'த்துக்', 'ந்துக்', 'த்துக்', 'ந்துக்',
            # Conditional
            'த்தால்', 'ந்தால்', 'க்கால்',
            # Negative forms
            'மாட்டேன்', 'மாட்டான்', 'மாட்டாள்', 'மாட்டோம்', 'மாட்டார்கள்',
            'வேண்டாம்', 'வேண்டா',
            # Honorific forms
            'க்கிறீர்கள்', 'த்தீர்கள்', 'ந்தீர்கள்',
            # Other common forms
            'ய', 'க', 'க்கிற', 'த்திற', 'ந்திற',
            'க்கும்', 'த்தும்', 'ந்தும்',
            # Perfective
            'த்திருக்கிறேன்', 'த்திருக்கிறான்', 'த்திருக்கிறாள்',
            'ந்திருக்கிறேன்', 'ந்திருக்கிறான்', 'ந்திருக்கிறாள்',
            'த்திருக்கிறோம்', 'த்திருக்கிறார்கள்',
            'ந்திருக்கிறோம்', 'ந்திருக்கிறார்கள்',
            # Past perfect
            'த்திருந்தேன்', 'த்திருந்தான்', 'த்திருந்தாள்',
            'ந்திருந்தேன்', 'ந்திருந்தான்', 'ந்திருந்தாள்',
            'த்திருந்தோம்', 'த்திருந்தார்கள்',
            'ந்திருந்தோம்', 'ந்திருந்தார்கள்',
        ]
        
        for suffix in sorted(suffixes, key=len, reverse=True):
            if verb.endswith(suffix):
                root = verb[:-len(suffix)]
                if len(root) >= 2:
                    return root
        
        return verb if len(verb) >= 2 else None
    
    def _extract_noun_root(self, noun: str) -> Optional[str]:
        """
        Extract noun root by removing plural/case markers
        Comprehensive list of Tamil noun suffixes for better accuracy
        """
        # Comprehensive noun suffixes (sorted by length - longest first for proper matching)
        suffixes = [
            # Plural + Case markers (longest combinations first)
            'ங்களுக்கு', 'களுக்கு',      # Plural + Dative
            'ங்களில்', 'களில்',            # Plural + Locative
            'ங்களின்', 'களின்',            # Plural + Genitive
            'ங்களை', 'களை',               # Plural + Accusative
            'ங்களுடன்', 'களுடன்',         # Plural + Comitative
            'ங்களால்', 'களால்',            # Plural + Instrumental
            'ங்களோடு', 'களோடு',           # Plural + Comitative (variant)
            
            # Singular + Case markers
            'த்துக்கு', 'த்தை', 'த்தில்', 'த்தின்',  # With 'த்து' infix
            'த்தால்', 'த்தோடு', 'த்துடன்',           # Instrumental, Comitative
            'த்தோடு', 'த்துடன்',
            
            # Simple case markers
            'க்கு', 'உக்கு',              # Dative
            'ஐ', 'த்தை',                  # Accusative
            'இல்', 'த்தில்',               # Locative
            'இன்', 'த்தின்',               # Genitive
            'ஆல்', 'த்தால்',               # Instrumental
            'ஓடு', 'த்தோடு',              # Comitative
            'உடன்', 'த்துடன்',            # Comitative (variant)
            'ஓடு', 'த்தோடு',
            
            # Plural markers
            'ங்கள்', 'கள்',                # Plural marker
            # Special: words ending with 'ம்' that become 'ங்கள்' in plural
            # This is handled by checking if root + 'ம்' exists
            
            # Other common markers
            'த்து', 'த்த',                 # Infix forms
            'க்கு', 'க்க',                 # Dative/infinitive marker
            'இல்', 'இன்',                  # Simple locative/genitive
            'ஐ',                          # Simple accusative
            'ஆல்',                        # Simple instrumental
            'ஓடு', 'உடன்',                # Simple comitative
            
            # Possessive markers
            'த்துடைய', 'த்துடையது',       # Possessive forms
            'த்துடையவர்', 'த்துடையவர்கள்',
            
            # Compound markers
            'த்தோடு', 'த்துடன்',           # With comitative
            'த்தால்',                      # With instrumental
        ]
        
        for suffix in sorted(suffixes, key=len, reverse=True):
            if noun.endswith(suffix):
                root = noun[:-len(suffix)]
                if len(root) >= 2:
                    # Special case: If root doesn't end with 'ம்' and suffix was plural,
                    # try adding 'ம்' to get the base form
                    # Example: 'பாடங்களை' -> 'பாட' -> 'பாடம்'
                    if suffix.startswith('ங்கள்') or suffix.startswith('கள்'):
                        if not root.endswith('ம்'):
                            # Try root + 'ம்' as potential base form
                            # But return the root for now - actual lookup will handle it
                            pass
                    return root
        
        # Special handling for words ending with 'இல்', 'க்கு', etc. that might need 'ம்' added
        # Example: 'பள்ளியில்' -> 'பள்ளி' (already correct, no 'ம்' needed)
        # But 'படத்தில்' -> 'படம்' (needs special handling)
        simple_case_markers = ['இல்', 'க்கு', 'உக்கு', 'ஐ', 'இன்', 'ஆல்', 'ஓடு', 'உடன்']
        for marker in simple_case_markers:
            if noun.endswith(marker):
                root = noun[:-len(marker)]
                if len(root) >= 2:
                    # If root doesn't end with 'ம்', it might be a word like 'பள்ளி'
                    # Return as-is
                    return root
        
        return noun if len(noun) >= 2 else None
    
    def normalize_verb(self, word: str) -> str:
        """
        Converts inflected Tamil verb to its base form (stem).
        MVP-level normalization (safe & extendable).
        Uses simple suffix stripping for reliable detection.
        """
        # First try the simple rule-based approach (faster, more reliable)
        for suffix in self.VERB_SUFFIXES:
            if word.endswith(suffix):
                root = word[:-len(suffix)]
                if len(root) >= 2:  # Ensure we have a valid root
                    return root
        
        # Fallback to comprehensive extraction if simple approach fails
        root = self._extract_verb_root(word)
        return root if root else word
    
    def detect_main_verb(self, tokens: List[str]) -> Optional[str]:
        """
        Detects the main verb in a Tamil sentence.
        Scans from right to left and returns normalized verb.
        Returns None if no confident verb is found.
        
        Args:
            tokens: List of word tokens from the sentence
            
        Returns:
            Normalized verb root or None
        """
        # Scan from right to left (Tamil is SOV, verb typically at end)
        for token in reversed(tokens):
            # Check if token ends with any verb suffix
            for suffix in self.VERB_SUFFIXES:
                if token.endswith(suffix):
                    # Normalize and return
                    normalized = self.normalize_verb(token)
                    if normalized and len(normalized) >= 2:
                        return normalized
        return None
    
    def normalize_noun(self, word: str) -> str:
        """
        Normalize noun by removing case markers (MVP level - public helper)
        Returns the root form of the noun
        """
        root = self._extract_noun_root(word)
        return root if root else word
    
    def get_verb_class(self, verb: str) -> Optional[str]:
        """Get semantic class for a verb"""
        # Direct lookup
        if verb in self.VERB_CLASSES:
            return self.VERB_CLASSES[verb]
        
        # Try root extraction
        root = self._extract_verb_root(verb)
        if root and root in self.verb_roots_to_class:
            classes = self.verb_roots_to_class[root]
            # Return first class if multiple
            return list(classes)[0] if classes else None
        
        return None
    
    def get_noun_allowed_classes(self, noun: str) -> List[str]:
        """Get allowed verb classes for a noun"""
        # Direct lookup
        if noun in self.NOUN_CLASSES:
            return self.NOUN_CLASSES[noun]
        
        # Try root extraction
        root = self._extract_noun_root(noun)
        if root and root in self.noun_roots_to_class:
            return list(self.noun_roots_to_class[root])
        
        return []
    
    def extract_noun_verb(self, sentence: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract noun and verb from a sentence.
        Uses right-to-left scanning to find the main verb, then looks for nouns before it.
        
        Args:
            sentence: Tamil sentence string
            
        Returns:
            Tuple of (noun, verb) - both can be None if not found
        """
        tokens = sentence.split()
        if not tokens:
            return None, None
        
        # Detect main verb using right-to-left scan
        verb = self.detect_main_verb(tokens)
        
        if verb is None:
            return None, None
        
        # Find the noun - typically appears before the verb in SOV order
        # Look for words before the verb that might be nouns
        noun = None
        verb_token_index = -1
        
        # Find which token contains the verb
        for i in range(len(tokens) - 1, -1, -1):
            token = tokens[i].strip('.,!?;:()[]{}\'"')
            for suffix in self.VERB_SUFFIXES:
                if token.endswith(suffix):
                    verb_token_index = i
                    break
            if verb_token_index != -1:
                break
        
        # Look for noun before the verb (typically object in SOV order)
        if verb_token_index > 0:
            # Check tokens before the verb
            for i in range(verb_token_index - 1, -1, -1):
                potential_noun = tokens[i].strip('.,!?;:()[]{}\'"')
                # Check if it's a known noun or has noun-like properties
                noun_classes = self.get_noun_allowed_classes(potential_noun)
                if noun_classes:
                    noun = potential_noun
                    break
                # Also check normalized form
                normalized_noun = self.normalize_noun(potential_noun)
                if normalized_noun != potential_noun:
                    noun_classes = self.get_noun_allowed_classes(normalized_noun)
                    if noun_classes:
                        noun = normalized_noun
                        break
        
        return noun, verb
    
    def check_verb_noun_compatibility(self, sentence: str) -> Dict:
        """
        Check verb-noun compatibility in a sentence (CORE RULE).
        Extracts noun and verb, then checks if they are semantically compatible.
        
        Args:
            sentence: Tamil sentence to check
            
        Returns:
            Dict with status and error information
        """
        noun, verb = self.extract_noun_verb(sentence)
        
        if noun is None or verb is None:
            return {
                "status": "SKIP",
                "message": "Could not detect noun or verb",
                "noun": None,
                "verb": None
            }
        
        # Get noun's allowed verb classes
        noun_allowed_classes = self.get_noun_allowed_classes(noun)
        if not noun_allowed_classes:
            return {
                "status": "SKIP",
                "message": f"Noun '{noun}' not in vocabulary ontology",
                "noun": noun,
                "verb": verb
            }
        
        # Get verb's semantic class
        verb_class = self.get_verb_class(verb)
        if not verb_class:
            return {
                "status": "SKIP",
                "message": f"Verb '{verb}' not in vocabulary ontology",
                "noun": noun,
                "verb": verb
            }
        
        # Check compatibility
        if verb_class not in noun_allowed_classes:
            return {
                "status": "VOCAB_ERROR",
                "error_type": "Verb–Noun Incompatibility",
                "noun": noun,
                "verb": verb,
                "noun_allowed_classes": noun_allowed_classes,
                "verb_class": verb_class,
                "message": f"'{noun}' என்ற பெயர்ச்சொல்லுடன் '{verb}' என்ற வினைச்சொல் இயல்பாகப் பயன்படுத்தப்படாது."
            }
        
        return {
            "status": "PASS",
            "message": "Vocabulary OK",
            "noun": noun,
            "verb": verb
        }
    
    def check_vocabulary_compatibility(self, verb: str, noun: str) -> Dict:
        """
        Check if verb and noun are semantically compatible
        
        Args:
            verb: Verb word
            noun: Noun word
            
        Returns:
            Dict with:
                - is_compatible: bool
                - verb_class: str or None
                - noun_allowed_classes: List[str]
                - error_message: str or None
        """
        verb_class = self.get_verb_class(verb)
        noun_classes = self.get_noun_allowed_classes(noun)
        
        # If we don't have information about either, assume compatible
        if not verb_class and not noun_classes:
            return {
                'is_compatible': True,
                'verb_class': None,
                'noun_allowed_classes': [],
                'error_message': None
            }
        
        # If we have verb class but no noun info, assume compatible
        if verb_class and not noun_classes:
            return {
                'is_compatible': True,
                'verb_class': verb_class,
                'noun_allowed_classes': [],
                'error_message': None
            }
        
        # If we have noun info but no verb info, assume compatible
        if not verb_class and noun_classes:
            return {
                'is_compatible': True,
                'verb_class': None,
                'noun_allowed_classes': noun_classes,
                'error_message': None
            }
        
        # Both have info - check compatibility
        if verb_class in noun_classes:
            return {
                'is_compatible': True,
                'verb_class': verb_class,
                'noun_allowed_classes': noun_classes,
                'error_message': None
            }
        else:
            # Incompatible
            return {
                'is_compatible': False,
                'verb_class': verb_class,
                'noun_allowed_classes': noun_classes,
                'error_message': f"'{verb}' (வினைச்சொல்) மற்றும் '{noun}' (பெயர்ச்சொல்) பொருளியல் ரீதியாக பொருந்தவில்லை"
            }
    
    def detect_vocabulary_errors(self, text: str) -> Dict:
        """
        Detect vocabulary errors in text
        
        Args:
            text: Text to check
            
        Returns:
            Dict with:
                - vocabulary_errors: List of error dicts
                - total_checks: int
                - error_count: int
                - main_verb: str or None (detected main verb)
                - main_verb_class: str or None (semantic class of main verb)
        """
        # Tokenize text
        words = text.split()
        
        # Detect main verb using right-to-left scan
        main_verb = self.detect_main_verb(words)
        
        vocabulary_errors = []
        checked_pairs = set()
        
        # Check adjacent word pairs
        for i in range(len(words) - 1):
            word1 = words[i].strip('.,!?;:()[]{}\'"')
            word2 = words[i + 1].strip('.,!?;:()[]{}\'"')
            
            # Try word1 as noun, word2 as verb
            noun_classes = self.get_noun_allowed_classes(word1)
            verb_class = self.get_verb_class(word2)
            
            if noun_classes and verb_class:
                pair_key = f"{word1}:{word2}"
                if pair_key not in checked_pairs:
                    checked_pairs.add(pair_key)
                    result = self.check_vocabulary_compatibility(word2, word1)
                    if not result['is_compatible']:
                        vocabulary_errors.append({
                            'verb': word2,
                            'noun': word1,
                            'verb_class': result['verb_class'],
                            'noun_allowed_classes': result['noun_allowed_classes'],
                            'error_message': result['error_message'],
                            'position': i
                        })
            
            # Try word1 as verb, word2 as noun
            verb_class1 = self.get_verb_class(word1)
            noun_classes2 = self.get_noun_allowed_classes(word2)
            
            if verb_class1 and noun_classes2:
                pair_key = f"{word1}:{word2}"
                if pair_key not in checked_pairs:
                    checked_pairs.add(pair_key)
                    result = self.check_vocabulary_compatibility(word1, word2)
                    if not result['is_compatible']:
                        vocabulary_errors.append({
                            'verb': word1,
                            'noun': word2,
                            'verb_class': result['verb_class'],
                            'noun_allowed_classes': result['noun_allowed_classes'],
                            'error_message': result['error_message'],
                            'position': i
                        })
        
        return {
            'vocabulary_errors': vocabulary_errors,
            'total_checks': len(checked_pairs),
            'error_count': len(vocabulary_errors),
            'main_verb': main_verb,
            'main_verb_class': self.get_verb_class(main_verb) if main_verb else None
        }


# ============================================================================
# SIMPLE USAGE FUNCTIONS
# ============================================================================

# Global detector instance (lazy loading)
_detector_instance = None

def get_detector():
    """Get or create global vocabulary detector instance"""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = TamilVocabularyDetector()
    return _detector_instance

def check_vocabulary(verb: str, noun: str) -> Dict:
    """
    Simple function to check vocabulary compatibility
    
    Usage:
        from tamil_vocabulary_detector import check_vocabulary
        result = check_vocabulary('சாப்பிடு', 'படம்')
        print(result['is_compatible'])  # False
    """
    detector = get_detector()
    return detector.check_vocabulary_compatibility(verb, noun)

def detect_vocabulary_errors(text: str) -> Dict:
    """
    Simple function to detect vocabulary errors in text
    
    Usage:
        from tamil_vocabulary_detector import detect_vocabulary_errors
        result = detect_vocabulary_errors('நான் படம் சாப்பிடுகிறேன்')
        print(result['vocabulary_errors'])
    """
    detector = get_detector()
    return detector.detect_vocabulary_errors(text)


# ============================================================================
# MAIN (for testing)
# ============================================================================

if __name__ == '__main__':
    import sys
    import io
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    print("="*70)
    print("Tamil Vocabulary Detector - Test")
    print("="*70)
    
    detector = TamilVocabularyDetector()
    
    # Test main verb detection
    print("\n[*] Testing main verb detection:")
    verb_detection_tests = [
        "நான் படிக்கிறேன்",
        "நான் புத்தகம் படிக்கிறேன்",
        "நான் உணவு சாப்பிடுகிறேன்",
        "நான் படம் பார்க்கிறேன்",
        "நான் நேற்று பள்ளிக்குச் சென்றேன்",
        "நான் தினமும் காலை நேரத்தில் நடைபயிற்சி செய்கிறேன்",
    ]
    
    for test_sentence in verb_detection_tests:
        tokens = test_sentence.split()
        main_verb = detector.detect_main_verb(tokens)
        verb_class = detector.get_verb_class(main_verb) if main_verb else None
        print(f"  '{test_sentence}'")
        print(f"    -> Main verb: '{main_verb}' (class: {verb_class})")
    
    # Test normalization functions
    print("\n[*] Testing normalization functions:")
    verb_tests = [
        ("சாப்பிடுகிறேன்", "சாப்பிடு"),
        ("படிக்கிறான்", "படி"),
        ("பார்த்தேன்", "பார்"),
        ("வந்தேன்", "வா"),
        ("செய்தேன்", "செய்"),
        ("உண்டேன்", "உண்"),
        ("குடித்தேன்", "குடி"),
    ]
    
    print("\n  Verb normalization:")
    for inflected, expected_root in verb_tests:
        normalized = detector.normalize_verb(inflected)
        status = "✓" if normalized == expected_root else "✗"
        print(f"    {status} '{inflected}' -> '{normalized}' (expected: '{expected_root}')")
    
    noun_tests = [
        ("பாடங்களை", "பாடம்"),
        ("புத்தகத்தை", "புத்தகம்"),
        ("பள்ளியில்", "பள்ளி"),
        ("உணவுக்கு", "உணவு"),
        ("படத்தின்", "படம்"),
        ("கல்லூரியில்", "கல்லூரி"),
    ]
    
    print("\n  Noun normalization:")
    for inflected, expected_root in noun_tests:
        normalized = detector.normalize_noun(inflected)
        status = "✓" if normalized == expected_root else "✗"
        print(f"    {status} '{inflected}' -> '{normalized}' (expected: '{expected_root}')")
    
    # Test cases
    print("\n[*] Testing verb-noun compatibility:")
    test_cases = [
        ("சாப்பிடு", "உணவு", True),  # Compatible
        ("சாப்பிடு", "படம்", False),  # Incompatible
        ("பார்", "படம்", True),        # Compatible
        ("பார்", "உணவு", False),       # Incompatible
        ("படி", "புத்தகம்", True),     # Compatible
        ("நினை", "பாடம்", True),       # Compatible
    ]
    
    for verb, noun, expected in test_cases:
        result = detector.check_vocabulary_compatibility(verb, noun)
        status = "✓" if result['is_compatible'] == expected else "✗"
        print(f"  {status} '{verb}' + '{noun}' -> {result['is_compatible']} (expected: {expected})")
        if not result['is_compatible']:
            print(f"      Error: {result['error_message']}")
    
    # Test with inflected forms
    print("\n[*] Testing with inflected forms:")
    inflected_tests = [
        ("சாப்பிடுகிறேன்", "உணவை", True),   # Compatible (inflected)
        ("படிக்கிறான்", "புத்தகத்தை", True), # Compatible (inflected)
        ("பார்க்கிறேன்", "படத்தில்", True),  # Compatible (inflected)
    ]
    
    for verb, noun, expected in inflected_tests:
        result = detector.check_vocabulary_compatibility(verb, noun)
        status = "✓" if result['is_compatible'] == expected else "✗"
        print(f"  {status} '{verb}' + '{noun}' -> {result['is_compatible']} (expected: {expected})")
    
    # Test verb-noun compatibility check
    print("\n[*] Testing verb-noun compatibility check:")
    compatibility_tests = [
        "நான் படம் சாப்பிடுகிறேன்",      # Should fail - incompatible
        "நான் உணவு சாப்பிடுகிறேன்",      # Should pass - compatible
        "நான் புத்தகம் படிக்கிறேன்",      # Should pass - compatible
        "நான் படம் பார்க்கிறேன்",         # Should pass - compatible
        "நான் உணவு பார்க்கிறேன்",         # Should fail - incompatible
    ]
    
    for test_sentence in compatibility_tests:
        result = detector.check_verb_noun_compatibility(test_sentence)
        status_icon = "✓" if result['status'] == 'PASS' else "✗" if result['status'] == 'VOCAB_ERROR' else "○"
        print(f"  {status_icon} '{test_sentence}'")
        print(f"    Status: {result['status']}")
        if result['status'] == 'VOCAB_ERROR':
            print(f"    Error: {result['message']}")
        elif result['status'] == 'PASS':
            print(f"    Noun: {result.get('noun')}, Verb: {result.get('verb')}")
        elif result['status'] == 'SKIP':
            print(f"    {result['message']}")
    
    # Additional test cases with case markers
    print("\n[*] Testing verb-noun compatibility with case markers:")
    sentences = [
        "நான் ஒரு படத்தை பார்த்தேன்",      # Should pass - compatible (படம் + பார்)
        "நான் ஒரு படத்தை சாப்பிட்டேன்",    # Should fail - incompatible (படம் + சாப்பிடு)
        "அவன் புத்தகத்தை படித்தான்",        # Should pass - compatible (புத்தகம் + படி)
        "அவன் உணவை பார்த்தான்"              # Should fail - incompatible (உணவு + பார்)
    ]
    
    for s in sentences:
        print(f"\n  '{s}'")
        result = detector.check_verb_noun_compatibility(s)
        status_icon = "✓" if result['status'] == 'PASS' else "✗" if result['status'] == 'VOCAB_ERROR' else "○"
        print(f"    {status_icon} Status: {result['status']}")
        if result['status'] == 'VOCAB_ERROR':
            print(f"    Error: {result['message']}")
            print(f"    Noun: {result.get('noun')}, Verb: {result.get('verb')}")
        elif result['status'] == 'PASS':
            print(f"    Noun: {result.get('noun')}, Verb: {result.get('verb')}")
        elif result['status'] == 'SKIP':
            print(f"    {result['message']}")
        print("    " + "-" * 50)
    
    # Test full text
    print("\n[*] Testing full text:")
    test_text = "நான் படம் சாப்பிடுகிறேன்"
    result = detector.detect_vocabulary_errors(test_text)
    print(f"  Text: {test_text}")
    print(f"  Errors found: {result['error_count']}")
    if result['vocabulary_errors']:
        for err in result['vocabulary_errors']:
            print(f"    - {err.get('error_message', err.get('message', ''))}")

